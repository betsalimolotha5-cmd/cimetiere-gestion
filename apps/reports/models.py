"""
Modèles pour les rapports générés.
"""
from django.db import models
from django.conf import settings


class RapportGenere(models.Model):
    """Rapport généré et sauvegardé."""
    
    class TypeRapport(models.TextChoices):
        OCCUPATION = 'OCCUPATION', 'Taux d\'occupation'
        FINANCIER = 'FINANCIER', 'Rapport financier'
        CONCESSIONS = 'CONCESSIONS', 'Concessions'
        DEFUNTS = 'DEFUNTS', 'Défunts'
        EXPIRATIONS = 'EXPIRATIONS', 'Concessions expirantes'
        PERSONNALISE = 'PERSONNALISE', 'Rapport personnalisé'
    
    class FormatExport(models.TextChoices):
        PDF = 'PDF', 'PDF'
        EXCEL = 'EXCEL', 'Excel'
        CSV = 'CSV', 'CSV'
    
    titre = models.CharField(max_length=200)
    type_rapport = models.CharField(
        max_length=20,
        choices=TypeRapport.choices,
        default=TypeRapport.OCCUPATION
    )
    format_export = models.CharField(
        max_length=10,
        choices=FormatExport.choices,
        default=FormatExport.PDF
    )
    fichier = models.FileField(upload_to='rapports/%Y/%m/')
    genere_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='rapports_generes'
    )
    parametres = models.JSONField(default=dict, blank=True)
    date_generation = models.DateTimeField(auto_now_add=True)
    nombre_lignes = models.IntegerField(default=0)
    taille_fichier = models.BigIntegerField(default=0)  # en bytes
    
    class Meta:
        ordering = ['-date_generation']
        verbose_name = 'Rapport généré'
        verbose_name_plural = 'Rapports générés'
    
    def __str__(self):
        return f"{self.titre} ({self.get_format_export_display()})"
    
    def taille_formatee(self):
        """Retourne la taille formatée."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if self.taille_fichier < 1024:
                return f"{self.taille_fichier:.1f} {unit}"
            self.taille_fichier /= 1024
        return f"{self.taille_fichier:.1f} TB"