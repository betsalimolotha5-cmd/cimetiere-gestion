"""
API Django Ninja pour la facturation et les paiements.
"""
from ninja import Router, Schema
from ninja.security import HttpBearer
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q, Sum, Count
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal
import logging
import uuid

from .models import Facture, Paiement, TransactionFinanciere
from apps.accounts.services import PermissionService

router = Router(tags=["Facturation"])
logger = logging.getLogger('audit')


# === AUTHENTIFICATION ===

class AuthBearer(HttpBearer):
    def authenticate(self, request, token):
        if token == "session_authenticated":
            return token
        return None


# === SCHÉMAS ===

# --- Factures ---
class FactureSchema(Schema):
    id: int
    numero_facture: str
    reference: uuid.UUID
    concession_id: int
    concession_numero: str
    client_id: int
    client_email: str
    client_nom: str
    montant_ht: Decimal
    taux_tva: Decimal
    montant_tva: Decimal
    montant_total: Decimal
    montant_paye: Decimal
    montant_restant: Decimal
    date_emission: date
    date_echeance: date
    statut: str
    statut_display: str
    email_envoye: bool
    est_payee: bool
    est_en_retard: bool
    
    class Config:
        from_attributes = True


class FactureCreateSchema(Schema):
    concession_id: int
    client_id: int
    montant_ht: Decimal
    taux_tva: Decimal = Decimal('0.00')
    date_emission: date
    date_echeance: date
    description: str = ''
    notes: str = ''


class FactureUpdateSchema(Schema):
    montant_ht: Optional[Decimal] = None
    taux_tva: Optional[Decimal] = None
    date_echeance: Optional[date] = None
    description: Optional[str] = None
    notes: Optional[str] = None


class MessageSchema(Schema):
    success: bool
    message: str
    data: Optional[dict] = None


# --- Paiements ---
class PaiementSchema(Schema):
    id: int
    reference: uuid.UUID
    numero_transaction: str
    facture_id: int
    facture_numero: str
    client_id: int
    client_email: str
    montant: Decimal
    mode_paiement: str
    mode_paiement_display: str
    reference_transaction: str
    numero_telephone: str
    statut: str
    statut_display: str
    date_paiement: datetime
    date_validation: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class PaiementCreateSchema(Schema):
    facture_id: int
    montant: Decimal
    mode_paiement: str
    reference_transaction: str = ''
    numero_telephone: str = ''
    notes: str = ''


class StatistiquesFinancieresSchema(Schema):
    total_factures: int
    factures_payees: int
    factures_en_retard: int
    factures_en_attente: int
    revenus_mois: Decimal
    revenus_annee: Decimal
    total_recu: Decimal
    total_restant: Decimal
    paiements_par_mode: dict


# === ENDPOINTS : FACTURES ===

@router.get("/factures", response=List[FactureSchema], auth=AuthBearer())
def list_factures(request, statut: Optional[str] = None, client_id: Optional[int] = None):
    """Lister toutes les factures."""
    if not PermissionService.can_view_financial_stats(request.user):
        return 403, {"detail": "Permission refusée"}
    
    queryset = Facture.objects.select_related('concession', 'client').all()
    
    # Filtrer par client si demandé (pour les clients non-admin)
    if request.user.is_client():
        queryset = queryset.filter(client=request.user)
    elif client_id:
        queryset = queryset.filter(client_id=client_id)
    
    if statut:
        queryset = queryset.filter(statut=statut)
    
    factures_data = []
    for facture in queryset:
        factures_data.append({
            'id': facture.id,
            'numero_facture': facture.numero_facture,
            'reference': facture.reference,
            'concession_id': facture.concession_id,
            'concession_numero': facture.concession.numero_contrat,
            'client_id': facture.client_id,
            'client_email': facture.client.email,
            'client_nom': facture.client.get_full_name(),
            'montant_ht': facture.montant_ht,
            'taux_tva': facture.taux_tva,
            'montant_tva': facture.montant_tva,
            'montant_total': facture.montant_total,
            'montant_paye': facture.montant_paye,
            'montant_restant': facture.montant_restant,
            'date_emission': facture.date_emission,
            'date_echeance': facture.date_echeance,
            'statut': facture.statut,
            'statut_display': facture.get_statut_display(),
            'email_envoye': facture.email_envoye,
            'est_payee': facture.est_payee(),
            'est_en_retard': facture.est_en_retard(),
        })
    
    return factures_data


