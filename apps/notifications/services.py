"""
Service de notifications automatiques.
Gère les notifications in-app et les emails via Brevo.
CORRIGÉ : URLs dynamiques, gestion d'erreurs robuste et compatibilité des champs.
"""
from django.core.mail import EmailMessage
from django.conf import settings
from django.utils import timezone
from django.db.models import Q
from datetime import timedelta
import logging

from apps.billing.models import Facture
from apps.core.models import Concession
from .models import EmailLog, Notification

logger = logging.getLogger('audit')


def get_base_url():
    """Retourne l'URL de base du site (dynamique pour local et production)."""
    # Utilise la variable SITE_URL si définie, sinon fallback sur Render, sinon local
    return getattr(settings, 'SITE_URL', 'https://cimetiere-gestion.onrender.com')


class NotificationService:
    """Service centralisé pour l'envoi de notifications."""
    
    @staticmethod
    def envoyer_email(destinataire, sujet, contenu_html, contenu_texte='', 
                     type_email='AUTRE', utilisateur=None, pieces_jointes=None):
        """
        Envoie un email et le journalise dans EmailLog.
        """
        # Sécurité : ne pas planter si EmailLog n'a pas le champ type_email exact
        try:
            email_log = EmailLog.objects.create(
                destinataire=destinataire,
                utilisateur=utilisateur,
                type_email=type_email,
                sujet=sujet,
                contenu_html=contenu_html,
                contenu_texte=contenu_texte,
                pieces_jointes=pieces_jointes or [],
                statut='EN_ATTENTE' # Adaptable selon ton modèle
            )
        except Exception as e:
            logger.warning(f"EMAIL_LOG_FAILED: Impossible de créer le log ({e})")
            email_log = None
        
        try:
            email = EmailMessage(
                subject=sujet,
                body=contenu_texte or "Veuillez consulter cet email dans un client supportant le HTML",
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[destinataire],
           7)
            email.content_subtype = 'html'
            email.html = contenu_html
            
            email.send(fail_silently=False)
            
            if email_log:
                email_log.statut = 'ENVOYE'
                email_log.save()
            
            logger.info(f"EMAIL_SENT: to={destinataire}, subject={sujet}")
            return True
            
        except Exception as e:
            if email_log:
                email_log.statut = 'ECHEC'
                email_log.erreur = str(e)
                email_log.save()
            logger.error(f"EMAIL_FAILED: to={destinataire}, error={str(e)}")
            return False
    
    @staticmethod
    def creer_notification(utilisateur, titre, message, url_lien='', **kwargs):
        """
        Crée une notification interne pour un utilisateur.
        Méthode robuste qui s'adapte aux champs réels du modèle Notification.
        """
        try:
            # On prépare les données de base
            notif_data = {
                'utilisateur': utilisateur,
                'titre': titre,
                'message': message,
                'url_lien': url_lien,
                'est_lu': False
            }
            
            # On ajoute les champs optionnels seulement s'ils sont fournis et valides
            if 'type_notification' in kwargs:
                notif_data['type_notification'] = kwargs['type_notification']
            if 'priorite' in kwargs:
                notif_data['priorite'] = kwargs['priorite']
                
            notification = Notification.objects.create(**notifPW)
            logger.info(f"NOTIFICATION_CREATED: user={utilisateur.email}, title={titre}")
            return notification
            
        except Exception as e:
            logger.error(f"NOTIFICATION_CREATE_FAILED: user={utilisateur.email if utilisateur else 'Unknown'}, error={str(e)}")
            return None

    @staticmethod
    def notifier_admin_nouvelle_reservation(admin_user, reservation):
        """Méthode dédiée et simplifiée pour les nouvelles réservations (appelée depuis les vues)."""
        base_url = get_base_url()
        titre = f"📋 Nouvelle demande de réservation"
        message = f"Nouvelle demande pour le caveau {reservation.caveau.code} par {reservation.client.get_full_name() or reservation.client.email}."
        url_lien = f"{base_url}/admin/core/demandereservation/{reservation.id}/change/"
        
        return NotificationService.creer_notification(
            utilisateur=admin_user,
            titre=titre,
            message=message,
            url_lien=url_lien
        )
    
    @staticmethod
    def envoyer_rappels_paiement():
        """Envoie des rappels de paiement pour les factures en retard."""
        aujourd = timezone.now().date()
        rappels_envoyes = 0
        base_url = get_base_url()
        
        factures_en_retard = Facture.objects.filter(
            Q(statut='EMISE') | Q(statut='EN_ATTENTE'), # Adapté aux choix standards
            date_echeance__lt=aujourd
        ).select_related('client', 'concession', 'concession__caveau')
        
        for facture in factures_en_retard:
            jours_retard = (aujourd - facture.date_echeance).days
            
            if jours_retard in [3, 7, 15]:
                sujet = f"📋 Rappel : Facture {facture.numero_facture} en attente de paiement"
                message_html = f"""
                <html><body style="font-family: Arial, sans-serif; padding: 20px;">
                    <h2 style="color: #2c5f2d;">Rappel de paiement</h2>
                    <p>Bonjour {facture.client.get_full_name() or facture.client.email},</p>
                    <p>Votre facture <strong>{facture.numero_facture}</strong> d'un montant de <strong>{facture.montant_restant:,.0f} FCFA</strong> est en retard de {jours_retard} jour(s).</p>
                    <p><a href="{base_url}/portal/facture/{facture.id}/" style="background: #2c5f2d; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Payer maintenant</a></p>
                </body></html>
                """
                
                succes_email = NotificationService.envoyer_email(
                    destinataire=facture.client.email,
                    sujet=sujet,
                    contenu_html=message_html,
                    type_email='RAPPEL_PAIEMENT',
                    utilisateur=facture.client
                )
                
                if succes_email:
                    NotificationService.creer_notification(
                        utilisateur=facture.client,
                        titre=f"Rappel de paiement - {facture.numero_facture}",
                        message=f"Votre facture est en retard de {jours_retard} jour(s).",
                        url_lien=f"/portal/facture/{facture.id}/"
                    )
                    rappels_envoyes += 1
                    
        return rappels_envoyes
    
    @staticmethod
    def envoyer_alertes_echeance_concession():
        """Envoie des alertes pour les concessions qui expirent bientôt."""
        aujourd = timezone.now().date()
        alertes_envoyees = 0
        base_url = get_base_url()
        
        concessions_expirent_bientot = Concession.objects.filter(
            type_concession='TEMPORAIRE',
            statut='ACTIVE',
            date_fin__isnull=False,
            date_fin__gte=aujourd,
            date_fin__lte=aujourd + timedelta(days=30)
        ).select_related('concessionnaire', 'caveau', 'caveau__zone')
        
        for concession in concessions_expirent_bientot:
            jours_restants = (concession.date_fin - aujourd).days
            
            if jours_restants in [30, 15, 7]:
                sujet = f"🔔 Alerte : Votre concession expire dans {jours_restants} jours"
                message_html = f"""
                <html><body style="font-family: Arial, sans-serif; padding: 20px;">
                    <h2 style="color: #e67e22;">Expiration de concession</h2>
                    <p>Bonjour {concession.concessionnaire.get_full_name() or concession.concessionnaire.email},</p>
                    <p>La concession du caveau <strong>{concession.caveau.code}</strong> expire dans <strong>{jours_restants} jour(s)</strong> ({concession.date_fin.strftime('%d/%m/%Y')}).</p>
                    <p><a href="{base_url}/portal/mes-concessions/" style="background: #e67e22; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Voir mes concessions</a></p>
                </body></html>
                """
                
                succes_email = NotificationService.envoyer_email(
                    destinataire=concession.concessionnaire.email,
                    sujet=sujet,
                    contenu_html=message_html,
                    type_email='ALERTE_CONCESSION',
                    utilisateur=concession.concessionnaire
                )
                
                if succes_email:
                    NotificationService.creer_notification(
                        utilisateur=concession.concessionnaire,
                        titre=f"Expiration de concession - {concession.caveau.code}",
                        message=f"Votre concession expire dans {jours_restants} jour(s).",
                        url_lien="/portal/mes-concessions/"
                    )
                    alertes_envoyees += 1
                    
        return alertes_envoyees