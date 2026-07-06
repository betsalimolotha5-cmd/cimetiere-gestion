"""
Modèles pour la gestion des utilisateurs et authentification.
"""
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
import pyotp


class UserManager(BaseUserManager):
    """Manager personnalisé pour le modèle User."""
    
    def create_user(self, email, password=None, **extra_fields):
        """Créer et sauvegarder un utilisateur standard."""
        if not email:
            raise ValueError('L\'adresse email est obligatoire')
        
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        """Créer et sauvegarder un superutilisateur."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('role', User.Role.ADMIN)
        extra_fields.setdefault('mfa_enabled', False)  # Admin n'a pas besoin de MFA
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Le superutilisateur doit avoir is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Le superutilisateur doit avoir is_superuser=True.')
        
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Modèle utilisateur personnalisé avec RBAC et MFA."""
    
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Administrateur'
        FIELD_AGENT = 'FIELD_AGENT', 'Agent de terrain'
        SECRETARY = 'SECRETARY', 'Secrétariat'
        CLIENT = 'CLIENT', 'Client (Citoyen)'
    
    # Informations de connexion
    email = models.EmailField('Adresse email', unique=True, db_index=True)
    is_active = models.BooleanField('Actif', default=True)
    is_staff = models.BooleanField('Staff', default=False)
    date_joined = models.DateTimeField('Date d\'inscription', default=timezone.now)
    
    # Rôle et permissions
    role = models.CharField(
        'Rôle',
        max_length=20,
        choices=Role.choices,
        default=Role.CLIENT
    )
    
    # MFA (Authentification à double facteur)
    mfa_enabled = models.BooleanField('MFA activé', default=True)
    mfa_secret = models.CharField('Clé secrète MFA', max_length=32, blank=True)
    mfa_verified = models.BooleanField('MFA vérifié', default=False)
    
    # Informations personnelles (communes)
    first_name = models.CharField('Prénom', max_length=150, blank=True)
    last_name = models.CharField('Nom', max_length=150, blank=True)
    phone = models.CharField('Téléphone', max_length=20, blank=True)
    
    # Informations spécifiques aux agents de terrain
    employee_id = models.CharField('Matricule employé', max_length=50, blank=True)
    assignment_zone = models.CharField('Zone d\'affectation', max_length=100, blank=True)
    
    # Informations spécifiques aux clients
    national_id = models.CharField('Numéro d\'identité nationale', max_length=50, blank=True)
    address = models.TextField('Adresse', blank=True)
    
    # Métadonnées
    last_login_ip = models.GenericIPAddressField('Dernière IP de connexion', null=True, blank=True)
    email_verified = models.BooleanField('Email vérifié', default=False)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    
    class Meta:
        verbose_name = 'Utilisateur'
        verbose_name_plural = 'Utilisateurs'
        ordering = ['-date_joined']
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.get_role_display()})"
    
    def get_full_name(self):
        """Retourne le nom complet de l'utilisateur."""
        return f"{self.first_name} {self.last_name}".strip()
    
    def get_short_name(self):
        """Retourne le prénom."""
        return self.first_name
    
    # === Méthodes RBAC ===
    
    def is_admin(self):
        """Vérifie si l'utilisateur est administrateur."""
        return self.role == self.Role.ADMIN or self.is_superuser
    
    def is_field_agent(self):
        """Vérifie si l'utilisateur est agent de terrain."""
        return self.role == self.Role.FIELD_AGENT
    
    def is_secretary(self):
        """Vérifie si l'utilisateur est secrétaire."""
        return self.role == self.Role.SECRETARY
    
    def is_client(self):
        """Vérifie si l'utilisateur est client."""
        return self.role == self.Role.CLIENT
    
    def can_manage_caveaux(self):
        """Vérifie si l'utilisateur peut gérer les caveaux."""
        return self.is_admin() or self.is_field_agent()
    
    def can_validate_reservations(self):
        """Vérifie si l'utilisateur peut valider les réservations."""
        return self.is_admin() or self.is_secretary()
    
    def can_view_financial_stats(self):
        """Vérifie si l'utilisateur peut voir les statistiques financières."""
        return self.is_admin()
    
    # === Méthodes MFA ===
    
    def generate_mfa_secret(self):
        """Génère une nouvelle clé secrète MFA."""
        self.mfa_secret = pyotp.random_base32()
        self.save(update_fields=['mfa_secret'])
        return self.mfa_secret
    
    def get_mfa_token(self):
        """Génère un token MFA basé sur le temps (TOTP)."""
        if not self.mfa_secret:
            self.generate_mfa_secret()
        totp = pyotp.TOTP(self.mfa_secret)
        return totp.now()
    
    def verify_mfa_token(self, token):
        """Vérifie un token MFA."""
        if not self.mfa_secret:
            return False
        totp = pyotp.TOTP(self.mfa_secret)
        return totp.verify(token)
    
    def save(self, *args, **kwargs):
        """Surcharge de save pour générer automatiquement la clé MFA."""
        if not self.mfa_secret and self.mfa_enabled:
            self.mfa_secret = pyotp.random_base32()
        super().save(*args, **kwargs)