@router.get("/factures/{facture_id}", response=FactureSchema, auth=AuthBearer())
def get_facture(request, facture_id: int):
    """Récupérer les détails d'une facture."""
    facture = get_object_or_404(
        Facture.objects.select_related('concession', 'client'),
        id=facture_id
    )
    
    # Vérifier les permissions
    if not request.user.is_admin() and facture.client != request.user:
        return 403, {"detail": "Permission refusée"}
    
    return {
        'id': facture.id,
        'numero_facture': facture.numero_facture,
        'reference': facture.reference,
        'concession_id': facture.concession_id,
        'concession_numero': facture.concession.numero_contrat,
        'client_id': facture.client_id,
        'client_email': facture.client.email,
        'client_nom': facture.client.get_full_name(),
        'montant_ht': facture.montant_ht,
        'taux_tva': facture.taux_tva,
        'montant_tva': facture.montant_tva,
        'montant_total': facture.montant_total,
        'montant_paye': facture.montant_paye,
        'montant_restant': facture.montant_restant,
        'date_emission': facture.date_emission,
        'date_echeance': facture.date_echeance,
        'statut': facture.statut,
        'statut_display': facture.get_statut_display(),
        'email_envoye': facture.email_envoye,
        'est_payee': facture.est_payee(),
        'est_en_retard': facture.est_en_retard(),
    }


@router.post("/factures", response=MessageSchema, auth=AuthBearer())
def create_facture(request, payload: FactureCreateSchema):
    """Créer une nouvelle facture."""
    if not PermissionService.can_view_financial_stats(request.user):
        return 403, {
            "success": False,
            "message": "Permission refusée.",
            "data": None
        }
    
    from apps.core.models import Concession
    
    concession = get_object_or_404(Concession, id=payload.concession_id)
    client = get_object_or_404(request.user.__class__, id=payload.client_id)
    
    # Générer un numéro de facture unique
    numero_facture = f"FACT-{timezone.now().strftime('%Y%m%d')}-{Facture.objects.count() + 1:04d}"
    
    try:
        facture = Facture.objects.create(
            numero_facture=numero_facture,
            concession=concession,
            client=client,
            montant_ht=payload.montant_ht,
            taux_tva=payload.taux_tva,
            date_emission=payload.date_emission,
            date_echeance=payload.date_echeance,
            description=payload.description,
            notes=payload.notes,
            statut=Facture.StatutFacture.BROUILLON,
            cree_par=request.user,
        )
        
        # Créer une transaction financière
        TransactionFinanciere.objects.create(
            type_transaction=TransactionFinanciere.TypeTransaction.FACTURE_EMISE,
            montant=facture.montant_total,
            sens='ENTREE',
            facture=facture,
            client=client,
            description=f"Facture {numero_facture} émise pour concession {concession.numero_contrat}",
            enregistre_par=request.user,
        )
        
        logger.info(
            f"INVOICE_CREATED: numero={numero_facture}, "
            f"montant={facture.montant_total}, by={request.user.email}"
        )
        
        return {
            "success": True,
            "message": f"Facture {numero_facture} créée avec succès.",
            "data": {"facture_id": facture.id, "numero_facture": numero_facture}
        }
    
    except Exception as e:
        logger.error(f"INVOICE_CREATION_FAILED: {str(e)}")
        return 500, {
            "success": False,
            "message": f"Erreur lors de la création : {str(e)}",
            "data": None
        }


@router.put("/factures/{facture_id}", response=MessageSchema, auth=AuthBearer())
def update_facture(request, facture_id: int, payload: FactureUpdateSchema):
    """Mettre à jour une facture."""
    if not PermissionService.can_view_financial_stats(request.user):
        return 403, {
            "success": False,
            "message": "Permission refusée.",
            "data": None
        }
    
    facture = get_object_or_404(Facture, id=facture_id)
    
    if facture.statut == Facture.StatutFacture.PAYEE:
        return 400, {
            "success": False,
            "message": "Impossible de modifier une facture payée.",
            "data": None
        }
    
    # Mettre à jour les champs fournis
    for field, value in payload.dict(exclude_unset=True).items():
        if value is not None:
            setattr(facture, field, value)
    
    facture.save()
    
    logger.info(f"INVOICE_UPDATED: numero={facture.numero_facture}, by={request.user.email}")
    
    return {
        "success": True,
        "message": "Facture mise à jour avec succès.",
        "data": {"facture_id": facture.id}
    }


@router.post("/factures/{facture_id}/emettre", response=MessageSchema, auth=AuthBearer())
def emettre_facture(request, facture_id: int):
    """Émettre une facture (passer de BROUILLON à EMISE)."""
    if not PermissionService.can_view_financial_stats(request.user):
        return 403, {
            "success": False,
            "message": "Permission refusée.",
            "data": None
        }
    
    facture = get_object_or_404(Facture, id=facture_id)
    
    if facture.statut != Facture.StatutFacture.BROUILLON:
        return 400, {
            "success": False,
            "message": "Seules les factures en brouillon peuvent être émises.",
            "data": None
        }
    
    facture.statut = Facture.StatutFacture.EMISE
    facture.save()
    
    logger.info(f"INVOICE_ISSUED: numero={facture.numero_facture}, by={request.user.email}")
    
    return {
        "success": True,
        "message": f"Facture {facture.numero_facture} émise avec succès.",
        "data": {"facture_id": facture.id}
    }


