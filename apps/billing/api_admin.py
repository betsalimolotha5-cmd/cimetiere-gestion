"""
API Admin pour la gestion de la facturation (CRUD complet).
Accessible uniquement aux administrateurs.
"""
from ninja import Router, Schema
from ninja.security import HttpBearer
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal
from django.db.models import Q
from django.utils import timezone
import logging

from .models import Facture, Paiement, TransactionFinanciere
from apps.accounts.models import User

router = Router(tags=["Admin - Facturation"])
logger = logging.getLogger('audit')


class AuthBearer(HttpBearer):
    def authenticate(self, request, token):
        if token == "session_authenticated":
            return token
        return None


# === SCHÉMAS ===

class FactureSchema(Schema):
    id: int
    numero_facture: str
    concession_id: Optional[int] = None
    client_id: int
    client_email: str
    client_nom: str
    montant_ht: Decimal
    taux_tva: Decimal
    montant_tva: Decimal
    montant_total: Decimal
    montant_paye: Decimal
    montant_restant: Decimal
    statut: str
    statut_display: str
    date_emission: date
    date_echeance: date
    date_paiement_complet: Optional[date] = None
    description: Optional[str] = None
    fichier_pdf: Optional[str] = None
    email_envoye: bool
    date_envoi_email: Optional[datetime] = None
    date_creation: datetime
    
    class Config:
        from_attributes = True


class FactureCreateUpdateSchema(Schema):
    concession_id: Optional[int] = None
    client_id: int
    montant_ht: Decimal
    taux_tva: Decimal = Decimal('0')
    description: Optional[str] = None
    date_emission: date = None
    date_echeance: date = None
    statut: str = 'EMISE'


class PaiementSchema(Schema):
    id: int
    numero_transaction: str
    facture_id: int
    facture_numero: str
    client_id: int
    client_email: str
    montant: Decimal
    mode_paiement: str
    statut: str
    statut_display: str
    reference_transaction: Optional[str] = None
    numero_telephone: Optional[str] = None
    date_paiement: date
    date_validation: Optional[date] = None
    valide_par_id: Optional[int] = None
    date_creation: datetime
    
    class Config:
        from_attributes = True


class PaiementCreateUpdateSchema(Schema):
    facture_id: int
    client_id: int
    montant: Decimal
    mode_paiement: str
    statut: str = 'EN_ATTENTE'
    reference_transaction: Optional[str] = None
    numero_telephone: Optional[str] = None
    date_paiement: date = None


class TransactionFinanciereSchema(Schema):
    id: int
    type_transaction: str
    montant: Decimal
    sens: str
    reference: Optional[str] = None
    facture_id: Optional[int] = None
    paiement_id: Optional[int] = None
    client_id: Optional[int] = None
    description: Optional[str] = None
    date_transaction: date
    date_creation: datetime
    
    class Config:
        from_attributes = True


class MessageSchema(Schema):
    success: bool
    message: str
    data: Optional[dict] = None


# === VÉRIFICATION DES PERMISSIONS ===

def check_admin(request):
    """Vérifie que l'utilisateur est administrateur."""
    if not request.user.is_authenticated:
        return False
    return request.user.is_admin()


# === ENDPOINTS FACTURES ===

@router.get("/factures/", response=List[FactureSchema], auth=AuthBearer())
def list_factures(request):
    """Liste toutes les factures."""
    if not check_admin(request):
        return 403, {"success": False, "message": "Accès refusé."}
    
    factures = Facture.objects.all().order_by('-date_emission').select_related('client', 'concession')
    return list(factures)


@router.get("/factures/{facture_id}", response=FactureSchema, auth=AuthBearer())
def get_facture(request, facture_id: int):
    """Récupère une facture spécifique."""
    if not check_admin(request):
        return 403, {"success": False, "message": "Accès refusé."}
    
    try:
        facture = Facture.objects.select_related('client', 'concession').get(id=facture_id)
        return facture
    except Facture.DoesNotExist:
        return 404, {"success": False, "message": "Facture introuvable."}


