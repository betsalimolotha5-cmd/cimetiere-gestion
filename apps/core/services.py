"""
Services métier pour le cœur de l'application : caveaux, concessions, exhumations.
"""
from django.utils import timezone
from django.db import transaction
from django.db.models import Q, Count, Sum, Avg
from django.contrib.gis.geos import Point, Polygon
from decimal import Decimal
from datetime import timedelta
from typing import Optional, List, Dict, Any
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
from apps.accounts.models import User

logger = logging.getLogger('audit')


class CaveauService:
    """Service de gestion des caveaux."""
    
    @staticmethod
    @transaction.atomic
    def creer_caveau(
        code: str,
        numero: str,
        zone: Zone,
        type_caveau: str = Caveau.TypeCaveau.CAVEAU,
        longueur: Decimal = Decimal('2.50'),
        largeur: Decimal = Decimal('1.20'),
        profondeur: Decimal = Decimal('1.50'),
        prix_concession: Decimal = Decimal('0.00'),
        prix_perpetuite: Decimal = Decimal('0.00'),
        longitude: Optional[float] = None,
        latitude: Optional[float] = None,
        notes: str = '',
        cree_par: Optional[User] = None
    ) -> Caveau:
        """Crée un nouveau caveau."""
        if Caveau.objects.filter(code=code).exists():
            raise ValueError(f"Un caveau avec le code {code} existe déjà.")
        
        position_gps = None
        if longitude and latitude:
            position_gps = Point(longitude, latitude, srid=4326)
        
        caveau = Caveau.objects.create(
            code=code,
            numero=numero,
            zone=zone,
            type_caveau=type_caveau,
            longueur=longueur,
            largeur=largeur,
            profondeur=profondeur,
            prix_concession=prix_concession,
            prix_perpetuite=prix_perpetuite,
            position_gps=position_gps,
            notes=notes,
            statut=Caveau.Statut.DISPONIBLE,
            cree_par=cree_par,
        )
        
        logger.info(f"CAVEAU_CREATED: code={code}, zone={zone.code}, by={cree_par.email if cree_par else 'system'}")
        
        return caveau
    
    @staticmethod
    @transaction.atomic
    def reserver_caveau(caveau: Caveau, user: User) -> Caveau:
        """Réserve un caveau (passe en statut RESERVE)."""
        if not caveau.est_disponible():
            raise ValueError(f"Le caveau {caveau.code} n'est pas disponible.")
        
        caveau.statut = Caveau.Statut.RESERVE
        caveau.save(update_fields=['statut', 'date_modification'])
        
        logger.info(f"CAVEAU_RESERVED: code={caveau.code}, by={user.email}")
        
        return caveau
    
    @staticmethod
    @transaction.atomic
    def valider_reservation(caveau: Caveau, user: User) -> Caveau:
        """Valide une réservation (passe en statut OCCUPE)."""
        if caveau.statut != Caveau.Statut.RESERVE:
            raise ValueError(f"Le caveau {caveau.code} n'est pas en attente de validation.")
        
        caveau.statut = Caveau.Statut.OCCUPE
        caveau.save(update_fields=['statut', 'date_modification'])
        
        logger.info(f"CAVEAU_VALIDATED: code={caveau.code}, by={user.email}")
        
        return caveau
    
    @staticmethod
    @transaction.atomic
    def liberer_caveau(caveau: Caveau, user: User) -> Caveau:
        """Libère un caveau (passe en statut DISPONIBLE)."""
        caveau.statut = Caveau.Statut.DISPONIBLE
        caveau.save(update_fields=['statut', 'date_modification'])
        
        logger.info(f"CAVEAU_FREED: code={caveau.code}, by={user.email}")
        
        return caveau
    
    @staticmethod
    def get_caveaux_disponibles(zone: Optional[Zone] = None) -> List[Caveau]:
        """Récupère la liste des caveaux disponibles."""
        queryset = Caveau.objects.filter(statut=Caveau.Statut.DISPONIBLE, est_reservable=True)
        
        if zone:
            queryset = queryset.filter(zone=zone)
        
        return list(queryset.order_by('zone', 'code'))
    
    @staticmethod
    def get_statistiques_zone(zone: Zone) -> Dict[str, int]:
        """Calcule les statistiques d'une zone."""
        caveaux = zone.caveaux.all()
        
        return {
            'total': caveaux.count(),
            'disponibles': caveaux.filter(statut=Caveau.Statut.DISPONIBLE).count(),
            'reserves': caveaux.filter(statut=Caveau.Statut.RESERVE).count(),
            'occupes': caveaux.filter(statut=Caveau.Statut.OCCUPE).count(),
            'non_exploitables': caveaux.filter(statut=Caveau.Statut.NON_EXPLOITABLE).count(),
        }


