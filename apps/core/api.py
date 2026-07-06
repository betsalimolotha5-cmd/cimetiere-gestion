"""
API Django Ninja pour le cœur métier : caveaux, concessions, cartographie.
"""
from ninja import Router, Schema, File, UploadedFile
from ninja.security import HttpBearer
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q, Count, Sum
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal
import logging

from .models import (
    ParametreCimetiere,
    Zone,
    Caveau,
    Defunt,
    Concession,
    Inhumation,
    DemandeExhumation,
)
from apps.accounts.services import PermissionService

router = Router(tags=["Cimetière"])
logger = logging.getLogger('audit')


# === AUTHENTIFICATION ===

class AuthBearer(HttpBearer):
    def authenticate(self, request, token):
        if token == "session_authenticated":
            return token
        return None


# === SCHÉMAS ===

# --- Paramètres ---
class ParametreCimetiereSchema(Schema):
    id: int
    nom: str
    adresse: str
    superficie_totale: Decimal
    longueur_standard_caveau: Decimal
    largeur_standard_caveau: Decimal
    largeur_allee: Decimal
    
    class Config:
        from_attributes = True


# --- Zones ---
class ZoneSchema(Schema):
    id: int
    code: str
    nom: str
    type_zone: str
    superficie: Optional[Decimal] = None
    est_exploitable: bool
    total_caveaux: int = 0
    caveaux_disponibles: int = 0
    
    class Config:
        from_attributes = True


class ZoneCreateSchema(Schema):
    code: str
    nom: str
    type_zone: str = Zone.TypeZone.SECTION
    superficie: Optional[Decimal] = None
    est_exploitable: bool = True


# --- Caveaux ---
class CaveauSchema(Schema):
    id: int
    code: str
    numero: str
    zone_id: int
    zone_code: str
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


class CaveauDetailSchema(Schema):
    id: int
    code: str
    numero: str
    zone: ZoneSchema
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
    notes: str
    date_creation: datetime
    date_modification: datetime
    
    class Config:
        from_attributes = True


class CaveauCreateSchema(Schema):
    code: str
    numero: str
    zone_id: int
    type_caveau: str = Caveau.TypeCaveau.INDIVIDUEL
    longueur: Decimal = Decimal('2.50')
    largeur: Decimal = Decimal('1.20')
    profondeur: Decimal = Decimal('1.50')
    prix_concession: Decimal = Decimal('0.00')
    prix_perpetuite: Decimal = Decimal('0.00')
    est_reservable: bool = True
    longitude: Optional[float] = None
    latitude: Optional[float] = None
    notes: str = ''


class CaveauUpdateSchema(Schema):
    type_caveau: Optional[str] = None
    statut: Optional[str] = None
    longueur: Optional[Decimal] = None
    largeur: Optional[Decimal] = None
    profondeur: Optional[Decimal] = None
    prix_concession: Optional[Decimal] = None
    prix_perpetuite: Optional[Decimal] = None
    est_reservable: Optional[bool] = None
    longitude: Optional[float] = None
    latitude: Optional[float] = None
    notes: Optional[str] = None


# --- Défunts ---
class DefuntSchema(Schema):
    id: int
    nom: str
    prenom: str
    date_naissance: Optional[date] = None
    date_deces: date
    lieu_deces: str
    nationalite: str
    numero_acte_deces: str
    
    class Config:
        from_attributes = True


class DefuntCreateSchema(Schema):
    nom: str
    prenom: str
    date_naissance: Optional[date] = None
    date_deces: date
    lieu_deces: str = ''
    nationalite: str = ''
    numero_acte_deces: str = ''
    notes: str = ''


# --- Concessions ---
class ConcessionSchema(Schema):
    id: int
    numero_contrat: str
    concessionnaire_id: int
    concessionnaire_email: str
    caveau_id: int
    caveau_code: str
    type_concession: str
    duree_annees: Optional[int] = None
    date_debut: date
    date_fin: Optional[date] = None
    date_signature: date
    statut: str
    statut_display: str
    montant_total: Decimal
    montant_paye: Decimal
    jours_restants: Optional[int] = None
    
    class Config:
        from_attributes = True