@router.post("/factures/{facture_id}/annuler", response=MessageSchema, auth=AuthBearer())
def annuler_facture(request, facture_id: int, motif: str = ''):
    """Annuler une facture."""
    if not PermissionService.can_view_financial_stats(request.user):
        return 403, {
            "success": False,
            "message": "Permission refusée.",
            "data": None
        }
    
    facture = get_object_or_404(Facture, id=facture_id)
    
    if facture.statut == Facture.StatutFacture.PAYEE:
        return 400, {
            "success": False,
            "message": "Impossible d'annuler une facture payée.",
            "data": None
        }
    
    facture.annuler(motif or 'Annulation par administration', request.user)
    
    return {
        "success": True,
        "message": f"Facture {facture.numero_facture} annulée.",
        "data": {"facture_id": facture.id}
    }


# === ENDPOINTS : PAIEMENTS ===

@router.get("/paiements", response=List[PaiementSchema], auth=AuthBearer())
def list_paiements(request, statut: Optional[str] = None, facture_id: Optional[int] = None):
    """Lister tous les paiements."""
    if not PermissionService.can_view_financial_stats(request.user):
        return 403, {"detail": "Permission refusée"}
    
    queryset = Paiement.objects.select_related('facture', 'client').all()
    
    # Filtrer par client si demandé
    if request.user.is_client():
        queryset = queryset.filter(client=request.user)
    
    if facture_id:
        queryset = queryset.filter(facture_id=facture_id)
    
    if statut:
        queryset = queryset.filter(statut=statut)
    
    paiements_data = []
    for paiement in queryset:
        paiements_data.append({
            'id': paiement.id,
            'reference': paiement.reference,
            'numero_transaction': paiement.numero_transaction,
            'facture_id': paiement.facture_id,
            'facture_numero': paiement.facture.numero_facture,
            'client_id': paiement.client_id,
            'client_email': paiement.client.email,
            'montant': paiement.montant,
            'mode_paiement': paiement.mode_paiement,
            'mode_paiement_display': paiement.get_mode_paiement_display(),
            'reference_transaction': paiement.reference_transaction,
            'numero_telephone': paiement.numero_telephone,
            'statut': paiement.statut,
            'statut_display': paiement.get_statut_display(),
            'date_paiement': paiement.date_paiement,
            'date_validation': paiement.date_validation,
        })
    
    return paiements_data


@router.post("/paiements", response=MessageSchema, auth=AuthBearer())
def enregistrer_paiement(request, payload: PaiementCreateSchema):
    """Enregistrer un paiement."""
    facture = get_object_or_404(Facture, id=payload.facture_id)
    
    # Vérifier les permissions
    if not request.user.is_admin() and facture.client != request.user:
        return 403, {
            "success": False,
            "message": "Permission refusée.",
            "data": None
        }
    
    if facture.statut == Facture.StatutFacture.ANNULEE:
        return 400, {
            "success": False,
            "message": "Impossible de payer une facture annulée.",
            "data": None
        }
    
    # Vérifier que le montant ne dépasse pas le restant
    if payload.montant > facture.montant_restant:
        return 400, {
            "success": False,
            "message": f"Le montant dépasse le restant dû ({facture.montant_restant} FC).",
            "data": None
        }
    
    try:
        paiement = Paiement.objects.create(
            facture=facture,
            client=facture.client,
            montant=payload.montant,
            mode_paiement=payload.mode_paiement,
            reference_transaction=payload.reference_transaction,
            numero_telephone=payload.numero_telephone,
            statut=Paiement.StatutPaiement.EN_ATTENTE if not request.user.is_admin() else Paiement.StatutPaiement.VALIDE,
            notes=payload.notes,
        )
        
        # Si admin, valider automatiquement
        if request.user.is_admin():
            paiement.valider(request.user)
            
            # Mettre à jour le montant payé de la facture
            facture.montant_paye += paiement.montant
            facture.save()
            
            # Créer une transaction financière
            TransactionFinanciere.objects.create(
                type_transaction=TransactionFinanciere.TypeTransaction.PAIEMENT_RECUE,
                montant=paiement.montant,
                sens='ENTREE',
                facture=facture,
                paiement=paiement,
                client=facture.client,
                description=f"Paiement reçu pour facture {facture.numero_facture}",
                enregistre_par=request.user,
            )
        
        logger.info(
            f"PAYMENT_RECORDED: transaction={paiement.numero_transaction}, "
            f"montant={paiement.montant}, by={request.user.email}"
        )
        
        return {
            "success": True,
            "message": "Paiement enregistré avec succès.",
            "data": {
                "paiement_id": paiement.id,
                "numero_transaction": paiement.numero_transaction,
                "statut": paiement.statut
            }
        }
    
    except Exception as e:
        logger.error(f"PAYMENT_FAILED: {str(e)}")
        return 500, {
            "success": False,
            "message": f"Erreur lors de l'enregistrement : {str(e)}",
            "data": None
        }