class ConcessionService:
    """Service de gestion des concessions."""
    
    @staticmethod
    @transaction.atomic
    def creer_concession(
        concessionnaire: User,
        caveau: Caveau,
        type_concession: str,
        duree_annees: Optional[int],
        montant_total: Decimal,
        date_debut: Optional[Any] = None,
        notes: str = '',
        cree_par: Optional[User] = None
    ) -> Concession:
        """Crée une nouvelle concession."""
        if not caveau.est_disponible():
            raise ValueError(f"Le caveau {caveau.code} n'est pas disponible.")
        
        if type_concession == Concession.TypeConcession.TEMPORAIRE and not duree_annees:
            raise ValueError("La durée est obligatoire pour les concessions temporaires.")
        
        # Générer un numéro de contrat unique
        numero_contrat = f"CON-{caveau.code}-{timezone.now().strftime('%Y%m%d%H%M%S')}"
        
        if date_debut is None:
            date_debut = timezone.now().date()
        
        concession = Concession.objects.create(
            numero_contrat=numero_contrat,
            concessionnaire=concessionnaire,
            caveau=caveau,
            type_concession=type_concession,
            duree_annees=duree_annees,
            date_debut=date_debut,
            date_signature=date_debut,
            statut=Concession.StatutConcession.ACTIVE,
            montant_total=montant_total,
            notes=notes,
            cree_par=cree_par,
        )
        
        # Réserver le caveau
        CaveauService.reserver_caveau(caveau, concessionnaire)
        
        logger.info(
            f"CONCESSION_CREATED: numero={numero_contrat}, "
            f"caveau={caveau.code}, by={cree_par.email if cree_par else 'system'}"
        )
        
        return concession
    
    @staticmethod
    @transaction.atomic
    def valider_concession(concession: Concession, user: User) -> Concession:
        """Valide une concession (passe le caveau en OCCUPE)."""
        if concession.caveau.statut != Caveau.Statut.RESERVE:
            raise ValueError(f"Le caveau {concession.caveau.code} n'est pas en attente de validation.")
        
        CaveauService.valider_reservation(concession.caveau, user)
        
        logger.info(
            f"CONCESSION_VALIDATED: numero={concession.numero_contrat}, "
            f"by={user.email}"
        )
        
        return concession
    
    @staticmethod
    @transaction.atomic
    def renouveler_concession(
        concession: Concession,
        nouvelle_duree: int,
        nouveau_montant: Decimal,
        user: User
    ) -> Concession:
        """Renouvelle une concession existante."""
        if concession.type_concession == Concession.TypeConcession.PERPETUELLE:
            raise ValueError("Impossible de renouveler une concession perpétuelle.")
        
        if not concession.est_active():
            raise ValueError("La concession n'est plus active.")
        
        nouvelle_concession = concession.renouveler(nouvelle_duree)
        nouvelle_concession.montant_total = nouveau_montant
        nouvelle_concession.save()
        
        logger.info(
            f"CONCESSION_RENEWED: old={concession.numero_contrat}, "
            f"new={nouvelle_concession.numero_contrat}, by={user.email}"
        )
        
        return nouvelle_concession
    
    @staticmethod
    @transaction.atomic
    def resilier_concession(concession: Concession, motif: str, user: User) -> Concession:
        """Résilié une concession."""
        concession.statut = Concession.StatutConcession.RESILIEE
        concession.notes = f"{concession.notes}\nRésilée: {motif}"
        concession.save()
        
        # Libérer le caveau s'il n'y a plus d'inhumations actives
        inhumations_actives = concession.inhumations.count()
        if inhumations_actives == 0:
            CaveauService.liberer_caveau(concession.caveau, user)
        
        logger.info(
            f"CONCESSION_CANCELLED: numero={concession.numero_contrat}, "
            f"motif={motif}, by={user.email}"
        )
        
        return concession
    
    @staticmethod
    def get_concessions_expiring_soon(jours: int = 90) -> List[Concession]:
        """Récupère les concessions qui expirent bientôt."""
        date_limite = timezone.now().date() + timedelta(days=jours)
        
        return list(
            Concession.objects.filter(
                statut=Concession.StatutConcession.ACTIVE,
                type_concession=Concession.TypeConcession.TEMPORAIRE,
                date_fin__isnull=False,
                date_fin__lte=date_limite
            ).select_related('concessionnaire', 'caveau').order_by('date_fin')
        )
    
    @staticmethod
    def get_concessions_expirees() -> List[Concession]:
        """Récupère les concessions expirées."""
        return list(
            Concession.objects.filter(
                statut=Concession.StatutConcession.ACTIVE,
                type_concession=Concession.TypeConcession.TEMPORAIRE,
                date_fin__lt=timezone.now().date()
            ).select_related('concessionnaire', 'caveau')
        )


