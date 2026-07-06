"""
Modèles de l'application core.
"""
from django.db import models
from django.contrib.gis.db import models as gis_models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal


class Zone(models.Model):
    """Zone du cimetière (section, bloc, etc.)."""
    
    class TypeZone(models.TextChoices):
        SECTION = 'SECTION', 'Section'
        BLOC = 'BLOC', 'Bloc'
        ALLÉE = 'ALLEE', 'Allée'
        AUTRE = 'AUTRE', 'Autre'
    
    code = models.CharField(max_length=20, unique=True)
    nom = models.CharField(max_length=100)
    type_zone = models.CharField(max_length=20, choices=TypeZone.choices, default=TypeZone.SECTION)
    description = models.TextField(blank=True)
    est_exploitable = models.BooleanField(default=True)
    superficie = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    coordonnees_gps = gis_models.PointField(null=True, blank=True)  # PostGIS
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['code']
        verbose_name = 'Zone'
        verbose_name_plural = 'Zones'
    
    def __str__(self):
        return f"{self.nom} ({self.code})"
    
    def calculer_capacite_theorique(self):
        """Calcule la capacité théorique en nombre de caveaux."""
        if not self.superficie or self.superficie == 0:
            return 0
        # Hypothèse : 3m² par caveau (2.5m x 1.2m)
        return int(self.superficie / 3)


