"""
Modèles pour la facturation et les paiements.
Conforme au CDC : workflow complet réservation → facture → paiement.
"""
from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
import logging

logger = logging.getLogger('audit')


class Facture(models.Model):
    """Facture émise pour une concession."""
    
    class StatutFacture(models.TextChoices):
        BROUILLON = 'BROUILLON', 'Brouillon'
        EMISE = 'EMISE', 'Émise'
        PARTIELLEMENT_PAYEE = 'PARTIELLEMENT_PAYEE', 'Partiellement payée'
        PAYEE = 'PAYEE', 'Payée'
        ANNULEE = 'ANNULEE', 'Annulée'
    
    numero_facture = models.CharField('N° de facture', max_length=50, unique=True, db_index=True)
    concession = models.ForeignKey(
        'core.Concession',
        on_delete=models.CASCADE,
        related_name='factures',
        verbose_name='Concession'
    )
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='factures',
        verbose_name='Client'
    )
    
    # Montants
    montant_ht = models.DecimalField('Montant HT', max_digits=12, decimal_places=2, default=Decimal('0.00'))
    taux_tva = models.DecimalField('Taux TVA (%)', max_digits=5, decimal_places=2, default=Decimal('0.00'))
    montant_tva = models.DecimalField('Montant TVA', max_digits=12, decimal_places=2, default=Decimal('0.00'))
    montant_total = models.DecimalField('Montant total TTC', max_digits=12, decimal_places=2, default=Decimal('0.00'))
    montant_paye = models.DecimalField('Montant payé', max_digits=12, decimal_places=2, default=Decimal('0.00'))
    montant_restant = models.DecimalField('Montant restant', max_digits=12, decimal_places=2, default=Decimal('0.00'))
    
    # Statut
    statut = models.CharField(
        'Statut',
        max_length=30,
        choices=StatutFacture.choices,
        default=StatutFacture.BROUILLON,
        db_index=True
    )
    
    # Dates
    date_emission = models.DateField('Date d\'émission')
    date_echeance = models.DateField('Date d\'échéance')
    date_paiement_complet = models.DateField('Date de paiement complet', null=True, blank=True)
    
    # Document PDF
    fichier_pdf = models.FileField('Fichier PDF', upload_to='factures/pdf/%Y/%m/', blank=True, null=True)
    email_envoye = models.BooleanField('Email envoyé', default=False)
    date_envoi_email = models.DateTimeField('Date envoi email', null=True, blank=True)
    
    # Description
    description = models.TextField('Description', blank=True)
    notes = models.TextField('Notes', blank=True)
    
    # Métadonnées
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    cree_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='factures_creees',
        verbose_name='Créé par'
    )
    
    class Meta:
        verbose_name = 'Facture'
        verbose_name_plural = 'Factures'
        ordering = ['-date_emission', '-id']
    
    def __str__(self):
        return f"{self.numero_facture} - {self.client.email} ({self.get_statut_display()})"
    
    def save(self, *args, **kwargs):
        """Calcul automatique des montants."""
        self.montant_tva = self.montant_ht * (self.taux_tva / Decimal('100'))
        self.montant_total = self.montant_ht + self.montant_tva
        self.montant_restant = self.montant_total - self.montant_paye
        
        if self.montant_restant < Decimal('0.01'):
            self.montant_restant = Decimal('0.00')
        
        super().save(*args, **kwargs)
    
    def est_payee(self):
        """Vérifie si la facture est entièrement payée."""
        return self.montant_restant <= Decimal('0.01')
    
    def mettre_a_jour_statut(self):
        """Met à jour le statut de la facture selon les paiements."""
        if self.est_payee():
            self.statut = self.StatutFacture.PAYEE
            if not self.date_paiement_complet:
                self.date_paiement_complet = timezone.now().date()
        elif self.montant_paye > Decimal('0'):
            self.statut = self.StatutFacture.PARTIELLEMENT_PAYEE
        else:
            self.statut = self.StatutFacture.EMISE
        
        self.save(update_fields=['statut', 'date_paiement_complet', 'montant_paye', 'montant_restant'])