@router.post("/factures/", response=MessageSchema, auth=AuthBearer())
def create_facture(request, payload: FactureCreateUpdateSchema):
    """Crée une nouvelle facture."""
    if not check_admin(request):
        return 403, {"success": False, "message": "Accès refusé."}
    
    try:
        client = User.objects.get(id=payload.client_id)
        
        # Calculer les montants
        montant_tva = payload.montant_ht * (payload.taux_tva / Decimal('100'))
        montant_total = payload.montant_ht + montant_tva
        
        facture = Facture.objects.create(
            numero_facture=f"FACT-{timezone.now().year}-{Facture.objects.count() + 1:05d}",
            concession_id=payload.concession_id,
            client=client,
            montant_ht=payload.montant_ht,
            taux_tva=payload.taux_tva,
            montant_tva=montant_tva,
            montant_total=montant_total,
            montant_paye=Decimal('0'),
            statut=payload.statut,
            description=payload.description,
            date_emission=payload.date_emission or timezone.now().date(),
            date_echeance=payload.date_echeance or (timezone.now().date() + timezone.timedelta(days=30)),
            cree_par=request.user
        )
        
        logger.info(f"ADMIN_FACTURE_CREATED: facture={facture.numero_facture}, client={client.email}")
        
        return {
            "success": True,
            "message": f"Facture {facture.numero_facture} créée avec succès.",
            "data": {"facture_id": facture.id}
        }
    except User.DoesNotExist:
        return 400, {"success": False, "message": "Client introuvable."}
    except Exception as e:
        logger.error(f"ADMIN_FACTURE_CREATE_FAILED: error={str(e)}")
        return 500, {"success": False, "message": f"Erreur: {str(e)}"}


@router.put("/factures/{facture_id}", response=MessageSchema, auth=AuthBearer())
def update_facture(request, facture_id: int, payload: FactureCreateUpdateSchema):
    """Met à jour une facture."""
    if not check_admin(request):
        return 403, {"success": False, "message": "Accès refusé."}
    
    try:
        facture = Facture.objects.get(id=facture_id)
        
        if payload.client_id:
            client = User.objects.get(id=payload.client_id)
            facture.client = client
        
        if payload.montant_ht is not None:
            facture.montant_ht = payload.montant_ht
            facture.montant_tva = payload.montant_ht * (payload.taux_tva / Decimal('100'))
            facture.montant_total = payload.montant_ht + facture.montant_tva
        
        if payload.taux_tva is not None:
            facture.taux_tva = payload.taux_tva
        
        if payload.description is not None:
            facture.description = payload.description
        
        if payload.statut is not None:
            facture.statut = payload.statut
        
        if payload.date_emission is not None:
            facture.date_emission = payload.date_emission
        
        if payload.date_echeance is not None:
            facture.date_echeance = payload.date_echeance
        
        facture.save()
        
        logger.info(f"ADMIN_FACTURE_UPDATED: facture={facture.numero_facture}")
        
        return {
            "success": True,
            "message": f"Facture {facture.numero_facture} mise à jour.",
            "data": {"facture_id": facture.id}
        }
    except Facture.DoesNotExist:
        return 404, {"success": False, "message": "Facture introuvable."}
    except User.DoesNotExist:
        return 400, {"success": False, "message": "Client introuvable."}
    except Exception as e:
        logger.error(f"ADMIN_FACTURE_UPDATE_FAILED: error={str(e)}")
        return 500, {"success": False, "message": f"Erreur: {str(e)}"}


@router.post("/factures/{facture_id}/valider-paiement", response=MessageSchema, auth=AuthBearer())
def valider_paiement_facture(request, facture_id: int):
    """Marque une facture comme payée."""
    if not check_admin(request):
        return 403, {"success": False, "message": "Accès refusé."}
    
    try:
        facture = Facture.objects.get(id=facture_id)
        facture.statut = 'PAYEE'
        facture.montant_paye = facture.montant_total
        facture.date_paiement_complet = timezone.now().date()
        facture.save()
        
        logger.info(f"ADMIN_FACTURE_PAID: facture={facture.numero_facture}")
        
        return {
            "success": True,
            "message": f"Facture {facture.numero_facture} marquée comme payée.",
            "data": None
        }
    except Facture.DoesNotExist:
        return 404, {"success": False, "message": "Facture introuvable."}


