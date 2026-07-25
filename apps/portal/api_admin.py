"""
API Admin pour la gestion des réservations et concessions.
Accessible uniquement aux administrateurs.
"""
from ninja import Router, Schema
from ninja.security import HttpBearer
from typing import Optional, List
from datetime import date, datetime, timedelta
from decimal import Decimal
from django.db.models import Q
from django.utils import timezone
import logging

from .models import DemandeReservation
from apps.core.models import Caveau, Concession, Defunt, Inhumation, Zone
from apps.accounts.models import User
from apps.billing.models import Facture

router = Router(tags=["Admin - Réservations"])
logger = logging.getLogger('audit')


class AuthBearer(HttpBearer):
    def authenticate(self, request, token):
        if token == "session_authenticated":
            return token
        return None


# === SCHÉMAS ===

class DemandeReservationSchema(Schema):
    id: int
    caveau_id: int
    caveau_code: str
    zone_nom: str
    defunt_nom: str
    defunt_prenom: str
    client_id: int
    client_email: str
    client_nom: str
    statut: str
    statut_display: str
    date_demande: datetime
    date_traitement: Optional[datetime] = None
    traite_par_id: Optional[int] = None
    traite_par_nom: Optional[str] = None
    motif_refus: Optional[str] = None
    telephone_contact: Optional[str] = None
    lien_parente: Optional[str] = None
    date_deces: Optional[date] = None
    
    class Config:
        from_attributes = True


class ConcessionSchema(Schema):
    id: int
    numero_contrat: str
    concessionnaire_id: int
    concessionnaire_email: str
    concessionnaire_nom: str
    caveau_id: int
    caveau_code: str
    defunt_id: Optional[int] = None
    defunt_nom: Optional[str] = None
    type_concession: str
    duree_annees: int
    date_debut: date
    date_fin: Optional[date] = None
    montant_total: Decimal
    montant_paye: Decimal
    statut: str
    statut_display: str
    date_signature: Optional[date] = None
    date_creation: datetime
    
    class Config:
        from_attributes = True


class CaveauAdminSchema(Schema):
    id: int
    code: str
    numero: str
    zone_id: int
    zone_nom: str
    type_caveau: str
    statut: str
    statut_display: str
    longueur: Decimal
    largeur: Decimal
    profondeur: Decimal
    prix_concession: Decimal
    prix_perpetuite: Decimal
    est_reservable: bool
    longitude: Optional[float] = None
    latitude: Optional[float] = None
    
    class Config:
        from_attributes = True


class ZoneAdminSchema(Schema):
    id: int
    code: str
    nom: str
    type_zone: str
    superficie: Optional[Decimal] = None
    est_exploitable: bool
    
    class Config:
        from_attributes = True


class DefuntAdminSchema(Schema):
    id: int
    nom: str
    prenom: str
    date_deces: Optional[date] = None
    sexe: Optional[str] = None
    numero_identite: Optional[str] = None
    lieu_naissance: Optional[str] = None
    
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


# === ENDPOINTS RÉSERVATIONS ===

@router.get("/reservations/", response=List[DemandeReservationSchema], auth=AuthBearer())
def list_reservations(request):
    """Liste toutes les demandes de réservation."""
    if not check_admin(request):
        return 403, {"success": False, "message": "Accès refusé."}
    
    reservations = DemandeReservation.objects.all().order_by('-date_demande').select_related(
        'caveau', 'caveau__zone', 'client', 'traite_par'
    )
    return list(reservations)


@router.get("/reservations/{reservation_id}", response=DemandeReservationSchema, auth=AuthBearer())
def get_reservation(request, reservation_id: int):
    """Récupère une demande de réservation spécifique."""
    if not check_admin(request):
        return 403, {"success": False, "message": "Accès refusé."}
    
    try:
        reservation = DemandeReservation.objects.select_related(
            'caveau', 'caveau__zone', 'client', 'traite_par'
        ).get(id=reservation_id)
        return reservation
    except DemandeReservation.DoesNotExist:
        return 404, {"success": False, "message": "Réservation introuvable."}


