"""
Modèles pour l'authentification à double facteur (MFA).
"""
from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import secrets


class MFACode(models.Model):
    """Code MFA temporaire envoyé par email."""
    
    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='mfa_codes',
        verbose_name='Utilisateur'
    )
    code = models.CharField('Code', max_length=6)
    date_creation = models.DateTimeField('Date de création', auto_now_add=True)
    date_expiration = models.DateTimeField('Date d\'expiration')
    utilise = models.BooleanField('Utilisé', default=False)
    ip_address = models.GenericIPAddressField(
        'Adresse IP',
        null=True,
        blank=True
    )
    
    class Meta:
        verbose_name = 'Code MFA'
        verbose_name_plural = 'Codes MFA'
        ordering = ['-date_creation']
        indexes = [
            models.Index(fields=['utilisateur', 'utilise']),
            models.Index(fields=['date_expiration']),
        ]
    
    def __str__(self):
        return f"Code MFA pour {self.utilisateur} - {self.code}"
    
    def est_valide(self):
        """Vérifie si le code est encore valide."""
        return not self.utilise and self.date_expiration > timezone.now()
    
    @classmethod
    def generer_code(cls, utilisateur, ip_address=None):
        """Génère un nouveau code MFA pour un utilisateur."""
        # Invalider les anciens codes
        cls.objects.filter(
            utilisateur=utilisateur,
            utilise=False
        ).update(utilise=True)
        
        # Générer un code à 6 chiffres
        code = ''.join([str(secrets.randbelow(10)) for _ in range(6)])
        
        return cls.objects.create(
            utilisateur=utilisateur,
            code=code,
            date_expiration=timezone.now() + timedelta(minutes=10),
            ip_address=ip_address
        ) 