@router.post("/factures/{facture_id}/annuler", response=MessageSchema, auth=AuthBearer())
def annuler_facture(request, facture_id: int, motif: str = "Annulée par l'administration"):
    """Annule une facture."""
    if not check_admin(request):
        return 403, {"success": False, "message": "Accès refusé."}
    
    try:
        facture = Facture.objects.get(id=facture_id)
        facture.statut = 'ANNULEE'
        facture.notes = f"{facture.notes or ''} ANNULATION: {motif}"
        facture.save()
        
        logger.info(f"ADMIN_FACTURE_CANCELLED: facture={facture.numero_facture}, motif={motif}")
        
        return {
            "success": True,
            "message": f"Facture {facture.numero_facture} annulée.",
            "data": None
        }
    except Facture.DoesNotExist:
        return 404, {"success": False, "message": "Facture introuvable."}


# === ENDPOINTS PAIEMENTS ===

@router.get("/paiements/", response=List[PaiementSchema], auth=AuthBearer())
def list_paiements(request):
    """Liste tous les paiements."""
    if not check_admin(request):
        return 403, {"success": False, "message": "Accès refusé."}
    
    paiements = Paiement.objects.all().order_by('-date_paiement').select_related('facture', 'client', 'valide_par')
    return list(paiements)


@router.get("/paiements/{paiement_id}", response=PaiementSchema, auth=AuthBearer())
def get_paiement(request, paiement_id: int):
    """Récupère un paiement spécifique."""
    if not check_admin(request):
        return 403, {"success": False, "message": "Accès refusé."}
    
    try:
        paiement = Paiement.objects.select_related('facture', 'client', 'valide_par').get(id=paiement_id)
        return paiement
    except Paiement.DoesNotExist:
        return 404, {"success": False, "message": "Paiement introuvable."}


@router.post("/paiements/", response=MessageSchema, auth=AuthBearer())
def create_paiement(request, payload: PaiementCreateUpdateSchema):
    """Crée un nouveau paiement."""
    if not check_admin(request):
        return 403, {"success": False, "message": "Accès refusé."}
    
    try:
        facture = Facture.objects.get(id=payload.facture_id)
        client = User.objects.get(id=payload.client_id)
        
        paiement = Paiement.objects.create(
            numero_transaction=f"PAY-{timezone.now().year}-{Paiement.objects.count() + 1:05d}",
            facture=facture,
            client=client,
            montant=payload.montant,
            mode_paiement=payload.mode_paiement,
            statut=payload.statut,
            reference_transaction=payload.reference_transaction,
            numero_telephone=payload.numero_telephone,
            date_paiement=payload.date_paiement or timezone.now().date(),
            cree_par=request.user
        )
        
        # Mettre à jour le montant payé de la facture
        facture.montant_paye += paiement.montant
        if facture.montant_paye >= facture.montant_total:
            facture.statut = 'PAYEE'
            facture.date_paiement_complet = timezone.now().date()
        facture.save()
        
        logger.info(f"ADMIN_PAIEMENT_CREATED: paiement={paiement.numero_transaction}, facture={facture.numero_facture}")
        
        return {
            "success": True,
            "message": f"Paiement {paiement.numero_transaction} créé avec succès.",
            "data": {"paiement_id": paiement.id}
        }
    except Facture.DoesNotExist:
        return 400, {"success": False, "message": "Facture introuvable."}
    except User.DoesNotExist:
        return 400, {"success": False, "message": "Client introuvable."}
    except Exception as e:
        logger.error(f"ADMIN_PAIEMENT_CREATE_FAILED: error={str(e)}")
        return 500, {"success": False, "message": f"Erreur: {str(e)}"}