@router.post("/reservations/{reservation_id}/valider", response=MessageSchema, auth=AuthBearer())
def valider_reservation(request, reservation_id: int):
    """Valide une demande de réservation avec workflow complet."""
    if not check_admin(request):
        return 403, {"success": False, "message": "Accès refusé."}
    
    try:
        from apps.billing.pdf_generator import generer_facture_pdf, envoyer_facture_par_email
        from apps.notifications.services import NotificationService
        from apps.notifications.models import EmailLog
        
        reservation = DemandeReservation.objects.select_related('caveau', 'client').get(
            id=reservation_id,
            statut=DemandeReservation.Statut.EN_ATTENTE
        )
        
        # 1. Valider la demande
        reservation.valider(request.user)
        
        # 2. Réserver le caveau
        caveau = reservation.caveau
        caveau.statut = 'RESERVE'
        caveau.save()
        
        # 3. Créer le défunt
        defunt, _ = Defunt.objects.get_or_create(
            nom=reservation.defunt_nom,
            prenom=reservation.defunt_prenom,
            defaults={'date_deces': reservation.date_deces}
        )
        
        # 4. Créer la concession
        numero_contrat = f"CONC-{timezone.now().year}-{reservation.id:05d}"
        duree_annees = 30
        montant_total = caveau.prix_concession or Decimal('50000')
        
        concession = Concession.objects.create(
            numero_contrat=numero_contrat,
            concessionnaire=reservation.client,
            caveau=caveau,
            defunt=defunt,
            type_concession=Concession.TypeConcession.TEMPORAIRE,
            duree_annees=duree_annees,
            date_debut=timezone.now().date(),
            montant_total=montant_total,
            montant_paye=Decimal('0'),
            statut=Concession.StatutConcession.ACTIVE,
            cree_par=request.user,
            notes=f"Créée automatiquement suite à la réservation {reservation.id}"
        )
        
        # 5. Créer la facture
        numero_facture = f"FACT-{timezone.now().year}-{reservation.id:05d}"
        facture = Facture.objects.create(
            numero_facture=numero_facture,
            concession=concession,
            client=reservation.client,
            montant_ht=montant_total,
            taux_tva=Decimal('0'),
            date_emission=timezone.now().date(),
            date_echeance=timezone.now().date() + timedelta(days=30),
            statut=Facture.StatutFacture.EMISE,
            description=f"Concession funéraire - Caveau {caveau.code} - {defunt.prenom} {defunt.nom}",
            cree_par=request.user
        )
        
        # 6. Générer le PDF
        try:
            pdf_path = generer_facture_pdf(facture)
            facture.fichier_pdf = pdf_path
            facture.save(update_fields=['fichier_pdf'])
        except Exception as e:
            logger.warning(f"PDF generation failed: {str(e)}")
        
        # 7. Envoyer la facture par email
        try:
            if envoyer_facture_par_email(facture):
                facture.email_envoye = True
                facture.date_envoi_email = timezone.now()
                facture.save(update_fields=['email_envoye', 'date_envoi_email'])
        except Exception as e:
            logger.warning(f"Email sending failed: {str(e)}")
        
        # 8. Notifier le client
        try:
            client = reservation.client
            sujet = f"✅ Votre demande de réservation a été validée - {concession.numero_contrat}"
            
            contenu_html = f"""
            <html><body>
                <h2>✅ Votre demande a été validée</h2>
                <p>Bonjour {client.get_full_name() or client.email},</p>
                <p>Votre demande de réservation pour le caveau <strong>{caveau.code}</strong> a été approuvée.</p>
                <p><strong>N° de contrat:</strong> {concession.numero_contrat}</p>
                <p><strong>N° de facture:</strong> {facture.numero_facture}</p>
                <p><strong>Montant:</strong> {facture.montant_total:,.0f} FCFA</p>
                <p>Votre facture PDF est en pièce jointe.</p>
            </body></html>
            """
            
            NotificationService.envoyer_email(
                destinataire=client.email,
                sujet=sujet,
                contenu_html=contenu_html,
                type_email=EmailLog.TypeEmail.AUTRE,
                utilisateur=client
            )
            
            NotificationService.creer_notification(
                utilisateur=client,
                titre='Demande de réservation validée',
                message=f'Votre demande pour le caveau {caveau.code} a été validée. Concession {concession.numero_contrat} créée.',
                url_lien='/portal/mes-factures/'
            )
        except Exception as e:
            logger.warning(f"Notification failed: {str(e)}")
        
        logger.info(f"ADMIN_RESERVATION_VALIDATED: reservation={reservation.id}, concession={concession.numero_contrat}")
        
        return {
            "success": True,
            "message": f"Réservation validée. Concession {concession.numero_contrat} et facture {facture.numero_facture} créées.",
            "data": {
                "concession_id": concession.id,
                "facture_id": facture.id
            }
        }
    except DemandeReservation.DoesNotExist:
        return 404, {"success": False, "message": "Réservation introuvable ou déjà traitée."}
    except Exception as e:
        logger.error(f"ADMIN_RESERVATION_VALIDATE_FAILED: error={str(e)}")
        return 500, {"success": False, "message": f"Erreur: {str(e)}"}