class Caveau(models.Model):
    """Caveau / emplacement funéraire."""
    
    class Statut(models.TextChoices):
        DISPONIBLE = 'DISPONIBLE', 'Disponible'
        RESERVE = 'RESERVE', 'Réservé'
        OCCUPE = 'OCCUPE', 'Occupé'
        NON_EXPLOITABLE = 'NON_EXPLOITABLE', 'Non exploitable'
    
    class TypeCaveau(models.TextChoices):
        INDIVIDUEL = 'INDIVIDUEL', 'Individuel'
        FAMILIAL = 'FAMILIAL', 'Familial'
        COLLECTIF = 'COLLECTIF', 'Collectif'
        URNAIRE = 'URNAIRE', 'Urinaire'
    
    code = models.CharField(max_length=20, unique=True)
    numero = models.CharField(max_length=20, blank=True)
    zone = models.ForeignKey(Zone, on_delete=models.PROTECT, related_name='caveaux')
    statut = models.CharField(max_length=20, choices=Statut.choices, default=Statut.DISPONIBLE)
    type_caveau = models.CharField(max_length=20, choices=TypeCaveau.choices, default=TypeCaveau.INDIVIDUEL)
    longueur = models.DecimalField(max_digits=5, decimal_places=2, default=2.5)
    largeur = models.DecimalField(max_digits=5, decimal_places=2, default=1.2)
    profondeur = models.DecimalField(max_digits=5, decimal_places=2, default=1.5)
    prix_concession = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    prix_perpetuite = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    position_gps = gis_models.PointField('Position GPS', null=True, blank=True)
    rangee = models.CharField('Rangée', max_length=20, blank=True)
    numero_place = models.CharField('Numéro de place', max_length=20, blank=True)
    cree_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='caveaux_crees',
        verbose_name='Créé par'
    )
    coordonnees_gps = gis_models.PointField(null=True, blank=True)
    notes = models.TextField(blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['zone', 'code']
        verbose_name = 'Caveau'
        verbose_name_plural = 'Caveaux'
    
    def __str__(self):
        return f"{self.code} ({self.zone.code})"
    
    def est_reservable(self):
        """Vérifie si le caveau peut être réservé."""
        return self.statut == self.Statut.DISPONIBLE
    
    def reserver(self):
        """Réserve le caveau."""
        if not self.est_reservable():
            raise ValueError("Ce caveau n'est pas disponible")
        self.statut = self.Statut.RESERVE
        self.save()
    
    def valider_reservation(self):
        """Valide la réservation (passe en occupé)."""
        if self.statut != self.Statut.RESERVE:
            raise ValueError("Le caveau n'est pas en statut réservé")
        self.statut = self.Statut.OCCUPE
        self.save()
    
    def liberer(self):
        """Libère le caveau."""
        self.statut = self.Statut.DISPONIBLE
        self.save()


class Defunt(models.Model):
    """Personne décédée."""
    
    class Sexe(models.TextChoices):
        MASCULIN = 'M', 'Masculin'
        FEMININ = 'F', 'Féminin'
        AUTRE = 'A', 'Autre'
    
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    date_naissance = models.DateField(null=True, blank=True)
    date_deces = models.DateField()
    lieu_deces = models.CharField(max_length=200, blank=True)
    sexe = models.CharField(max_length=1, choices=Sexe.choices, default=Sexe.MASCULIN)
    numero_identite = models.CharField(max_length=50, blank=True)
    nom_pere = models.CharField(max_length=100, blank=True)
    nom_mere = models.CharField(max_length=100, blank=True)
    photo = models.ImageField('Photo', upload_to='defunts/photos/', blank=True, null=True)
    nationalite = models.CharField('Nationalité', max_length=100, blank=True)
    numero_acte_deces = models.CharField('N° acte de décès', max_length=50, blank=True)
    notes = models.TextField(blank=True)
    date_enregistrement = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-date_deces', 'nom']
        verbose_name = 'Défunt'
        verbose_name_plural = 'Défunts'
    
    def __str__(self):
        return f"{self.nom} {self.prenom}"
    
    def get_full_name(self):
        return f"{self.prenom} {self.nom}"
    
    def age_au_deces(self):
        """Calcule l'âge au décès."""
        if not self.date_naissance:
            return None
        return (self.date_deces - self.date_naissance).days // 365


class Concession(models.Model):
    """Concession funéraire."""
    
    class TypeConcession(models.TextChoices):
        TEMPORAIRE = 'TEMPORAIRE', 'Temporaire'
        PERPETUELLE = 'PERPETUELLE', 'Perpétuelle'
    
    class StatutConcession(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        EXPIREE = 'EXPIREE', 'Expirée'
        RESILIEE = 'RESILIEE', 'Résiliée'
        RENOUVELEE = 'RENOUVELEE', 'Renouvelée'
    
    numero_contrat = models.CharField(max_length=50, unique=True)
    concessionnaire = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='concessions'
    )
    caveau = models.ForeignKey(Caveau, on_delete=models.PROTECT, related_name='concessions')
    defunt = models.ForeignKey(Defunt, on_delete=models.SET_NULL, null=True, blank=True, related_name='concessions')
    type_concession = models.CharField(max_length=20, choices=TypeConcession.choices, default=TypeConcession.TEMPORAIRE)
    duree_annees = models.IntegerField(null=True, blank=True)
    date_debut = models.DateField()
    date_fin = models.DateField(null=True, blank=True)
    date_signature = models.DateField(auto_now_add=True)
    statut = models.CharField(max_length=20, choices=StatutConcession.choices, default=StatutConcession.ACTIVE)
    montant_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    montant_paye = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    document_contrat = models.FileField(
        'Document du contrat',
        upload_to='concessions/documents/',
        blank=True
    )
    cree_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='concessions_crees',
        verbose_name='Créé par'
    )
    notes = models.TextField(blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date_debut']
        verbose_name = 'Concession'
        verbose_name_plural = 'Concessions'
    
    def __str__(self):
        return f"{self.numero_contrat} - {self.caveau.code}"
    
    def save(self, *args, **kwargs):
        """Calcule automatiquement la date de fin pour les concessions temporaires."""
        if self.type_concession == self.TypeConcession.TEMPORAIRE and self.duree_annees and not self.date_fin:
            self.date_fin = self.date_debut + timedelta(days=365 * self.duree_annees)
        super().save(*args, **kwargs)
    
    def est_active(self):
        """Vérifie si la concession est active."""
        if self.statut != self.StatutConcession.ACTIVE:
            return False
        if self.type_concession == self.TypeConcession.PERPETUELLE:
            return True
        if self.date_fin and self.date_fin < timezone.now().date():
            return False
        return True
    
    def jours_restants(self):
        """Calcule les jours restants."""
        if not self.date_fin:
            return None
        delta = self.date_fin - timezone.now().date()
        return max(0, delta.days)


class Inhumation(models.Model):
    """Inhumation d'un défunt dans un caveau."""
    
    concession = models.ForeignKey(Concession, on_delete=models.CASCADE, related_name='inhumations')
    defunt = models.ForeignKey(Defunt, on_delete=models.PROTECT, related_name='inhumations')
    date_inhumation = models.DateField()
    profondeur = models.DecimalField(
        'Profondeur (m)',
        max_digits=5,
        decimal_places=2,
        default=1.5
    )
    numero_place_dans_caveau = models.CharField(
        'N° place dans caveau',
        max_length=20,
        blank=True
    )
    enregistre_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inhumations_enregistrees',
        verbose_name='Enregistré par'
    )
    notes = models.TextField(blank=True)
    date_enregistrement = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-date_inhumation']
        verbose_name = 'Inhumation'
        verbose_name_plural = 'Inhumations'
    
    def __str__(self):
        return f"{self.defunt} - {self.date_inhumation}"