class ConcessionCreateSchema(Schema):
    concessionnaire_id: int
    caveau_id: int
    type_concession: str = Concession.TypeConcession.TEMPORAIRE
    duree_annees: Optional[int] = None
    date_debut: date
    date_signature: date
    montant_total: Decimal = Decimal('0.00')
    notes: str = ''


class ReservationSchema(Schema):
    caveau_id: int
    defunt_nom: str
    defunt_prenom: str
    defunt_date_naissance: Optional[date] = None
    defunt_date_deces: date
    defunt_lieu_deces: str = ''
    defunt_nationalite: str = ''
    defunt_numero_acte: str = ''
    duree_annees: int = 10
    type_concession: str = Concession.TypeConcession.TEMPORAIRE


# --- Inhumations ---
class InhumationSchema(Schema):
    id: int
    concession_id: int
    defunt_id: int
    defunt_nom: str
    defunt_prenom: str
    caveau_id: int
    caveau_code: str
    date_inhumation: datetime
    profondeur: Decimal
    numero_place_dans_caveau: str
    
    class Config:
        from_attributes = True


# --- Exhumations ---
class DemandeExhumationSchema(Schema):
    id: int
    demandeur_id: int
    demandeur_email: str
    nom_demandeur: str
    lien_parente: str
    telephone_demandeur: str
    inhumation_id: int
    defunt_nom: str
    defunt_prenom: str
    caveau_code: str
    motif: str
    destination: str
    statut: str
    statut_display: str
    date_demande: datetime
    date_validation: Optional[datetime] = None
    date_realisation: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class DemandeExhumationCreateSchema(Schema):
    inhumation_id: int
    nom_demandeur: str
    lien_parente: str
    telephone_demandeur: str
    motif: str
    destination: str


class MessageSchema(Schema):
    success: bool
    message: str
    data: Optional[dict] = None


class StatsSchema(Schema):
    total_caveaux: int
    caveaux_disponibles: int
    caveaux_reserves: int
    caveaux_occupes: int
    caveaux_non_exploitables: int
    taux_occupation: float
    concessions_actives: int
    concessions_expiring_soon: int
    revenus_mois: Decimal
    revenus_annee: Decimal


# === ENDPOINTS : PARAMÈTRES ===

@router.get("/parametres", response=ParametreCimetiereSchema)
def get_parametres(request):
    """Récupérer les paramètres du cimetière."""
    params = ParametreCimetiere.objects.first()
    if not params:
        return 404, {"detail": "Paramètres non configurés"}
    return params


# === ENDPOINTS : ZONES ===

@router.get("/zones", response=List[ZoneSchema])
def list_zones(request):
    """Lister toutes les zones."""
    zones = Zone.objects.annotate(
        total_caveaux=Count('caveaux'),
        caveaux_disponibles=Count(
            'caveaux',
            filter=Q(caveaux__statut=Caveau.Statut.DISPONIBLE)
        )
    ).order_by('code')
    return zones


@router.get("/zones/{zone_id}", response=ZoneSchema)
def get_zone(request, zone_id: int):
    """Récupérer les détails d'une zone."""
    zone = get_object_or_404(Zone, id=zone_id)
    zone.total_caveaux = zone.caveaux.count()
    zone.caveaux_disponibles = zone.caveaux.filter(
        statut=Caveau.Statut.DISPONIBLE
    ).count()
    return zone


@router.post("/zones", response=ZoneSchema, auth=AuthBearer())
def create_zone(request, payload: ZoneCreateSchema):
    """Créer une nouvelle zone."""
    if not PermissionService.can_manage_caveaux(request.user):
        return 403, {"detail": "Permission refusée"}
    
    if Zone.objects.filter(code=payload.code).exists():
        return 400, {"detail": "Ce code existe déjà"}
    
    zone = Zone.objects.create(
        code=payload.code,
        nom=payload.nom,
        type_zone=payload.type_zone,
        superficie=payload.superficie,
        est_exploitable=payload.est_exploitable,
    )
    
    logger.info(f"ZONE_CREATED: code={zone.code}, by={request.user.email}")
    
    return zone


# === ENDPOINTS : CAVEAUX ===