@router.post("/reservations/{reservation_id}/refuser", response=MessageSchema, auth=AuthBearer())
def refuser_reservation(request, reservation_id: int, motif: str = "Refusé par l'administration"):
    """Refuse une demande de réservation."""
    if not check_admin(request):
        return 403, {"success": False, "message": "Accès refusé."}
    
    try:
        from apps.notifications.services import NotificationService
        from apps.notifications.models import EmailLog
        
        reservation = DemandeReservation.objects.select_related('caveau', 'client').get(
            id=reservation_id,
            statut=DemandeReservation.Statut.EN_ATTENTE
        )
        
        # Refuser la demande
        reservation.refuser(request.user, motif=motif)
        
        # Notifier le client
        client = reservation.client
        sujet = f"❌ Votre demande de réservation a été refusée - Caveau {reservation.caveau.code}"
        
        contenu_html = f"""
        <html><body>
            <h2>❌ Votre demande a été refusée</h2>
            <p>Bonjour {client.get_full_name() or client.email},</p>
            <p>Votre demande de réservation pour le caveau <strong>{reservation.caveau.code}</strong> a été refusée.</p>
            <p><strong>Motif:</strong> {motif}</p>
        </body></html>
        """
        
        NotificationService.envoyer_email(
            destinataire=client.email,
            sujet=sujet,
            contenu_html=contenu_html,
            type_email=EmailLog.TypeEmail.AUTRE,
            utilisateur=client
        )
        
        NotificationService.creer_notification(
            utilisateur=client,
            titre='Demande de réservation refusée',
            message=f'Votre demande pour le caveau {reservation.caveau.code} a été refusée.',
            url_lien='/portal/mes-reservations/'
        )
        
        logger.info(f"ADMIN_RESERVATION_REFUSED: reservation={reservation.id}, motif={motif}")
        
        return {
            "success": True,
            "message": f"Réservation refusée. Client notifié.",
            "data": None
        }
    except DemandeReservation.DoesNotExist:
        return 404, {"success": False, "message": "Réservation introuvable ou déjà traitée."}
    except Exception as e:
        logger.error(f"ADMIN_RESERVATION_REFUSE_FAILED: error={str(e)}")
        return 500, {"success": False, "message": f"Erreur: {str(e)}"}


@router.post("/reservations/bulk-valider", response=MessageSchema, auth=AuthBearer())
def bulk_valider_reservations(request, reservation_ids: List[int]):
    """Valide plusieurs réservations en masse."""
    if not check_admin(request):
        return 403, {"success": False, "message": "Accès refusé."}
    
    try:
        count = 0
        erreurs = []
        
        for reservation_id in reservation_ids:
            try:
                reservation = DemandeReservation.objects.get(
                    id=reservation_id,
                    statut=DemandeReservation.Statut.EN_ATTENTE
                )
                # Appeler la validation individuelle
                result = valider_reservation(request, reservation_id)
                if result[0] == 200:
                    count += 1
            except Exception as e:
                erreurs.append(f"Réservation #{reservation_id}: {str(e)}")
        
        logger.info(f"ADMIN_BULK_VALIDATE: count={count}, errors={len(erreurs)}")
        
        return {
            "success": True,
            "message": f"{count} réservation(s) validée(s). {len(erreurs)} erreur(s).",
            "data": {"success_count": count, "error_count": len(erreurs), "errors": erreurs}
        }
    except Exception as e:
        logger.error(f"ADMIN_BULK_VALIDATE_FAILED: error={str(e)}")
        return 500, {"success": False, "message": f"Erreur: {str(e)}"}


# === ENDPOINTS CONCESSIONS ===

@router.get("/concessions/", response=List[ConcessionSchema], auth=AuthBearer())
def list_concessions(request):
    """Liste toutes les concessions."""
    if not check_admin(request):
        return 403, {"success": False, "message": "Accès refusé."}
    
    concessions = Concession.objects.all().order_by('-date_creation').select_related(
        'concessionnaire', 'caveau', 'caveau__zone', 'defunt'
    )
    return list(concessions)


