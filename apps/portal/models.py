"""
Modèles pour le portail client (Réservations).
Conforme au CDC : validation → caveau RESERVE → concession → facture.
"""
from django.db import models
from django.conf import settings
from django.utils import timezone
from apps.core.models import Caveau


class DemandeReservation(models.Model):
    """Demande de réservation émise par un client pour un caveau."""

    class Statut(models.TextChoices):
        EN_ATTENTE = 'EN_ATTENTE', 'En attente de validation (Orange)'
        VALIDEE = 'VALIDEE', 'Validée par l\'admin (Rouge)'
        REFUSEE = 'REFUSEE', 'Refusée'
        ANNULEE = 'ANNULEE', 'Annulée'

    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reservations',
        verbose_name='Client'
    )
    caveau = models.ForeignKey(
        Caveau,
        on_delete=models.PROTECT,
        related_name='reservations',
        verbose_name='Caveau'
    )

    # --- Informations sur le défunt (saisies lors de la réservation) ---
    defunt_nom = models.CharField('Nom du défunt', max_length=100)
    defunt_prenom = models.CharField('Prénom du défunt', max_length=100)
    date_deces = models.DateField('Date de décès')
    lien_parente = models.CharField('Lien de parenté avec le demandeur', max_length=50)
    
    # --- Coordonnées du demandeur ---
    telephone_contact = models.CharField('Téléphone de contact', max_length=20)

    # --- Workflow ---
    statut = models.CharField(
        'Statut',
        max_length=20,
        choices=Statut.choices,
        default=Statut.EN_ATTENTE
    )
    date_demande = models.DateTimeField('Date de demande', auto_now_add=True)
    date_traitement = models.DateTimeField('Date de traitement', null=True, blank=True)
    traite_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reservations_traitees',
        verbose_name='Traité par'
    )
    motif_refus = models.TextField('Motif de refus', blank=True, null=True)

    # --- Métadonnées ---
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Demande de réservation'
        verbose_name_plural = 'Demandes de réservation'
        ordering = ['-date_demande']

    def __str__(self):
        return f"Réservation {self.caveau.code} - {self.client.get_full_name()} ({self.statut})"

    def valider(self, admin_user):
        """
        Valide la demande et met à jour le statut du caveau.
        Conforme au CDC : validation → caveau RESERVE.
        """
        # Mettre à jour le statut de la demande
        self.statut = self.Statut.VALIDEE
        self.date_traitement = timezone.now()
        self.traite_par = admin_user
        self.save()
        
        # Mettre à jour le statut du caveau
        self.caveau.statut = 'RESERVE'
        self.caveau.save(update_fields=['statut'])

    def refuser(self, admin_user, motif):
        """Refuse la demande avec un motif."""
        self.statut = self.Statut.REFUSEE
        self.date_traitement = timezone.now()
        self.traite_par = admin_user
        self.motif_refus = motif
        self.save()