@router.get("/caveaux", response=List[CaveauSchema])
def list_caveaux(request, zone_id: Optional[int] = None, statut: Optional[str] = None):
    """Lister tous les caveaux avec filtres optionnels."""
    queryset = Caveau.objects.select_related('zone').all()
    
    if zone_id:
        queryset = queryset.filter(zone_id=zone_id)
    
    if statut:
        queryset = queryset.filter(statut=statut)
    
    caveaux_data = []
    for caveau in queryset:
        caveaux_data.append({
            'id': caveau.id,
            'code': caveau.code,
            'numero': caveau.numero,
            'zone_id': caveau.zone_id,
            'zone_code': caveau.zone.code,
            'type_caveau': caveau.type_caveau,
            'statut': caveau.statut,
            'statut_display': caveau.get_statut_display(),
            'longueur': caveau.longueur,
            'largeur': caveau.largeur,
            'profondeur': caveau.profondeur,
            'prix_concession': caveau.prix_concession,
            'prix_perpetuite': caveau.prix_perpetuite,
            'est_reservable': caveau.est_reservable(),
            'longitude': caveau.position_gps.x if caveau.position_gps else None,
            'latitude': caveau.position_gps.y if caveau.position_gps else None,
        })
    
    return caveaux_data


@router.get("/caveaux/{caveau_id}", response=CaveauDetailSchema)
def get_caveau(request, caveau_id: int):
    """Récupérer les détails d'un caveau."""
    caveau = get_object_or_404(Caveau.objects.select_related('zone'), id=caveau_id)
    return caveau


@router.post("/caveaux", response=CaveauSchema, auth=AuthBearer())
def create_caveau(request, payload: CaveauCreateSchema):
    """Créer un nouveau caveau."""
    if not PermissionService.can_manage_caveaux(request.user):
        return 403, {"detail": "Permission refusée"}
    
    if Caveau.objects.filter(code=payload.code).exists():
        return 400, {"detail": "Ce code existe déjà"}
    
    zone = get_object_or_404(Zone, id=payload.zone_id)
    
    # Créer le point GPS si coordonnées fournies
    position_gps = None
    if payload.longitude and payload.latitude:
        from django.contrib.gis.geos import Point
        position_gps = Point(payload.longitude, payload.latitude, srid=4326)
    
    caveau = Caveau.objects.create(
        code=payload.code,
        numero=payload.numero,
        zone=zone,
        type_caveau=payload.type_caveau,
        longueur=payload.longueur,
        largeur=payload.largeur,
        profondeur=payload.profondeur,
        prix_concession=payload.prix_concession,
        prix_perpetuite=payload.prix_perpetuite,
        est_reservable=payload.est_reservable,
        position_gps=position_gps,
        notes=payload.notes,
        cree_par=request.user,
    )
    
    logger.info(f"CAVEAU_CREATED: code={caveau.code}, by={request.user.email}")
    
    return {
        'id': caveau.id,
        'code': caveau.code,
        'numero': caveau.numero,
        'zone_id': caveau.zone_id,
        'zone_code': caveau.zone.code,
        'type_caveau': caveau.type_caveau,
        'statut': caveau.statut,
        'statut_display': caveau.get_statut_display(),
        'longueur': caveau.longueur,
        'largeur': caveau.largeur,
        'profondeur': caveau.profondeur,
        'prix_concession': caveau.prix_concession,
        'prix_perpetuite': caveau.prix_perpetuite,
        'est_reservable': caveau.est_reservable(),
        'longitude': caveau.position_gps.x if caveau.position_gps else None,
        'latitude': caveau.position_gps.y if caveau.position_gps else None,
    }