@router.get("/concessions/{concession_id}", response=ConcessionSchema, auth=AuthBearer())
def get_concession(request, concession_id: int):
    """Récupère une concession spécifique."""
    if not check_admin(request):
        return 403, {"success": False, "message": "Accès refusé."}
    
    try:
        concession = Concession.objects.select_related(
            'concessionnaire', 'caveau', 'caveau__zone', 'defunt'
        ).get(id=concession_id)
        return concession
    except Concession.DoesNotExist:
        return 404, {"success": False, "message": "Concession introuvable."}


# === ENDPOINTS CAVEAUX ===

@router.get("/caveaux-admin/", response=List[CaveauAdminSchema], auth=AuthBearer())
def list_caveaux_admin(request):
    """Liste tous les caveaux (version admin avec plus de détails)."""
    if not check_admin(request):
        return 403, {"success": False, "message": "Accès refusé."}
    
    caveaux = Caveau.objects.all().order_by('code').select_related('zone')
    return list(caveaux)


@router.get("/caveaux-admin/{caveau_id}", response=CaveauAdminSchema, auth=AuthBearer())
def get_caveau_admin(request, caveau_id: int):
    """Récupère un caveau spécifique."""
    if not check_admin(request):
        return 403, {"success": False, "message": "Accès refusé."}
    
    try:
        caveau = Caveau.objects.select_related('zone').get(id=caveau_id)
        return caveau
    except Caveau.DoesNotExist:
        return 404, {"success": False, "message": "Caveau introuvable."}


@router.post("/caveaux-admin/", response=MessageSchema, auth=AuthBearer())
def create_caveau(request, payload: CaveauAdminSchema):
    """Crée un nouveau caveau."""
    if not check_admin(request):
        return 403, {"success": False, "message": "Accès refusé."}
    
    try:
        zone = Zone.objects.get(id=payload.zone_id)
        
        caveau = Caveau.objects.create(
            code=payload.code,
            numero=payload.numero,
            zone=zone,
            type_caveau=payload.type_caveau,
            statut=payload.statut,
            longueur=payload.longueur,
            largeur=payload.largeur,
            profondeur=payload.profondeur,
            prix_concession=payload.prix_concession,
            prix_perpetuite=payload.prix_perpetuite,
            est_reservable=payload.est_reservable
        )
        
        logger.info(f"ADMIN_CAVEAU_CREATED: caveau={caveau.code}, zone={zone.nom}")
        
        return {
            "success": True,
            "message": f"Caveau {caveau.code} créé avec succès.",
            "data": {"caveau_id": caveau.id}
        }
    except Zone.DoesNotExist:
        return 400, {"success": False, "message": "Zone introuvable."}
    except Exception as e:
        logger.error(f"ADMIN_CAVEAU_CREATE_FAILED: error={str(e)}")
        return 500, {"success": False, "message": f"Erreur: {str(e)}"}


@router.put("/caveaux-admin/{caveau_id}", response=MessageSchema, auth=AuthBearer())
def update_caveau(request, caveau_id: int, payload: CaveauAdminSchema):
    """Met à jour un caveau."""
    if not check_admin(request):
        return 403, {"success": False, "message": "Accès refusé."}
    
    try:
        caveau = Caveau.objects.get(id=caveau_id)
        
        if payload.code:
            caveau.code = payload.code
        if payload.numero:
            caveau.numero = payload.numero
        if payload.zone_id:
            caveau.zone = Zone.objects.get(id=payload.zone_id)
        if payload.type_caveau:
            caveau.type_caveau = payload.type_caveau
        if payload.statut:
            caveau.statut = payload.statut
        if payload.longueur is not None:
            caveau.longueur = payload.longueur
        if payload.largeur is not None:
            caveau.largeur = payload.largeur
        if payload.profondeur is not None:
            caveau.profondeur = payload.profondeur
        if payload.prix_concession is not None:
            caveau.prix_concession = payload.prix_concession
        if payload.prix_perpetuite is not None:
            caveau.prix_perpetuite = payload.prix_perpetuite
        if payload.est_reservable is not None:
            caveau.est_reservable = payload.est_reservable
        
        caveau.save()
        
        logger.info(f"ADMIN_CAVEAU_UPDATED: caveau={caveau.code}")
        
        return {
            "success": True,
            "message": f"Caveau {caveau.code} mis à jour.",
            "data": {"caveau_id": caveau.id}
        }
    except Caveau.DoesNotExist:
        return 404, {"success": False, "message": "Caveau introuvable."}
    except Zone.DoesNotExist:
        return 400, {"success": False, "message": "Zone introuvable."}
    except Exception as e:
        logger.error(f"ADMIN_CAVEAU_UPDATE_FAILED: error={str(e)}")
        return 500, {"success": False, "message": f"Erreur: {str(e)}"}


