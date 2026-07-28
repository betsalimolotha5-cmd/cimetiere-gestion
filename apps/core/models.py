"""
Modèles de l'application core.
AJOUT : Mise à jour automatique du statut du caveau à 'OCCUPE' lors d'une nouvelle inhumation.
AJOUT : Modèle RappelExpiration pour le suivi des relances automatiques.
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
    coordonnees_gps = gis_models.PointField(null=True, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['code']
        verbose_name = 'Zone'
        verbose_name_plural = 'Zones'
    
    def __str__(self):
        return f"{self.nom} ({self.code})"
    
    def calculer_capacite_theorique(self):
        if not self.superficie or self.superficie == 0:
            return 0
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
        return self.statut == self.Statut.DISPONIBLE
    
    def reserver(self):
        if not self.est_reservable():
            raise ValueError("Ce caveau n'est pas disponible")
        self.statut = self.Statut.RESERVE
        self.save()
    
    def valider_reservation(self):
        if self.statut != self.Statut.RESERVE:
            raise ValueError("Le caveau n'est pas en statut réservé")
        self.statut = self.Statut.OCCUPE
        self.save()
    
    def liberer(self):
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
    document_contrat = models.FileField('Document du contrat', upload_to='concessions/documents/', blank=True)
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
        if self.type_concession == self.TypeConcession.TEMPORAIRE and self.duree_annees and not self.date_fin:
            self.date_fin = self.date_debut + timedelta(days=365 * self.duree_annees)
        super().save(*args, **kwargs)
    
    def est_active(self):
        if self.statut != self.StatutConcession.ACTIVE:
            return False
        if self.type_concession == self.TypeConcession.PERPETUELLE:
            return True
        if self.date_fin and self.date_fin < timezone.now().date():
            return False
        return True
    
    def jours_restants(self):
        if not self.date_fin:
            return None
        delta = self.date_fin - timezone.now().date()
        return max(0, delta.days)


class Inhumation(models.Model):
    """Inhumation d'un défunt dans un caveau."""
    
    concession = models.ForeignKey(Concession, on_delete=models.CASCADE, related_name='inhumations')
    defunt = models.ForeignKey(Defunt, on_delete=models.PROTECT, related_name='inhumations')
    date_inhumation = models.DateField()
    profondeur = models.DecimalField('Profondeur (m)', max_digits=5, decimal_places=2, default=1.5)
    numero_place_dans_caveau = models.CharField('N° place dans caveau', max_length=20, blank=True)
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

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if is_new and self.concession and self.concession.caveau:
            caveau = self.concession.caveau
            if caveau.statut in [Caveau.Statut.DISPONIBLE, Caveau.Statut.RESERVE]:
                caveau.statut = Caveau.Statut.OCCUPE
                caveau.save(update_fields=['statut', 'date_modification'])


