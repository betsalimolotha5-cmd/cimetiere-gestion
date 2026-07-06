"""
Service de notifications automatiques.
Gère les rappels de paiement et les alertes d'échéance.
"""
from django.core.mail import EmailMessage
from django.conf import settings
from django.utils import timezone
from django.db.models import Q
from datetime import timedelta
from decimal import Decimal
import logging

from apps.billing.models import Facture
from apps.core.models import Concession
from .models import EmailLog, Notification

logger = logging.getLogger('audit')


class NotificationService:
    """Service centralisé pour l'envoi de notifications automatiques."""
    
    @staticmethod
    def envoyer_email(destinataire, sujet, contenu_html, contenu_texte='', 
                     type_email=EmailLog.TypeEmail.AUTRE, utilisateur=None, pieces_jointes=None):
        """
        Envoie un email et le journalise dans EmailLog.
        
        Returns:
            bool: True si l'email a été envoyé avec succès
        """
        # Créer le log d'email
        email_log = EmailLog.objects.create(
            destinataire=destinataire,
            utilisateur=utilisateur,
            type_email=type_email,
            sujet=sujet,
            contenu_html=contenu_html,
            contenu_texte=contenu_texte,
            pieces_jointes=pieces_jointes or [],
            statut=EmailLog.StatutEmail.EN_ATTENTE
        )
        
        try:
            # Créer l'email
            email = EmailMessage(
                subject=sujet,
                body=contenu_texte or contenu_html,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[destinataire],
            )
            email.content_subtype = 'html'
            email.html = contenu_html
            
            # Ajouter les pièces jointes si nécessaire
            # (à implémenter selon les besoins)
            
            # Envoyer l'email
            email.send(fail_silently=False)
            
            # Marquer comme envoyé
            email_log.marquer_envoye()
            
            logger.info(f"EMAIL_SENT: type={type_email}, to={destinataire}, subject={sujet}")
            return True
            
        except Exception as e:
            # Marquer comme échec
            email_log.marquer_echec(str(e))
            logger.error(f"EMAIL_FAILED: type={type_email}, to={destinataire}, error={str(e)}")
            return False
    
    @staticmethod
    def creer_notification(utilisateur, titre, message, 
                          type_notification=Notification.TypeNotification.INFO,
                          priorite=Notification.Priorite.NORMALE, url_lien=''):
        """
        Crée une notification interne pour un utilisateur.
        """
        notification = Notification.objects.create(
            utilisateur=utilisateur,
            type_notification=type_notification,
            priorite=priorite,
            titre=titre,
            message=message,
            url_lien=url_lien
        )
        
        logger.info(f"NOTIFICATION_CREATED: user={utilisateur.email}, title={titre}")
        return notification
    
    @staticmethod
    def envoyer_rappels_paiement():
        """
        Envoie des rappels de paiement pour les factures en retard ou proches de l'échéance.
        
        Règles :
        - Factures en retard de 3 jours : rappel immédiat
        - Factures en retard de 7 jours : rappel urgent
        - Factures en retard de 15 jours : rappel final
        """
        aujourd = timezone.now().date()
        rappels_envoyes = 0
        
        # Factures en retard
        factures_en_retard = Facture.objects.filter(
            Q(statut=Facture.StatutFacture.EMISE) | Q(statut=Facture.StatutFacture.PARTIELLEMENT_PAYEE),
            date_echeance__lt=aujourd
        ).select_related('client', 'concession', 'concession__caveau')
        
        for facture in factures_en_retard:
            jours_retard = (aujourd - facture.date_echeance).days
            
            # Déterminer le type de rappel
            if jours_retard == 3:
                priorite = Notification.Priorite.NORMALE
                sujet = f"📋 Rappel : Facture {facture.numero_facture} en attente de paiement"
                message_html = NotificationService._generer_html_rappel(facture, jours_retard, 'normal')
            elif jours_retard == 7:
                priorite = Notification.Priorite.HAUTE
                sujet = f"⚠️ URGENT : Facture {facture.numero_facture} en retard de {jours_retard} jours"
                message_html = NotificationService._generer_html_rappel(facture, jours_retard, 'urgent')
            elif jours_retard == 15:
                priorite = Notification.Priorite.URGENTE
                sujet = f"🚨 DERNIER RAPPEL : Facture {facture.numero_facture} - Action requise"
                message_html = NotificationService._generer_html_rappel(facture, jours_retard, 'final')
            else:
                continue  # Pas de rappel pour ce jour
            
            # Envoyer l'email
            succes = NotificationService.envoyer_email(
                destinataire=facture.client.email,
                sujet=sujet,
                contenu_html=message_html,
                type_email=EmailLog.TypeEmail.RAPPEL_PAIEMENT,
                utilisateur=facture.client
            )
            
            if succes:
                # Créer une notification interne
                NotificationService.creer_notification(
                    utilisateur=facture.client,
                    titre=f"Rappel de paiement - {facture.numero_facture}",
                    message=f"Votre facture de {facture.montant_restant:,.2f} FCFA est en retard de {jours_retard} jour(s).",
                    type_notification=Notification.TypeNotification.WARNING,
                    priorite=priorite,
                    url_lien=f'/billing/facture/{facture.id}/'
                )
                rappels_envoyes += 1
        
        logger.info(f"PAYMENT_REMINDERS_SENT: count={rappels_envoyes}")
        return rappels_envoyes
    
    @staticmethod
    def envoyer_alertes_echeance_concession():
        """
        Envoie des alertes pour les concessions qui expirent bientôt.
        
        Règles :
        - 30 jours avant échéance : information
        - 15 jours avant échéance : avertissement
        - 7 jours avant échéance : alerte urgente
        """
        aujourd = timezone.now().date()
        alertes_envoyees = 0
        
        # Concessions temporaires qui expirent bientôt
        concessions_expirent_bientot = Concession.objects.filter(
            type_concession=Concession.TypeConcession.TEMPORAIRE,
            statut=Concession.StatutConcession.ACTIVE,
            date_fin__isnull=False,
            date_fin__gte=aujourd,
            date_fin__lte=aujourd + timedelta(days=30)
        ).select_related('concessionnaire', 'caveau', 'caveau__zone')
        
        for concession in concessions_expirent_bientot:
            jours_restants = (concession.date_fin - aujourd).days
            
            # Déterminer le type d'alerte
            if jours_restants == 30:
                priorite = Notification.Priorite.BASSE
                sujet = f"ℹ️ Information : Votre concession expire dans 30 jours"
                type_notification = Notification.TypeNotification.INFO
            elif jours_restants == 15:
                priorite = Notification.Priorite.NORMALE
                sujet = f"⚠️ Attention : Votre concession expire dans 15 jours"
                type_notification = Notification.TypeNotification.WARNING
            elif jours_restants == 7:
                priorite = Notification.Priorite.HAUTE
                sujet = f"🚨 URGENT : Votre concession expire dans 7 jours"
                type_notification = Notification.TypeNotification.WARNING
            else:
                continue  # Pas d'alerte pour ce jour
            
            # Générer le contenu HTML
            message_html = NotificationService._generer_html_alerte_concession(concession, jours_restants)
            
            # Envoyer l'email
            succes = NotificationService.envoyer_email(
                destinataire=concession.concessionnaire.email,
                sujet=sujet,
                contenu_html=message_html,
                type_email=EmailLog.TypeEmail.ALERTA_CONCESSION,
                utilisateur=concession.concessionnaire
            )
            
            if succes:
                # Créer une notification interne
                NotificationService.creer_notification(
                    utilisateur=concession.concessionnaire,
                    titre=f"Expiration de concession - {concession.caveau.code}",
                    message=f"Votre concession pour le caveau {concession.caveau.code} expire dans {jours_restants} jour(s).",
                    type_notification=type_notification,
                    priorite=priorite,
                    url_lien='/mes-concessions/'
                )
                alertes_envoyees += 1
        
        logger.info(f"CONCESSION_ALERTS_SENT: count={alertes_envoyees}")
        return alertes_envoyees
    
    @staticmethod
    def _generer_html_rappel(facture, jours_retard, niveau):
        """Génère le HTML pour un email de rappel de paiement."""
        couleurs = {
            'normal': '#f39c12',
            'urgent': '#e67e22',
            'final': '#e74c3c'
        }
        couleur = couleurs.get(niveau, '#f39c12')
        
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; background-color: #f5f5f5; padding: 20px;">
            <div style="max-width: 600px; margin: auto; background: white; padding: 30px; border-radius: 10px;">
                <h2 style="color: {couleur};">📋 Rappel de paiement</h2>
                <p>Bonjour <strong>{facture.client.get_full_name() or facture.client.email}</strong>,</p>
                
                <div style="background: #fff3cd; border-left: 4px solid {couleur}; padding: 15px; margin: 20px 0;">
                    <p style="margin: 5px 0;"><strong>Facture :</strong> {facture.numero_facture}</p>
                    <p style="margin: 5px 0;"><strong>Montant restant :</strong> {facture.montant_restant:,.2f} FCFA</p>
                    <p style="margin: 5px 0;"><strong>Retard :</strong> {jours_retard} jour(s)</p>
                    <p style="margin: 5px 0;"><strong>Date d'échéance :</strong> {facture.date_echeance.strftime('%d/%m/%Y')}</p>
                </div>
                
                <p>Nous vous rappelons que votre facture est en retard de <strong>{jours_retard} jour(s)</strong>.</p>
                <p>Merci de procéder au paiement dès que possible pour éviter toute interruption de service.</p>
                
                <p style="margin-top: 30px;">
                    <a href="http://127.0.0.1:8000/billing/facture/{facture.id}/" 
                       style="background: {couleur}; color: white; padding: 12px 24px; text-decoration: none; 
                              border-radius: 5px; display: inline-block;">
                        💳 Payer maintenant
                    </a>
                </p>
                
                <p style="margin-top: 30px; color: #7f8c8d; font-size: 12px;">
                    Pour toute question, n'hésitez pas à nous contacter.
                </p>
            </div>
        </body>
        </html>
        """
        return html
    
    @staticmethod
    def _generer_html_alerte_concession(concession, jours_restants):
        """Génère le HTML pour un email d'alerte d'expiration de concession."""
        if jours_restants <= 7:
            couleur = '#e74c3c'
        elif jours_restants <= 15:
            couleur = '#e67e22'
        else:
            couleur = '#3498db'
        
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; background-color: #f5f5f5; padding: 20px;">
            <div style="max-width: 600px; margin: auto; background: white; padding: 30px; border-radius: 10px;">
                <h2 style="color: {couleur};">🔔 Alerte d'expiration de concession</h2>
                <p>Bonjour <strong>{concession.concessionnaire.get_full_name() or concession.concessionnaire.email}</strong>,</p>
                
                <div style="background: #eaf4fc; border-left: 4px solid {couleur}; padding: 15px; margin: 20px 0;">
                    <p style="margin: 5px 0;"><strong>Caveau :</strong> {concession.caveau.code}</p>
                    <p style="margin: 5px 0;"><strong>Zone :</strong> {concession.caveau.zone.nom if concession.caveau.zone else 'Non définie'}</p>
                    <p style="margin: 5px 0;"><strong>Date d'expiration :</strong> {concession.date_fin.strftime('%d/%m/%Y')}</p>
                    <p style="margin: 5px 0;"><strong>Jours restants :</strong> {jours_restants} jour(s)</p>
                </div>
                
                <p>Votre concession funéraire expire dans <strong>{jours_restants} jour(s)</strong>.</p>
                <p>Nous vous invitons à contacter l'administration pour discuter des options de renouvellement.</p>
                
                <p style="margin-top: 30px; color: #7f8c8d; font-size: 12px;">
                    Pour toute question, n'hésitez pas à nous contacter.
                </p>
            </div>
        </body>
        </html>
        """
        return html