@router.put("/caveaux/{caveau_id}", response=CaveauSchema, auth=AuthBearer())
def update_caveau(request, caveau_id: int, payload: CaveauUpdateSchema):
    """Mettre à jour un caveau."""
    if not PermissionService.can_manage_caveaux(request.user):
        return 403, {"detail": "Permission refusée"}
    
    caveau = get_object_or_404(Caveau.objects.select_related('zone'), id=caveau_id)
    
    # Mettre à jour les champs fournis
    for field, value in payload.dict(exclude_unset=True).items():
        if value is not None:
            if field in ['longitude', 'latitude']:
                # Gérer les coordonnées GPS
                from django.contrib.gis.geos import Point
                if payload.longitude and payload.latitude:
                    caveau.position_gps = Point(payload.longitude, payload.latitude, srid=4326)
            else:
                setattr(caveau, field, value)
    
    caveau.save()
    
    logger.info(f"CAVEAU_UPDATED: code={caveau.code}, by={request.user.email}")
    
    return {
        'id': caveau.id,
        'code': caveau.code,
        'numero': caveau.numero,
        'zone_id': caveau.zone_id,
        'zone_code': caveau.zone.code,
        'type_caveau': caveau.type_caveau,
        'statut': caveau.statut,
        'statut_display': caveau.get_statut_display(),
        'longueur': caveau.longueur,
        'largeur': caveau.largeur,
        'profondeur': caveau.profondeur,
        'prix_concession': caveau.prix_concession,
        'prix_perpetuite': caveau.prix_perpetuite,
        'est_reservable': caveau.est_reservable(),
        'longitude': caveau.position_gps.x if caveau.position_gps else None,
        'latitude': caveau.position_gps.y if caveau.position_gps else None,
    }


# === ENDPOINTS : RÉSERVATIONS ===

@router.post("/reservations", response=MessageSchema, auth=AuthBearer())
def create_reservation(request, payload: ReservationSchema):
    """Créer une réservation de caveau."""
    caveau = get_object_or_404(Caveau, id=payload.caveau_id)
    
    # Vérifier que le caveau est disponible
    if not caveau.est_reservable():
        return 400, {
            "success": False,
            "message": "Ce caveau n'est pas disponible à la réservation.",
            "data": None
        }
    
    try:
        # Créer le défunt
        defunt = Defunt.objects.create(
            nom=payload.defunt_nom,
            prenom=payload.defunt_prenom,
            date_naissance=payload.defunt_date_naissance,
            date_deces=payload.defunt_date_deces,
            lieu_deces=payload.defunt_lieu_deces,
            nationalite=payload.defunt_nationalite,
            numero_acte_deces=payload.defunt_numero_acte,
        )
        
        # Passer le caveau en statut réservé
        caveau.reserver()
        
        # Créer la concession
        concession = Concession.objects.create(
            numero_contrat=f"RES-{caveau.code}-{timezone.now().strftime('%Y%m%d%H%M%S')}",
            concessionnaire=request.user,
            caveau=caveau,
            type_concession=payload.type_concession,
            duree_annees=payload.duree_annees if payload.type_concession == Concession.TypeConcession.TEMPORAIRE else None,
            date_debut=timezone.now().date(),
            date_signature=timezone.now().date(),
            statut=Concession.StatutConcession.ACTIVE,
            montant_total=caveau.prix_concession,
            cree_par=request.user,
        )
        
        # Créer l'inhumation prévisionnelle
        Inhumation.objects.create(
            concession=concession,
            defunt=defunt,
            caveau=caveau,
            date_inhumation=timezone.now(),
            enregistre_par=request.user,
        )
        
        logger.info(
            f"RESERVATION_CREATED: caveau={caveau.code}, "
            f"user={request.user.email}, concession={concession.numero_contrat}"
        )
        
        return {
            "success": True,
            "message": f"Réservation enregistrée pour le caveau {caveau.code}. En attente de validation.",
            "data": {
                "concession_id": concession.id,
                "numero_contrat": concession.numero_contrat,
                "caveau_code": caveau.code,
            }
        }
    
    except Exception as e:
        logger.error(f"RESERVATION_FAILED: {str(e)}")
        return 500, {
            "success": False,
            "message": f"Erreur lors de la réservation : {str(e)}",
            "data": None
        }


@router.post("/reservations/{concession_id}/valider", response=MessageSchema, auth=AuthBearer())
def valider_reservation(request, concession_id: int):
    """Valider une réservation (admin/secrétariat)."""
    if not PermissionService.can_validate_reservations(request.user):
        return 403, {
            "success": False,
            "message": "Permission refusée.",
            "data": None
        }
    
    concession = get_object_or_404(Concession, id=concession_id)
    
    try:
        # Valider le caveau
        concession.caveau.valider_reservation()
        
        logger.info(
            f"RESERVATION_VALIDATED: concession={concession.numero_contrat}, "
            f"by={request.user.email}"
        )
        
        return {
            "success": True,
            "message": f"La réservation {concession.numero_contrat} a été validée.",
            "data": {
                "concession_id": concession.id,
                "numero_contrat": concession.numero_contrat,
            }
        }
    
    except Exception as e:
        logger.error(f"VALIDATION_FAILED: {str(e)}")
        return 500, {
            "success": False,
            "message": f"Erreur lors de la validation : {str(e)}",
            "data": None
        }


