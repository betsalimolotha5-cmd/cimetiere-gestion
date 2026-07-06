"""
Tâches d'arrière-plan pour les notifications et alertes.
Peuvent être exécutées via cron, Celery ou un gestionnaire de tâches.
"""
from django.utils import timezone
from typing import List, Dict, Any
from datetime import timedelta
import logging

from .services import NotificationService
from .models import EmailLog, Notification
from apps.accounts.models import User
from apps.core.models import Concession, Caveau
from apps.billing.models import Facture, Paiement

logger = logging.getLogger('audit')


class NotificationTasks:
    """Tâches planifiées pour les notifications."""
    
    @staticmethod
    def verifier_concessions_expiring():
        """
        Vérifie quotidiennement les concessions qui expirent bientôt.
        À exécuter une fois par jour.
        """
        logger.info("TASK_START: verifier_concessions_expiring")
        
        try:
            alertes_envoyees = NotificationService.envoyer_alertes_echeance_concession()
            
            logger.info(f"TASK_END: verifier_concessions_expiring, total_alertes={alertes_envoyees}")
            
            return {
                'success': True,
                'total_alertes': alertes_envoyees,
            }
        
        except Exception as e:
            logger.error(f"TASK_FAILED: verifier_concessions_expiring, error={str(e)}")
            return {
                'success': False,
                'error': str(e),
            }
    
    @staticmethod
    def verifier_factures_en_retard():
        """
        Vérifie quotidiennement les factures en retard et envoie des rappels.
        À exécuter une fois par jour.
        """
        logger.info("TASK_START: verifier_factures_en_retard")
        
        try:
            rappels_envoyes = NotificationService.envoyer_rappels_paiement()
            
            logger.info(f"TASK_END: verifier_factures_en_retard, total_rappels={rappels_envoyes}")
            
            return {
                'success': True,
                'total_rappels': rappels_envoyes,
            }
        
        except Exception as e:
            logger.error(f"TASK_FAILED: verifier_factures_en_retard, error={str(e)}")
            return {
                'success': False,
                'error': str(e),
            }
    
    @staticmethod
    def verifier_seuil_places_critiques():
        """
        Vérifie les zones qui approchent de la saturation.
        À exécuter une fois par jour.
        """
        logger.info("TASK_START: verifier_seuil_places_critiques")
        
        try:
            from apps.core.models import Zone
            from django.db.models import Count, Q
            
            seuil = 90
            zones_critiques = []
            
            # Récupérer toutes les zones avec leurs caveaux
            zones = Zone.objects.annotate(
                total_caveaux=Count('caveaux'),
                caveaux_non_exploitables=Count('caveaux', filter=Q(caveaux__statut='NON_EXPLOITABLE'))
            )
            
            for zone in zones:
                if zone.total_caveaux == 0:
                    continue
                
                # Calculer le taux d'occupation
                caveaux_disponibles = zone.caveaux.filter(statut='DISPONIBLE').count()
                caveaux_exploitables = zone.total_caveaux - zone.caveaux_non_exploitables
                
                if caveaux_exploitables == 0:
                    continue
                
                taux_occupation = ((caveaux_exploitables - caveaux_disponibles) / caveaux_exploitables) * 100
                
                if taux_occupation >= seuil:
                    zones_critiques.append({
                        'zone': zone,
                        'taux_occupation': round(taux_occupation, 2),
                        'caveaux_disponibles': caveaux_disponibles,
                        'total_exploitable': caveaux_exploitables,
                    })
            
            # Notifier les administrateurs
            admins = User.objects.filter(is_staff=True, is_active=True)
            
            if zones_critiques:
                for admin in admins:
                    for zone_info in zones_critiques:
                        NotificationService.creer_notification(
                            utilisateur=admin,
                            titre=f'Zone {zone_info["zone"].code} en saturation',
                            message=f'La zone {zone_info["zone"].nom} atteint {zone_info["taux_occupation"]}% de saturation.',
                            type_notification=Notification.TypeNotification.WARNING,
                            priorite=Notification.Priorite.HAUTE,
                            url_lien=f'/admin/core/zone/{zone_info["zone"].id}/change/',
                        )
            
            logger.info(f"TASK_END: verifier_seuil_places_critiques, zones_critiques={len(zones_critiques)}")
            
            return {
                'success': True,
                'zones_critiques': len(zones_critiques),
            }
        
        except Exception as e:
            logger.error(f"TASK_FAILED: verifier_seuil_places_critiques, error={str(e)}")
            return {
                'success': False,
                'error': str(e),
            }
    
    @staticmethod
    def nettoyer_anciens_logs_emails(jours: int = 90):
        """
        Nettoie les anciens logs d'emails pour libérer de l'espace.
        À exécuter une fois par semaine.
        """
        logger.info(f"TASK_START: nettoyer_anciens_logs_emails, jours={jours}")
        
        try:
            date_limite = timezone.now() - timedelta(days=jours)
            
            anciens_logs = EmailLog.objects.filter(
                date_envoi_tente__lt=date_limite,
                statut__in=[EmailLog.StatutEmail.ENVOYE, EmailLog.StatutEmail.ECHEC]
            )
            
            count = anciens_logs.count()
            anciens_logs.delete()
            
            logger.info(f"TASK_END: nettoyer_anciens_logs_emails, deleted={count}")
            
            return {
                'success': True,
                'deleted': count,
            }
        
        except Exception as e:
            logger.error(f"TASK_FAILED: nettoyer_anciens_logs_emails, error={str(e)}")
            return {
                'success': False,
                'error': str(e),
            }
    
    @staticmethod
    def nettoyer_anciennes_notifications(jours: int = 30):
        """
        Nettoie les anciennes notifications lues.
        À exécuter une fois par semaine.
        """
        logger.info(f"TASK_START: nettoyer_anciennes_notifications, jours={jours}")
        
        try:
            date_limite = timezone.now() - timedelta(days=jours)
            
            anciennes_notifs = Notification.objects.filter(
                date_creation__lt=date_limite,
                lue=True
            )
            
            count = anciennes_notifs.count()
            anciennes_notifs.delete()
            
            logger.info(f"TASK_END: nettoyer_anciennes_notifications, deleted={count}")
            
            return {
                'success': True,
                'deleted': count,
            }
        
        except Exception as e:
            logger.error(f"TASK_FAILED: nettoyer_anciennes_notifications, error={str(e)}")
            return {
                'success': False,
                'error': str(e),
            }
    
    @staticmethod
    def envoyer_rapport_quotidien_admin():
        """
        Envoie un rapport quotidien aux administrateurs.
        À exécuter une fois par jour le matin.
        """
        logger.info("TASK_START: envoyer_rapport_quotidien_admin")
        
        try:
            from django.db.models import Sum, Count
            
            admins = User.objects.filter(is_staff=True, is_active=True)
            
            # Statistiques du jour
            nouvelles_inscriptions = User.objects.filter(
                date_joined__date=timezone.now().date()
            ).count()
            
            nouvelles_reservations = Concession.objects.filter(
                date_creation__date=timezone.now().date()
            ).count()
            
            paiements_du_jour = Paiement.objects.filter(
                date_paiement__date=timezone.now().date(),
                statut=Paiement.StatutPaiement.VALIDE
            ).aggregate(total=Sum('montant'))['total'] or 0
            
            factures_en_retard = Facture.objects.filter(
                statut__in=[
                    Facture.StatutFacture.EMISE,
                    Facture.StatutFacture.PARTIELLEMENT_PAYEE
                ],
                date_echeance__lt=timezone.now().date()
            ).count()
            
            # Envoyer le rapport à chaque admin
            for admin in admins:
                NotificationService.creer_notification(
                    utilisateur=admin,
                    titre='Rapport quotidien',
                    message=f'Rapport du {timezone.now().strftime("%d/%m/%Y")}:\n'
                            f'- Nouvelles inscriptions: {nouvelles_inscriptions}\n'
                            f'- Nouvelles réservations: {nouvelles_reservations}\n'
                            f'- Paiements reçus: {paiements_du_jour:,.2f} FCFA\n'
                            f'- Factures en retard: {factures_en_retard}',
                    type_notification=Notification.TypeNotification.INFO,
                    priorite=Notification.Priorite.NORMALE,
                    url_lien='/admin/',
                )
            
            logger.info(f"TASK_END: envoyer_rapport_quotidien_admin, admins_notified={admins.count()}")
            
            return {
                'success': True,
                'admins_notified': admins.count(),
                'stats': {
                    'nouvelles_inscriptions': nouvelles_inscriptions,
                    'nouvelles_reservations': nouvelles_reservations,
                    'paiements_du_jour': str(paiements_du_jour),
                    'factures_en_retard': factures_en_retard,
                }
            }
        
        except Exception as e:
            logger.error(f"TASK_FAILED: envoyer_rapport_quotidien_admin, error={str(e)}")
            return {
                'success': False,
                'error': str(e),
            }
    
    @staticmethod
    def executer_toutes_taches_quotidiennes():
        """
        Exécute toutes les tâches quotidiennes.
        Utile pour un cron job unique.
        """
        logger.info("TASK_START: executer_toutes_taches_quotidiennes")
        
        results = {
            'concessions_expiring': NotificationTasks.verifier_concessions_expiring(),
            'factures_en_retard': NotificationTasks.verifier_factures_en_retard(),
            'seuil_places_critiques': NotificationTasks.verifier_seuil_places_critiques(),
            'rapport_admin': NotificationTasks.envoyer_rapport_quotidien_admin(),
        }
        
        logger.info("TASK_END: executer_toutes_taches_quotidiennes")
        
        return results