class InhumationService:
    """Service de gestion des inhumations."""
    
    @staticmethod
    @transaction.atomic
    def enregistrer_inhumation(
        concession: Concession,
        defunt: Defunt,
        caveau: Caveau,
        profondeur: Decimal = Decimal('1.50'),
        numero_place: str = '',
        notes: str = '',
        enregistre_par: Optional[User] = None
    ) -> Inhumation:
        """Enregistre une inhumation."""
        if concession.caveau != caveau:
            raise ValueError("Le caveau ne correspond pas à la concession.")
        
        if caveau.statut not in [Caveau.Statut.RESERVE, Caveau.Statut.OCCUPE]:
            raise ValueError(f"Le caveau {caveau.code} n'est pas disponible pour une inhumation.")
        
        inhumation = Inhumation.objects.create(
            concession=concession,
            defunt=defunt,
            caveau=caveau,
            profondeur=profondeur,
            numero_place_dans_caveau=numero_place,
            notes=notes,
            enregistre_par=enregistre_par,
        )
        
        # Valider la concession si ce n'est pas déjà fait
        if caveau.statut == Caveau.Statut.RESERVE:
            CaveauService.valider_reservation(caveau, enregistre_par)
        
        logger.info(
            f"INHUMATION_RECORDED: defunt={defunt}, caveau={caveau.code}, "
            f"by={enregistre_par.email if enregistre_par else 'system'}"
        )
        
        return inhumation


class ExhumationService:
    """Service de gestion des exhumations."""
    
    @staticmethod
    @transaction.atomic
    def creer_demande_exhumation(
        demandeur: User,
        inhumation: Inhumation,
        nom_demandeur: str,
        lien_parente: str,
        telephone_demandeur: str,
        motif: str,
        destination: str
    ) -> DemandeExhumation:
        """Crée une demande d'exhumation."""
        demande = DemandeExhumation.objects.create(
            demandeur=demandeur,
            inhumation=inhumation,
            nom_demandeur=nom_demandeur,
            lien_parente=lien_parente,
            telephone_demandeur=telephone_demandeur,
            motif=motif,
            destination=destination,
        )
        
        logger.info(
            f"EXHUMATION_REQUESTED: id={demande.id}, "
            f"defunt={inhumation.defunt}, by={demandeur.email}"
        )
        
        return demande
    
    @staticmethod
    @transaction.atomic
    def valider_demande(demande: DemandeExhumation, validateur: User) -> DemandeExhumation:
        """Valide une demande d'exhumation."""
        demande.valider(validateur)
        
        logger.info(
            f"EXHUMATION_VALIDATED: id={demande.id}, by={validateur.email}"
        )
        
        return demande
    
    @staticmethod
    @transaction.atomic
    def refuser_demande(demande: DemandeExhumation, motif: str, validateur: User) -> DemandeExhumation:
        """Refuse une demande d'exhumation."""
        demande.refuser(motif, validateur)
        
        logger.info(
            f"EXHUMATION_REFUSED: id={demande.id}, by={validateur.email}"
        )
        
        return demande
    
    @staticmethod
    @transaction.atomic
    def realiser_exhumation(demande: DemandeExhumation, user: User) -> DemandeExhumation:
        """Marque une exhumation comme réalisée."""
        demande.marquer_realisee()
        
        logger.info(
            f"EXHUMATION_COMPLETED: id={demande.id}, by={user.email}"
        )
        
        return demande