# === ENDPOINTS : CONCESSIONS ===

@router.get("/concessions", response=List[ConcessionSchema], auth=AuthBearer())
def list_concessions(request, statut: Optional[str] = None, type_concession: Optional[str] = None):
    """Lister toutes les concessions."""
    if not PermissionService.can_manage_concessions(request.user):
        return 403, {"detail": "Permission refusée"}
    
    queryset = Concession.objects.select_related(
        'concessionnaire', 'caveau'
    ).all()
    
    if statut:
        queryset = queryset.filter(statut=statut)
    
    if type_concession:
        queryset = queryset.filter(type_concession=type_concession)
    
    concessions_data = []
    for concession in queryset:
        concessions_data.append({
            'id': concession.id,
            'numero_contrat': concession.numero_contrat,
            'concessionnaire_id': concession.concessionnaire_id,
            'concessionnaire_email': concession.concessionnaire.email,
            'caveau_id': concession.caveau_id,
            'caveau_code': concession.caveau.code,
            'type_concession': concession.type_concession,
            'duree_annees': concession.duree_annees,
            'date_debut': concession.date_debut,
            'date_fin': concession.date_fin,
            'date_signature': concession.date_signature,
            'statut': concession.statut,
            'statut_display': concession.get_statut_display(),
            'montant_total': concession.montant_total,
            'montant_paye': concession.montant_paye,
            'jours_restants': concession.jours_restants(),
        })
    
    return concessions_data


@router.get("/concessions/{concession_id}", response=ConcessionSchema, auth=AuthBearer())
def get_concession(request, concession_id: int):
    """Récupérer les détails d'une concession."""
    if not PermissionService.can_manage_concessions(request.user):
        return 403, {"detail": "Permission refusée"}
    
    concession = get_object_or_404(
        Concession.objects.select_related('concessionnaire', 'caveau'),
        id=concession_id
    )
    
    return {
        'id': concession.id,
        'numero_contrat': concession.numero_contrat,
        'concessionnaire_id': concession.concessionnaire_id,
        'concessionnaire_email': concession.concessionnaire.email,
        'caveau_id': concession.caveau_id,
        'caveau_code': concession.caveau.code,
        'type_concession': concession.type_concession,
        'duree_annees': concession.duree_annees,
        'date_debut': concession.date_debut,
        'date_fin': concession.date_fin,
        'date_signature': concession.date_signature,
        'statut': concession.statut,
        'statut_display': concession.get_statut_display(),
        'montant_total': concession.montant_total,
        'montant_paye': concession.montant_paye,
        'jours_restants': concession.jours_restants(),
    }


# === ENDPOINTS : EXHUMATIONS ===

@router.get("/exhumations", response=List[DemandeExhumationSchema], auth=AuthBearer())
def list_exhumations(request, statut: Optional[str] = None):
    """Lister toutes les demandes d'exhumation."""
    if not PermissionService.can_perform_exhumations(request.user):
        return 403, {"detail": "Permission refusée"}
    
    queryset = DemandeExhumation.objects.select_related(
        'demandeur', 'inhumation', 'inhumation__defunt', 'inhumation__caveau'
    ).all()
    
    if statut:
        queryset = queryset.filter(statut=statut)
    
    exhumations_data = []
    for demande in queryset:
        exhumations_data.append({
            'id': demande.id,
            'demandeur_id': demande.demandeur_id,
            'demandeur_email': demande.demandeur.email,
            'nom_demandeur': demande.nom_demandeur,
            'lien_parente': demande.lien_parente,
            'telephone_demandeur': demande.telephone_demandeur,
            'inhumation_id': demande.inhumation_id,
            'defunt_nom': demande.inhumation.defunt.nom,
            'defunt_prenom': demande.inhumation.defunt.prenom,
            'caveau_code': demande.inhumation.caveau.code,
            'motif': demande.motif,
            'destination': demande.destination,
            'statut': demande.statut,
            'statut_display': demande.get_statut_display(),
            'date_demande': demande.date_demande,
            'date_validation': demande.date_validation,
            'date_realisation': demande.date_realisation,
        })
    
    return exhumations_data


