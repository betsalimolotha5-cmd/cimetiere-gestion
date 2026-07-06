"""
Service de génération de rapports et statistiques.
"""
from django.db.models import Sum, Count, Q, Avg, F
from django.db.models.functions import TruncMonth, TruncYear
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import logging

from apps.billing.models import Facture, Paiement, TransactionFinanciere
from apps.core.models import Concession, Caveau, Zone, Defunt
from apps.notifications.models import EmailLog, Notification

logger = logging.getLogger('audit')


class RapportService:
    """Service centralisé pour la génération de rapports."""
    
    @staticmethod
    def rapport_financier(date_debut=None, date_fin=None):
        """
        Génère un rapport financier complet.
        
        Returns:
            dict: Statistiques financières
        """
        if not date_fin:
            date_fin = timezone.now().date()
        if not date_debut:
            date_debut = date_fin - timedelta(days=30)
        
        # Factures de la période
        factures_periode = Facture.objects.filter(
            date_emission__gte=date_debut,
            date_emission__lte=date_fin
        )
        
        total_facture = factures_periode.aggregate(
            total_ht=Sum('montant_ht'),
            total_ttc=Sum('montant_total'),
            total_paye=Sum('montant_paye'),
            total_restant=Sum('montant_restant')
        )
        
        # Paiements de la période
        paiements_periode = Paiement.objects.filter(
            date_paiement__date__gte=date_debut,
            date_paiement__date__lte=date_fin,
            statut=Paiement.StatutPaiement.VALIDE
        )
        
        total_paiements = paiements_periode.aggregate(
            total=Sum('montant')
        )
        
        # Paiements par mode
        paiements_par_mode = paiements_periode.values('mode_paiement').annotate(
            total=Sum('montant'),
            count=Count('id')
        ).order_by('-total')
        
        # Factures en retard
        factures_en_retard = Facture.objects.filter(
            Q(statut=Facture.StatutFacture.EMISE) | Q(statut=Facture.StatutFacture.PARTIELLEMENT_PAYEE),
            date_echeance__lt=date_fin
        ).count()
        
        # Évolution mensuelle (6 derniers mois)
        evolution_mensuelle = Facture.objects.filter(
            date_emission__gte=date_fin - timedelta(days=180)
        ).annotate(
            mois=TruncMonth('date_emission')
        ).values('mois').annotate(
            total=Sum('montant_total'),
            count=Count('id')
        ).order_by('mois')
        
        return {
            'date_debut': date_debut,
            'date_fin': date_fin,
            'total_factures': factures_periode.count(),
            'total_ht': total_facture['total_ht'] or Decimal('0'),
            'total_ttc': total_facture['total_ttc'] or Decimal('0'),
            'total_paye': total_facture['total_paye'] or Decimal('0'),
            'total_restant': total_facture['total_restant'] or Decimal('0'),
            'total_paiements': total_paiements['total'] or Decimal('0'),
            'nb_paiements': paiements_periode.count(),
            'paiements_par_mode': list(paiements_par_mode),
            'factures_en_retard': factures_en_retard,
            'evolution_mensuelle': list(evolution_mensuelle),
        }
    
    @staticmethod
    def rapport_occupation():
        """
        Génère un rapport d'occupation des caveaux.
        
        Returns:
            dict: Statistiques d'occupation
        """
        total_caveaux = Caveau.objects.count()
        caveaux_disponibles = Caveau.objects.filter(statut='DISPONIBLE').count()
        caveaux_reserves = Caveau.objects.filter(statut='RESERVE').count()
        caveaux_occupes = Caveau.objects.filter(statut='OCCUPE').count()
        caveaux_non_exploitables = Caveau.objects.filter(statut='NON_EXPLOITABLE').count()
        
        # Occupation par zone
        occupation_par_zone = Zone.objects.annotate(
            total_caveaux=Count('caveaux'),
            disponibles=Count('caveaux', filter=Q(caveaux__statut='DISPONIBLE')),
            reserves=Count('caveaux', filter=Q(caveaux__statut='RESERVE')),
            occupes=Count('caveaux', filter=Q(caveaux__statut='OCCUPE')),
            non_exploitables=Count('caveaux', filter=Q(caveaux__statut='NON_EXPLOITABLE'))
        ).values(
            'id', 'nom', 'total_caveaux', 'disponibles', 'reserves', 'occupes', 'non_exploitables'
        )
        
        # Calculer le taux d'occupation
        taux_occupation = 0
        if total_caveaux > 0:
            taux_occupation = ((caveaux_reserves + caveaux_occupes) / total_caveaux) * 100
        
        return {
            'total_caveaux': total_caveaux,
            'caveaux_disponibles': caveaux_disponibles,
            'caveaux_reserves': caveaux_reserves,
            'caveaux_occupes': caveaux_occupes,
            'caveaux_non_exploitables': caveaux_non_exploitables,
            'taux_occupation': round(taux_occupation, 2),
            'occupation_par_zone': list(occupation_par_zone),
        }
    
    @staticmethod
    def rapport_concessions():
        """
        Génère un rapport sur les concessions.
        
        Returns:
            dict: Statistiques des concessions
        """
        aujourd = timezone.now().date()
        
        total_concessions = Concession.objects.count()
        concessions_actives = Concession.objects.filter(statut=Concession.StatutConcession.ACTIVE).count()
        concessions_expirees = Concession.objects.filter(statut=Concession.StatutConcession.EXPIREE).count()
        concessions_resiliees = Concession.objects.filter(statut=Concession.StatutConcession.RESILIEE).count()
        concessions_renouvelees = Concession.objects.filter(statut=Concession.StatutConcession.RENOUVELEE).count()
        
        # Concessions temporaires vs perpétuelles
        concessions_temporaires = Concession.objects.filter(
            type_concession=Concession.TypeConcession.TEMPORAIRE
        ).count()
        concessions_perpetuelles = Concession.objects.filter(
            type_concession=Concession.TypeConcession.PERPETUELLE
        ).count()
        
        # Concessions qui expirent bientôt (30 jours)
        concessions_expirent_bientot = Concession.objects.filter(
            type_concession=Concession.TypeConcession.TEMPORAIRE,
            statut=Concession.StatutConcession.ACTIVE,
            date_fin__isnull=False,
            date_fin__gte=aujourd,
            date_fin__lte=aujourd + timedelta(days=30)
        ).count()
        
        # Répartition par type
        repartition_par_type = Concession.objects.values('type_concession').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Évolution mensuelle des nouvelles concessions (12 derniers mois)
        evolution_mensuelle = Concession.objects.filter(
            date_debut__gte=aujourd - timedelta(days=365)
        ).annotate(
            mois=TruncMonth('date_debut')
        ).values('mois').annotate(
            count=Count('id')
        ).order_by('mois')
        
        return {
            'total_concessions': total_concessions,
            'concessions_actives': concessions_actives,
            'concessions_expirees': concessions_expirees,
            'concessions_resiliees': concessions_resiliees,
            'concessions_renouvelees': concessions_renouvelees,
            'concessions_temporaires': concessions_temporaires,
            'concessions_perpetuelles': concessions_perpetuelles,
            'concessions_expirent_bientot': concessions_expirent_bientot,
            'repartition_par_type': list(repartition_par_type),
            'evolution_mensuelle': list(evolution_mensuelle),
        }
    
    @staticmethod
    def rapport_notifications():
        """
        Génère un rapport sur les notifications envoyées.
        
        Returns:
            dict: Statistiques des notifications
        """
        aujourd = timezone.now().date()
        
        total_emails = EmailLog.objects.count()
        emails_envoyes = EmailLog.objects.filter(statut=EmailLog.StatutEmail.ENVOYE).count()
        emails_echec = EmailLog.objects.filter(statut=EmailLog.StatutEmail.ECHEC).count()
        emails_attente = EmailLog.objects.filter(statut=EmailLog.StatutEmail.EN_ATTENTE).count()
        
        # Taux de succès
        taux_succes = 0
        if total_emails > 0:
            taux_succes = (emails_envoyes / total_emails) * 100
        
        # Emails par type
        emails_par_type = EmailLog.objects.values('type_email').annotate(
            count=Count('id'),
            envoyes=Count('id', filter=Q(statut='ENVOYE')),
            echecs=Count('id', filter=Q(statut='ECHEC'))
        ).order_by('-count')
        
        # Notifications internes
        total_notifications = Notification.objects.count()
        notifications_non_lues = Notification.objects.filter(lue=False).count()
        notifications_urgentes = Notification.objects.filter(
            priorite=Notification.Priorite.URGENTE,
            lue=False
        ).count()
        
        # Évolution mensuelle des emails (6 derniers mois)
        evolution_mensuelle = EmailLog.objects.filter(
            date_envoi_tente__date__gte=aujourd - timedelta(days=180)
        ).annotate(
            mois=TruncMonth('date_envoi_tente')
        ).values('mois').annotate(
            total=Count('id'),
            envoyes=Count('id', filter=Q(statut='ENVOYE')),
            echecs=Count('id', filter=Q(statut='ECHEC'))
        ).order_by('mois')
        
        return {
            'total_emails': total_emails,
            'emails_envoyes': emails_envoyes,
            'emails_echec': emails_echec,
            'emails_attente': emails_attente,
            'taux_succes': round(taux_succes, 2),
            'emails_par_type': list(emails_par_type),
            'total_notifications': total_notifications,
            'notifications_non_lues': notifications_non_lues,
            'notifications_urgentes': notifications_urgentes,
            'evolution_mensuelle': list(evolution_mensuelle),
        }