class ParametreCimetiere(models.Model):
    """Paramètres globaux du cimetière."""
    
    nom = models.CharField('Nom du cimetière', max_length=200)
    adresse = models.TextField('Adresse', blank=True)
    coordonnees_centre = gis_models.PointField(
        'Coordonnées du centre',
        null=True,
        blank=True,
        help_text='Coordonnées GPS du centre du cimetière'
    )
    
    # Dimensions standards
    superficie_totale = models.DecimalField(
        'Superficie totale (m²)',
        max_digits=10,
        decimal_places=2,
        default=0
    )
    longueur_standard_caveau = models.DecimalField(
        'Longueur standard caveau (m)',
        max_digits=5,
        decimal_places=2,
        default=2.5
    )
    largeur_standard_caveau = models.DecimalField(
        'Largeur standard caveau (m)',
        max_digits=5,
        decimal_places=2,
        default=1.2
    )
    largeur_allee = models.DecimalField(
        'Largeur allée (m)',
        max_digits=5,
        decimal_places=2,
        default=3.0
    )
    
    # Métadonnées
    date_creation = models.DateTimeField('Date de création', auto_now_add=True)
    date_modification = models.DateTimeField('Date de modification', auto_now=True)
    
    class Meta:
        verbose_name = 'Paramètre du cimetière'
        verbose_name_plural = 'Paramètres du cimetière'
    
    def __str__(self):
        return self.nom


class DemandeExhumation(models.Model):
    """Demande d'exhumation d'un défunt."""

    class StatutDemande(models.TextChoices):
        EN_ATTENTE = 'EN_ATTENTE', 'En attente'
        VALIDEE = 'VALIDEE', 'Validée'
        REFUSEE = 'REFUSEE', 'Refusée'
        REALISEE = 'REALISEE', 'Réalisée'

    class Destination(models.TextChoices):
        AUTRE_CIMETIERE = 'AUTRE_CIMETIERE', 'Autre cimetière'
        DOMICILE = 'DOMICILE', 'Domicile familial'
        CRAMATORIUM = 'CRAMATORIUM', 'Cramatorium'
        AUTRE = 'AUTRE', 'Autre'

    # Inhumation concernée
    inhumation = models.ForeignKey(
        Inhumation,
        on_delete=models.PROTECT,
        related_name='demandes_exhumation',
        verbose_name='Inhumation concernée'
    )

    # Demandeur
    demandeur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='demandes_exhumation',
        verbose_name='Demandeur'
    )
    nom_demandeur = models.CharField('Nom du demandeur', max_length=200)
    lien_parente = models.CharField('Lien de parenté', max_length=100)
    telephone_demandeur = models.CharField('Téléphone', max_length=20, blank=True)

    # Détails
    motif = models.TextField('Motif de la demande')
    destination = models.CharField(
        'Destination',
        max_length=30,
        choices=Destination.choices,
        default=Destination.AUTRE_CIMETIERE
    )

    # Documents
    autorisation_mairie = models.FileField(
        'Autorisation de la mairie',
        upload_to='exhumations/autorisations/',
        blank=True
    )
    proces_verbal = models.FileField(
        'Procès-verbal',
        upload_to='exhumations/proces_verbaux/',
        blank=True
    )

    # Statut
    statut = models.CharField(
        'Statut',
        max_length=20,
        choices=StatutDemande.choices,
        default=StatutDemande.EN_ATTENTE,
        db_index=True
    )
    motif_refus = models.TextField('Motif du refus', blank=True)

    # Dates
    date_demande = models.DateTimeField('Date de la demande', default=timezone.now)
    date_validation = models.DateTimeField('Date de validation', null=True, blank=True)
    date_realisation = models.DateTimeField('Date de réalisation', null=True, blank=True)
    date_modification = models.DateTimeField('Date de modification', auto_now=True)

    # Validation
    valide_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='exhumations_validees_admin',
        verbose_name='Validée par'
    )

    # Notes
    notes = models.TextField('Notes', blank=True)

    class Meta:
        verbose_name = 'Demande d\'exhumation'
        verbose_name_plural = 'Demandes d\'exhumation'
        ordering = ['-date_demande']

    def __str__(self):
        return f"Demande #{self.id} - {self.nom_demandeur} ({self.get_statut_display()})"

    def valider(self, utilisateur):
        """Valide la demande d'exhumation."""
        if self.statut != self.StatutDemande.EN_ATTENTE:
            raise ValueError("Seules les demandes en attente peuvent être validées")
        self.statut = self.StatutDemande.VALIDEE
        self.date_validation = timezone.now()
        self.valide_par = utilisateur
        self.save()

    def refuser(self, motif, utilisateur):
        """Refuse la demande d'exhumation."""
        if self.statut != self.StatutDemande.EN_ATTENTE:
            raise ValueError("Seules les demandes en attente peuvent être refusées")
        self.statut = self.StatutDemande.REFUSEE
        self.motif_refus = motif
        self.valide_par = utilisateur
        self.save()