@router.post("/paiements/{paiement_id}/valider", response=MessageSchema, auth=AuthBearer())
def valider_paiement(request, paiement_id: int):
    """Valider un paiement."""
    if not PermissionService.can_view_financial_stats(request.user):
        return 403, {
            "success": False,
            "message": "Permission refusée.",
            "data": None
        }
    
    paiement = get_object_or_404(Paiement, id=paiement_id)
    
    if paiement.statut != Paiement.StatutPaiement.EN_ATTENTE:
        return 400, {
            "success": False,
            "message": "Seuls les paiements en attente peuvent être validés.",
            "data": None
        }
    
    try:
        paiement.valider(request.user)
        
        # Mettre à jour le montant payé de la facture
        facture = paiement.facture
        facture.montant_paye += paiement.montant
        facture.save()
        
        # Créer une transaction financière
        TransactionFinanciere.objects.create(
            type_transaction=TransactionFinanciere.TypeTransaction.PAIEMENT_RECUE,
            montant=paiement.montant,
            sens='ENTREE',
            facture=facture,
            paiement=paiement,
            client=facture.client,
            description=f"Paiement validé pour facture {facture.numero_facture}",
            enregistre_par=request.user,
        )
        
        return {
            "success": True,
            "message": "Paiement validé avec succès.",
            "data": {"paiement_id": paiement.id}
        }
    
    except Exception as e:
        logger.error(f"PAYMENT_VALIDATION_FAILED: {str(e)}")
        return 500, {
            "success": False,
            "message": f"Erreur lors de la validation : {str(e)}",
            "data": None
        }


# === ENDPOINTS : STATISTIQUES FINANCIÈRES ===

@router.get("/statistiques", response=StatistiquesFinancieresSchema, auth=AuthBearer())
def get_statistiques_financieres(request):
    """Récupérer les statistiques financières."""
    if not PermissionService.can_view_financial_stats(request.user):
        return 403, {"detail": "Permission refusée"}
    
    # Statistiques des factures
    total_factures = Facture.objects.count()
    factures_payees = Facture.objects.filter(statut=Facture.StatutFacture.PAYEE).count()
    factures_en_retard = Facture.objects.filter(
        statut__in=[Facture.StatutFacture.EMISE, Facture.StatutFacture.PARTIELLEMENT_PAYEE],
        date_echeance__lt=timezone.now().date()
    ).count()
    factures_en_attente = Facture.objects.filter(
        statut__in=[Facture.StatutFacture.EMISE, Facture.StatutFacture.PARTIELLEMENT_PAYEE]
    ).count()
    
    # Revenus
    revenus_mois = Paiement.objects.filter(
        statut=Paiement.StatutPaiement.VALIDE,
        date_paiement__month=timezone.now().month,
        date_paiement__year=timezone.now().year
    ).aggregate(total=Sum('montant'))['total'] or Decimal('0.00')
    
    revenus_annee = Paiement.objects.filter(
        statut=Paiement.StatutPaiement.VALIDE,
        date_paiement__year=timezone.now().year
    ).aggregate(total=Sum('montant'))['total'] or Decimal('0.00')
    
    # Totaux
    total_recu = Paiement.objects.filter(
        statut=Paiement.StatutPaiement.VALIDE
    ).aggregate(total=Sum('montant'))['total'] or Decimal('0.00')
    
    total_restant = Facture.objects.filter(
        statut__in=[Facture.StatutFacture.EMISE, Facture.StatutFacture.PARTIELLEMENT_PAYEE]
    ).aggregate(total=Sum('montant_restant'))['total'] or Decimal('0.00')
    
    # Paiements par mode
    paiements_par_mode = {}
    for mode in Paiement.ModePaiement.choices:
        montant = Paiement.objects.filter(
            statut=Paiement.StatutPaiement.VALIDE,
            mode_paiement=mode[0]
        ).aggregate(total=Sum('montant'))['total'] or Decimal('0.00')
        paiements_par_mode[mode[1]] = str(montant)
    
    return {
        'total_factures': total_factures,
        'factures_payees': factures_payees,
        'factures_en_retard': factures_en_retard,
        'factures_en_attente': factures_en_attente,
        'revenus_mois': revenus_mois,
        'revenus_annee': revenus_annee,
        'total_recu': total_recu,
        'total_restant': total_restant,
        'paiements_par_mode': paiements_par_mode,
    }