@router.post("/paiements/{paiement_id}/valider", response=MessageSchema, auth=AuthBearer())
def valider_paiement(request, paiement_id: int):
    """Valide un paiement."""
    if not check_admin(request):
        return 403, {"success": False, "message": "Accès refusé."}
    
    try:
        paiement = Paiement.objects.get(id=paiement_id)
        
        if paiement.statut != 'EN_ATTENTE':
            return 400, {"success": False, "message": "Seuls les paiements en attente peuvent être validés."}
        
        paiement.statut = 'VALIDE'
        paiement.date_validation = timezone.now().date()
        paiement.valide_par = request.user
        paiement.save()
        
        # Mettre à jour la facture
        facture = paiement.facture
        facture.montant_paye += paiement.montant
        if facture.montant_paye >= facture.montant_total:
            facture.statut = 'PAYEE'
            facture.date_paiement_complet = timezone.now().date()
        facture.save()
        
        logger.info(f"ADMIN_PAIEMENT_VALIDATED: paiement={paiement.numero_transaction}")
        
        return {
            "success": True,
            "message": f"Paiement {paiement.numero_transaction} validé avec succès.",
            "data": None
        }
    except Paiement.DoesNotExist:
        return 404, {"success": False, "message": "Paiement introuvable."}


@router.post("/paiements/{paiement_id}/refuser", response=MessageSchema, auth=AuthBearer())
def refuser_paiement(request, paiement_id: int, motif: str = "Refusé par l'administration"):
    """Refuse un paiement."""
    if not check_admin(request):
        return 403, {"success": False, "message": "Accès refusé."}
    
    try:
        paiement = Paiement.objects.get(id=paiement_id)
        
        if paiement.statut != 'EN_ATTENTE':
            return 400, {"success": False, "message": "Seuls les paiements en attente peuvent être refusés."}
        
        paiement.statut = 'REFUSE'
        paiement.motif_refus = motif
        paiement.save()
        
        logger.info(f"ADMIN_PAIEMENT_REFUSED: paiement={paiement.numero_transaction}, motif={motif}")
        
        return {
            "success": True,
            "message": f"Paiement {paiement.numero_transaction} refusé.",
            "data": None
        }
    except Paiement.DoesNotExist:
        return 404, {"success": False, "message": "Paiement introuvable."}


# === ENDPOINTS TRANSACTIONS ===

@router.get("/transactions/", response=List[TransactionFinanciereSchema], auth=AuthBearer())
def list_transactions(request):
    """Liste toutes les transactions financières."""
    if not check_admin(request):
        return 403, {"success": False, "message": "Accès refusé."}
    
    transactions = TransactionFinanciere.objects.all().order_by('-date_transaction')
    return list(transactions)


@router.get("/statistiques-financieres/", auth=AuthBearer())
def get_statistiques_financieres(request):
    """Récupère les statistiques financières."""
    if not check_admin(request):
        return 403, {"success": False, "message": "Accès refusé."}
    
    from django.db.models import Sum
    
    # Revenus du mois
    mois_actuel = timezone.now().replace(day=1)
    revenus_mois = Paiement.objects.filter(
        statut='VALIDE',
        date_validation__gte=mois_actuel
    ).aggregate(total=Sum('montant'))['total'] or Decimal('0')
    
    # Revenus de l'année
    annee_actuelle = timezone.now().replace(month=1, day=1)
    revenus_annee = Paiement.objects.filter(
        statut='VALIDE',
        date_validation__gte=annee_actuelle
    ).aggregate(total=Sum('montant'))['total'] or Decimal('0')
    
    # Factures en retard
    factures_en_retard = Facture.objects.filter(
        statut__in=['EMISE', 'PARTIELLEMENT_PAYEE'],
        date_echeance__lt=timezone.now().date()
    ).count()
    
    # Factures impayées
    factures_impayees = Facture.objects.filter(
        statut__in=['EMISE', 'PARTIELLEMENT_PAYEE']
    ).count()
    
    # Total facturé
    total_facture = Facture.objects.filter(statut='EMISE').aggregate(total=Sum('montant_total'))['total'] or Decimal('0')
    
    # Total payé
    total_paye = Paiement.objects.filter(statut='VALIDE').aggregate(total=Sum('montant'))['total'] or Decimal('0')
    
    return {
        "revenus_mois": float(revenus_mois),
        "revenus_annee": float(revenus_annee),
        "factures_en_retard": factures_en_retard,
        "factures_impayees": factures_impayees,
        "total_facture": float(total_facture),
        "total_paye": float(total_paye),
        "taux_recouvrement": float((total_paye / total_facture * 100)) if total_facture > 0 else 0
    }