class ParametreCimetiere(models.Model):
    """Paramètres globaux du cimetière."""
    
    nom = models.CharField('Nom du cimetière', max_length=200)
    adresse = models.TextField('Adresse', blank=True)
    coordonnees_centre = gis_models.PointField('Coordonnées du centre', null=True, blank=True, help_text='Coordonnées GPS du centre du cimetière')
    superficie_totale = models.DecimalField('Superficie totale (m²)', max_digits=10, decimal_places=2, default=0)
    longueur_standard_caveau = models.DecimalField('Longueur standard caveau (m)', max_digits=5, decimal_places=2, default=2.5)
    largeur_standard_caveau = models.DecimalField('Largeur standard caveau (m)', max_digits=5, decimal_places=2, default=1.2)
    largeur_allee = models.DecimalField('Largeur allée (m)', max_digits=5, decimal_places=2, default=3.0)
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

    inhumation = models.ForeignKey(Inhumation, on_delete=models.PROTECT, related_name='demandes_exhumation', verbose_name='Inhumation concernée')
    demandeur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='demandes_exhumation', verbose_name='Demandeur')
    nom_demandeur = models.CharField('Nom du demandeur', max_length=200)
    lien_parente = models.CharField('Lien de parenté', max_length=100)
    telephone_demandeur = models.CharField('Téléphone', max_length=20, blank=True)
    motif = models.TextField('Motif de la demande')
    destination = models.CharField('Destination', max_length=30, choices=Destination.choices, default=Destination.AUTRE_CIMETIERE)
    autorisation_mairie = models.FileField('Autorisation de la mairie', upload_to='exhumations/autorisations/', blank=True)
    proces_verbal = models.FileField('Procès-verbal', upload_to='exhumations/proces_verbaux/', blank=True)
    statut = models.CharField('Statut', max_length=20, choices=StatutDemande.choices, default=StatutDemande.EN_ATTENTE, db_index=True)
    motif_refus = models.TextField('Motif du refus', blank=True)
    date_demande = models.DateTimeField('Date de la demande', default=timezone.now)
    date_validation = models.DateTimeField('Date de validation', null=True, blank=True)
    date_realisation = models.DateTimeField('Date de réalisation', null=True, blank=True)
    date_modification = models.DateTimeField('Date de modification', auto_now=True)
    valide_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='exhumations_validees_admin', verbose_name='Validée par')
    notes = models.TextField('Notes', blank=True)

    class Meta:
        verbose_name = 'Demande d\'exhumation'
        verbose_name_plural = 'Demandes d\'exhumation'
        ordering = ['-date_demande']

    def __str__(self):
        return f"Demande #{self.id} - {self.nom_demandeur} ({self.get_statut_display()})"

    def valider(self, utilisateur):
        if self.statut != self.StatutDemande.EN_ATTENTE:
            raise ValueError("Seules les demandes en attente peuvent être validées")
        self.statut = self.StatutDemande.VALIDEE
        self.date_validation = timezone.now()
        self.valide_par = utilisateur
        self.save()

    def refuser(self, motif, utilisateur):
        if self.statut != self.StatutDemande.EN_ATTENTE:
            raise ValueError("Seules les demandes en attente peuvent être refusées")
        self.statut = self.StatutDemande.REFUSEE
        self.motif_refus = motif
        self.valide_par = utilisateur
        self.save()


class RappelExpiration(models.Model):
    """Historique des rappels d'expiration de concession envoyés automatiquement."""
    
    class TypeRappel(models.TextChoices):
        J30 = 'J30', '30 jours avant'
        J15 = 'J15', '15 jours avant'
        J7 = 'J7', '7 jours avant'
        J0 = 'J0', 'Jour J (Expiré)'
    
    class StatutEnvoi(models.TextChoices):
        SUCCES = 'SUCCES', 'Succès'
        ECHEC = 'ECHEC', 'Échec'
    
    concession = models.ForeignKey(
        Concession,
        on_delete=models.CASCADE,
        related_name='rappels_expiration',
        verbose_name='Concession concernée'
    )
    type_rappel = models.CharField(
        'Type de rappel',
        max_length=10,
        choices=TypeRappel.choices
    )
    date_envoi = models.DateTimeField('Date d\'envoi', auto_now_add=True)
    statut_envoi = models.CharField(
        'Statut de l\'envoi',
        max_length=20,
        choices=StatutEnvoi.choices,
        default=StatutEnvoi.SUCCES
    )
    message_erreur = models.TextField('Message d\'erreur (si échec)', blank=True)
    
    class Meta:
        verbose_name = 'Rappel d\'expiration'
        verbose_name_plural = 'Rappels d\'expiration'
        ordering = ['-date_envoi']
        constraints = [
            models.UniqueConstraint(
                fields=['concession', 'type_rappel'],
                name='unique_rappel_par_concession'
            )
        ]
    
    def __str__(self):
        return f"Rappel {self.get_type_rappel_display()} pour {self.concession.numero_contrat}"