# === ENDPOINTS ZONES ===

@router.get("/zones-admin/", response=List[ZoneAdminSchema], auth=AuthBearer())
def list_zones_admin(request):
    """Liste toutes les zones."""
    if not check_admin(request):
        return 403, {"success": False, "message": "Accès refusé."}
    
    zones = Zone.objects.all().order_by('nom')
    return list(zones)


@router.post("/zones-admin/", response=MessageSchema, auth=AuthBearer())
def create_zone(request, payload: ZoneAdminSchema):
    """Crée une nouvelle zone."""
    if not check_admin(request):
        return 403, {"success": False, "message": "Accès refusé."}
    
    try:
        zone = Zone.objects.create(
            code=payload.code,
            nom=payload.nom,
            type_zone=payload.type_zone,
            superficie=payload.superficie,
            est_exploitable=payload.est_exploitable
        )
        
        logger.info(f"ADMIN_ZONE_CREATED: zone={zone.nom}")
        
        return {
            "success": True,
            "message": f"Zone {zone.nom} créée avec succès.",
            "data": {"zone_id": zone.id}
        }
    except Exception as e:
        logger.error(f"ADMIN_ZONE_CREATE_FAILED: error={str(e)}")
        return 500, {"success": False, "message": f"Erreur: {str(e)}"}


# === ENDPOINTS DÉFUNTS ===

@router.get("/defunts-admin/", response=List[DefuntAdminSchema], auth=AuthBearer())
def list_defunts_admin(request):
    """Liste tous les défunts."""
    if not check_admin(request):
        return 403, {"success": False, "message": "Accès refusé."}
    
    defunts = Defunt.objects.all().order_by('nom', 'prenom')
    return list(defunts)


@router.post("/defunts-admin/", response=MessageSchema, auth=AuthBearer())
def create_defunt(request, payload: DefuntAdminSchema):
    """Crée un nouveau défunt."""
    if not check_admin(request):
        return 403, {"success": False, "message": "Accès refusé."}
    
    try:
        defunt = Defunt.objects.create(
            nom=payload.nom,
            prenom=payload.prenom,
            date_deces=payload.date_deces,
            sexe=payload.sexe,
            numero_identite=payload.numero_identite,
            lieu_naissance=payload.lieu_naissance
        )
        
        logger.info(f"ADMIN_DEFUNT_CREATED: defunt={defunt.nom} {defunt.prenom}")
        
        return {
            "success": True,
            "message": f"Défunt {defunt.nom} {defunt.prenom} créé avec succès.",
            "data": {"defunt_id": defunt.id}
        }
    except Exception as e:
        logger.error(f"ADMIN_DEFUNT_CREATE_FAILED: error={str(e)}")
        return 500, {"success": False, "message": f"Erreur: {str(e)}"}


# === STATISTIQUES ===

@router.get("/statistiques-cimetiere/", auth=AuthBearer())
def get_statistiques_cimetiere(request):
    """Récupère les statistiques du cimetière."""
    if not check_admin(request):
        return 403, {"success": False, "message": "Accès refusé."}
    
    from django.db.models import Count
    
    # Caveaux
    total_caveaux = Caveau.objects.count()
    caveaux_disponibles = Caveau.objects.filter(statut='DISPONIBLE').count()
    caveaux_occupes = Caveau.objects.filter(statut='OCCUPE').count()
    caveaux_reserves = Caveau.objects.filter(statut='RESERVE').count()
    
    # Concessions
    concessions_actives = Concession.objects.filter(statut='ACTIVE').count()
    concessions_expirées = Concession.objects.filter(statut='EXPIREE').count()
    
    # Réservations
    reservations_en_attente = DemandeReservation.objects.filter(statut='EN_ATTENTE').count()
    reservations_validees = DemandeReservation.objects.filter(statut='VALIDEE').count()
    
    # Zones
    zones_exploitables = Zone.objects.filter(est_exploitable=True).count()
    
    return {
        "total_caveaux": total_caveaux,
        "caveaux_disponibles": caveaux_disponibles,
        "caveaux_occupes": caveaux_occupes,
        "caveaux_reserves": caveaux_reserves,
        "taux_occupation": (caveaux_occupes / total_caveaux * 100) if total_caveaux > 0 else 0,
        "concessions_actives": concessions_actives,
        "concessions_expirées": concessions_expirées,
        "reservations_en_attente": reservations_en_attente,
        "reservations_validees": reservations_validees,
        "zones_exploitables": zones_exploitables
    }