@router.post("/exhumations", response=MessageSchema, auth=AuthBearer())
def create_exhumation(request, payload: DemandeExhumationCreateSchema):
    """Créer une demande d'exhumation."""
    inhumation = get_object_or_404(Inhumation, id=payload.inhumation_id)
    
    demande = DemandeExhumation.objects.create(
        demandeur=request.user,
        nom_demandeur=payload.nom_demandeur,
        lien_parente=payload.lien_parente,
        telephone_demandeur=payload.telephone_demandeur,
        inhumation=inhumation,
        motif=payload.motif,
        destination=payload.destination,
    )
    
    logger.info(
        f"EXHUMATION_REQUESTED: id={demande.id}, "
        f"by={request.user.email}"
    )
    
    return {
        "success": True,
        "message": "Demande d'exhumation enregistrée. En attente de validation.",
        "data": {"demande_id": demande.id}
    }


@router.post("/exhumations/{demande_id}/valider", response=MessageSchema, auth=AuthBearer())
def valider_exhumation(request, demande_id: int):
    """Valider une demande d'exhumation."""
    if not PermissionService.can_perform_exhumations(request.user):
        return 403, {
            "success": False,
            "message": "Permission refusée.",
            "data": None
        }
    
    demande = get_object_or_404(DemandeExhumation, id=demande_id)
    
    try:
        demande.valider(request.user)
        
        return {
            "success": True,
            "message": "Demande d'exhumation validée.",
            "data": {"demande_id": demande.id}
        }
    
    except Exception as e:
        return 500, {
            "success": False,
            "message": f"Erreur : {str(e)}",
            "data": None
        }


# === ENDPOINTS : STATISTIQUES ===

@router.get("/statistiques", response=StatsSchema, auth=AuthBearer())
def get_statistiques(request):
    """Récupérer les statistiques globales."""
    if not PermissionService.can_view_financial_stats(request.user):
        return 403, {"detail": "Permission refusée"}
    
    # Statistiques des caveaux
    total_caveaux = Caveau.objects.count()
    caveaux_disponibles = Caveau.objects.filter(statut=Caveau.Statut.DISPONIBLE).count()
    caveaux_reserves = Caveau.objects.filter(statut=Caveau.Statut.RESERVE).count()
    caveaux_occupes = Caveau.objects.filter(statut=Caveau.Statut.OCCUPE).count()
    caveaux_non_exploitables = Caveau.objects.filter(statut=Caveau.Statut.NON_EXPLOITABLE).count()
    
    # Taux d'occupation
    taux_occupation = 0.0
    if total_caveaux > 0:
        taux_occupation = round((caveaux_occupes / total_caveaux) * 100, 2)
    
    # Concessions
    concessions_actives = Concession.objects.filter(
        statut=Concession.StatutConcession.ACTIVE
    ).count()
    
    concessions_expiring_soon = Concession.objects.filter(
        statut=Concession.StatutConcession.ACTIVE,
        date_fin__isnull=False,
        date_fin__lte=timezone.now().date() + timezone.timedelta(days=90)
    ).count()
    
    # Statistiques financières
    from apps.billing.models import Paiement
    
    revenus_mois = Paiement.objects.filter(
        date_paiement__month=timezone.now().month,
        date_paiement__year=timezone.now().year,
        statut='VALIDE'
    ).aggregate(total=Sum('montant'))['total'] or Decimal('0.00')
    
    revenus_annee = Paiement.objects.filter(
        date_paiement__year=timezone.now().year,
        statut='VALIDE'
    ).aggregate(total=Sum('montant'))['total'] or Decimal('0.00')
    
    return {
        'total_caveaux': total_caveaux,
        'caveaux_disponibles': caveaux_disponibles,
        'caveaux_reserves': caveaux_reserves,
        'caveaux_occupes': caveaux_occupes,
        'caveaux_non_exploitables': caveaux_non_exploitables,
        'taux_occupation': taux_occupation,
        'concessions_actives': concessions_actives,
        'concessions_expiring_soon': concessions_expiring_soon,
        'revenus_mois': revenus_mois,
        'revenus_annee': revenus_annee,
    }