class CartographieService:
    """Service de gestion de la cartographie."""
    
    @staticmethod
    def get_caveaux_geojson(zone: Optional[Zone] = None) -> Dict[str, Any]:
        """Génère les données GeoJSON pour la carte."""
        queryset = Caveau.objects.select_related('zone').filter(
            position_gps__isnull=False
        )
        
        if zone:
            queryset = queryset.filter(zone=zone)
        
        features = []
        for caveau in queryset:
            feature = {
                'type': 'Feature',
                'geometry': {
                    'type': 'Point',
                    'coordinates': [
                        caveau.position_gps.x,
                        caveau.position_gps.y
                    ]
                },
                'properties': {
                    'id': caveau.id,
                    'code': caveau.code,
                    'zone': caveau.zone.code,
                    'type': caveau.type_caveau,
                    'statut': caveau.statut,
                    'statut_display': caveau.get_statut_display(),
                    'prix': str(caveau.prix_concession),
                    'reservable': caveau.est_reservable(),
                }
            }
            features.append(feature)
        
        return {
            'type': 'FeatureCollection',
            'features': features
        }
    
    @staticmethod
    def calculer_capacite_cimetiere() -> Dict[str, int]:
        """Calcule la capacité théorique et réelle du cimetière."""
        params = ParametreCimetiere.objects.first()
        
        if not params:
            return {
                'capacite_theorique': 0,
                'capacite_reelle': 0,
                'taux_remplissage': 0.0
            }
        
        capacite_theorique = params.calculer_capacite_theorique()
        capacite_reelle = Caveau.objects.count()
        
        taux_remplissage = 0.0
        if capacite_reelle > 0:
            occupes = Caveau.objects.filter(statut=Caveau.Statut.OCCUPE).count()
            taux_remplissage = round((occupes / capacite_reelle) * 100, 2)
        
        return {
            'capacite_theorique': capacite_theorique,
            'capacite_reelle': capacite_reelle,
            'taux_remplissage': taux_remplissage
        }
    
    @staticmethod
    def get_statistiques_globales() -> Dict[str, Any]:
        """Calcule les statistiques globales du cimetière."""
        total = Caveau.objects.count()
        disponibles = Caveau.objects.filter(statut=Caveau.Statut.DISPONIBLE).count()
        reserves = Caveau.objects.filter(statut=Caveau.Statut.RESERVE).count()
        occupes = Caveau.objects.filter(statut=Caveau.Statut.OCCUPE).count()
        non_exploitables = Caveau.objects.filter(statut=Caveau.Statut.NON_EXPLOITABLE).count()
        
        taux_occupation = 0.0
        if total > 0:
            taux_occupation = round((occupes / total) * 100, 2)
        
        return {
            'total_caveaux': total,
            'caveaux_disponibles': disponibles,
            'caveaux_reserves': reserves,
            'caveaux_occupes': occupes,
            'caveaux_non_exploitables': non_exploitables,
            'taux_occupation': taux_occupation,
        }


class AlertesService:
    """Service de gestion des alertes."""
    
    @staticmethod
    def get_concessions_a_renouveler(jours_avant_echeance: int = 90) -> List[Concession]:
        """Récupère les concessions à renouveler prochainement."""
        return ConcessionService.get_concessions_expiring_soon(jours_avant_echeance)
    
    @staticmethod
    def get_caveaux_bientout_saturation(seuil: int = 90) -> List[Zone]:
        """Récupère les zones接近 de la saturation."""
        zones_saturees = []
        
        for zone in Zone.objects.all():
            stats = CaveauService.get_statistiques_zone(zone)
            if stats['total'] > 0:
                taux = (stats['occupes'] / stats['total']) * 100
                if taux >= seuil:
                    zones_saturees.append({
                        'zone': zone,
                        'taux_occupation': round(taux, 2),
                        'stats': stats
                    })
        
        return zones_saturees
    
    @staticmethod
    def get_demandes_exhumation_en_attente() -> List[DemandeExhumation]:
        """Récupère les demandes d'exhumation en attente."""
        return list(
            DemandeExhumation.objects.filter(
                statut=DemandeExhumation.StatutDemande.EN_ATTENTE
            ).select_related('demandeur', 'inhumation', 'inhumation__defunt')
        )