class Paiement(models.Model):
    """Paiement effectué pour une facture."""
    
    class StatutPaiement(models.TextChoices):
        EN_ATTENTE = 'EN_ATTENTE', 'En attente de validation'
        VALIDE = 'VALIDE', 'Validé'
        REFUSE = 'REFUSE', 'Refusé'
        REMBOURSE = 'REMBOURSE', 'Remboursé'
    
    class ModePaiement(models.TextChoices):
        MOBILE_MONEY = 'MOBILE_MONEY', 'Mobile Money'
        AIRTEL_MONEY = 'AIRTEL_MONEY', 'Airtel Money'
        ESPECES = 'ESPECES', 'Espèces'
        VIREMENT = 'VIREMENT', 'Virement bancaire'
        CHEQUE = 'CHEQUE', 'Chèque'
        CARTE = 'CARTE', 'Carte bancaire'
    
    numero_transaction = models.CharField(
        'N° de transaction',
        max_length=50,
        unique=True,
        db_index=True,
        default=''
    )
    facture = models.ForeignKey(
        Facture,
        on_delete=models.CASCADE,
        related_name='paiements',
        verbose_name='Facture'
    )
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='paiements',
        verbose_name='Client'
    )
    
    montant = models.DecimalField('Montant', max_digits=12, decimal_places=2)
    mode_paiement = models.CharField(
        'Mode de paiement',
        max_length=20,
        choices=ModePaiement.choices
    )
    
    # Détails de la transaction
    reference_transaction = models.CharField('Référence transaction', max_length=100, blank=True)
    numero_telephone = models.CharField('N° de téléphone', max_length=20, blank=True)
    
    # Statut
    statut = models.CharField(
        'Statut',
        max_length=20,
        choices=StatutPaiement.choices,
        default=StatutPaiement.EN_ATTENTE,
        db_index=True
    )
    
    # Dates
    date_paiement = models.DateTimeField('Date de paiement', auto_now_add=True)
    date_validation = models.DateTimeField('Date de validation', null=True, blank=True)
    
    # Validation
    valide_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='paiements_valides',
        verbose_name='Validé par'
    )
    
    # Notes
    notes = models.TextField('Notes', blank=True)
    
    # Métadonnées
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Paiement'
        verbose_name_plural = 'Paiements'
        ordering = ['-date_paiement']
    
    def __str__(self):
        return f"{self.numero_transaction} - {self.montant} FCFA ({self.get_statut_display()})"
    
    def save(self, *args, **kwargs):
        """Génère automatiquement le numéro de transaction."""
        if not self.numero_transaction:
            timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
            self.numero_transaction = f"PAY-{timestamp}-{self.facture_id or 'NEW'}"
        super().save(*args, **kwargs)
    
    def valider(self, admin_user):
        """
        Valide le paiement et met à jour la facture.
        Conforme au CDC : validation → facture payée → caveau OCCUPE.
        """
        self.statut = self.StatutPaiement.VALIDE
        self.date_validation = timezone.now()
        self.valide_par = admin_user
        self.save()
        
        # Mettre à jour la facture
        facture = self.facture
        facture.montant_paye += self.montant
        facture.mettre_a_jour_statut()
        
        # Si la facture est entièrement payée, mettre le caveau en OCCUPE
        if facture.est_payee() and facture.concession:
            caveau = facture.concession.caveau
            if caveau.statut != 'OCCUPE':
                caveau.statut = 'OCCUPE'
                caveau.save(update_fields=['statut'])
        
        logger.info(
            f"PAYMENT_VALIDATED: transaction={self.numero_transaction}, "
            f"montant={self.montant}, by={admin_user.email}"
        )
    
    def refuser(self, motif, admin_user):
        """Refuse le paiement."""
        self.statut = self.StatutPaiement.REFUSE
        self.notes = f"Refusé: {motif}"
        self.valide_par = admin_user
        self.save()
        
        logger.info(
            f"PAYMENT_REFUSED: transaction={self.numero_transaction}, "
            f"montant={self.montant}, by={admin_user.email}"
        )


class TransactionFinanciere(models.Model):
    """Journal de toutes les transactions financières (audit trail)."""
    
    class TypeTransaction(models.TextChoices):
        PAIEMENT = 'PAIEMENT', 'Paiement'
        REMBOURSEMENT = 'REMBOURSEMENT', 'Remboursement'
        AJUSTEMENT = 'AJUSTEMENT', 'Ajustement'
        ANNULATION = 'ANNULATION', 'Annulation'
    
    class Sens(models.TextChoices):
        ENTREE = 'ENTREE', 'Entrée (argent reçu)'
        SORTIE = 'SORTIE', 'Sortie (argent dépensé)'
    
    type_transaction = models.CharField(
        'Type de transaction',
        max_length=20,
        choices=TypeTransaction.choices
    )
    montant = models.DecimalField('Montant', max_digits=12, decimal_places=2)
    sens = models.CharField(
        'Sens',
        max_length=10,
        choices=Sens.choices
    )
    
    # Liens optionnels
    facture = models.ForeignKey(
        Facture,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions',
        verbose_name='Facture liée'
    )
    paiement = models.ForeignKey(
        Paiement,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions',
        verbose_name='Paiement lié'
    )
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions',
        verbose_name='Client'
    )
    
    description = models.TextField('Description')
    reference = models.CharField('Référence', max_length=100, blank=True)
    date_transaction = models.DateTimeField('Date de transaction', auto_now_add=True)
    
    enregistre_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions_enregistrees',
        verbose_name='Enregistré par'
    )
    
    date_creation = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Transaction financière'
        verbose_name_plural = 'Transactions financières'
        ordering = ['-date_transaction']
    
    def __str__(self):
        return f"{self.get_type_transaction_display()} - {self.montant} FCFA ({self.get_sens_display()})"