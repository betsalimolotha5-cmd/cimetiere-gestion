"""
Modèles pour la gestion des notifications et emails.
"""
from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid


class EmailLog(models.Model):
    """Journal de tous les emails envoyés."""
    
    class StatutEmail(models.TextChoices):
        ENVOYE = 'ENVOYE', 'Envoyé'
        ECHEC = 'ECHEC', 'Échec'
        EN_ATTENTE = 'EN_ATTENTE', 'En attente'
    
    class TypeEmail(models.TextChoices):
        MFA_CODE = 'MFA_CODE', 'Code MFA'
        BIENVENUE = 'BIENVENUE', 'Email de bienvenue'
        CONFIRMATION_RESERVATION = 'CONFIRMATION_RESERVATION', 'Confirmation de réservation'
        FACTURE = 'FACTURE', 'Facture'
        RAPPEL_PAIEMENT = 'RAPPEL_PAIEMENT', 'Rappel de paiement'
        ALERTE_CONCESSION = 'ALERTE_CONCESSION', 'Alerte concession'
        AUTRE = 'AUTRE', 'Autre'
    
    # Identification
    reference = models.UUIDField(
        'Référence unique',
        default=uuid.uuid4,
        editable=False,
        unique=True
    )
    
    # Destinataire
    destinataire = models.EmailField('Destinataire')
    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='emails_recus',
        verbose_name='Utilisateur destinataire'
    )
    
    # Contenu
    type_email = models.CharField(
        'Type d\'email',
        max_length=30,
        choices=TypeEmail.choices,
        default=TypeEmail.AUTRE
    )
    sujet = models.CharField('Sujet', max_length=255)
    contenu_html = models.TextField('Contenu HTML')
    contenu_texte = models.TextField('Contenu texte', blank=True)
    
    # Pièces jointes
    pieces_jointes = models.JSONField(
        'Pièces jointes',
        default=list,
        blank=True,
        help_text='Liste des chemins de fichiers joints'
    )
    
    # Statut
    statut = models.CharField(
        'Statut',
        max_length=20,
        choices=StatutEmail.choices,
        default=StatutEmail.EN_ATTENTE,
        db_index=True
    )
    message_erreur = models.TextField('Message d\'erreur', blank=True)
    
    # Dates
    date_envoi_tente = models.DateTimeField('Date de tentative d\'envoi', default=timezone.now)
    date_envoi_reussi = models.DateTimeField('Date d\'envoi réussi', null=True, blank=True)
    
    # Métadonnées
    date_creation = models.DateTimeField('Date de création', auto_now_add=True)
    
    class Meta:
        verbose_name = 'Journal d\'email'
        verbose_name_plural = 'Journaux d\'emails'
        ordering = ['-date_envoi_tente']
        indexes = [
            models.Index(fields=['statut']),
            models.Index(fields=['type_email']),
            models.Index(fields=['destinataire']),
        ]
    
    def __str__(self):
        return f"{self.get_type_email_display()} - {self.destinataire} ({self.get_statut_display()})"
    
    def marquer_envoye(self):
        """Marque l'email comme envoyé avec succès."""
        self.statut = self.StatutEmail.ENVOYE
        self.date_envoi_reussi = timezone.now()
        self.save(update_fields=['statut', 'date_envoi_reussi'])
    
    def marquer_echec(self, message_erreur: str):
        """Marque l'email comme échec."""
        self.statut = self.StatutEmail.ECHEC
        self.message_erreur = message_erreur
        self.save(update_fields=['statut', 'message_erreur'])


class Notification(models.Model):
    """Notifications internes pour les utilisateurs."""
    
    class TypeNotification(models.TextChoices):
        INFO = 'INFO', 'Information'
        SUCCESS = 'SUCCESS', 'Succès'
        WARNING = 'WARNING', 'Avertissement'
        ERROR = 'ERROR', 'Erreur'
    
    class Priorite(models.TextChoices):
        BASSE = 'BASSE', 'Basse'
        NORMALE = 'NORMALE', 'Normale'
        HAUTE = 'HAUTE', 'Haute'
        URGENTE = 'URGENTE', 'Urgente'
    
    # Destinataire
    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name='Utilisateur destinataire'
    )
    
    # Contenu
    type_notification = models.CharField(
        'Type',
        max_length=20,
        choices=TypeNotification.choices,
        default=TypeNotification.INFO
    )
    priorite = models.CharField(
        'Priorité',
        max_length=20,
        choices=Priorite.choices,
        default=Priorite.NORMALE
    )
    titre = models.CharField('Titre', max_length=200)
    message = models.TextField('Message')
    
    # Lien optionnel
    url_lien = models.URLField('Lien associé', blank=True)
    
    # Statut de lecture
    lue = models.BooleanField('Lue', default=False, db_index=True)
    date_lecture = models.DateTimeField('Date de lecture', null=True, blank=True)
    
    # Métadonnées
    date_creation = models.DateTimeField('Date de création', auto_now_add=True)
    
    class Meta:
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
        ordering = ['-date_creation']
        indexes = [
            models.Index(fields=['utilisateur', 'lue']),
            models.Index(fields=['priorite']),
        ]
    
    def __str__(self):
        return f"{self.titre} - {self.utilisateur}"
    
    def marquer_comme_lue(self):
        """Marque la notification comme lue."""
        if not self.lue:
            self.lue = True
            self.date_lecture = timezone.now()
            self.save(update_fields=['lue', 'date_lecture'])
    
    @classmethod
    def compter_non_lues(cls, utilisateur):
        """Compte le nombre de notifications non lues pour un utilisateur."""
        return cls.objects.filter(utilisateur=utilisateur, lue=False).count()