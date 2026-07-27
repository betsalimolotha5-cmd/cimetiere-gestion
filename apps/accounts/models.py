"""
Modèles pour la gestion des utilisateurs et authentification.
AMÉLIORÉ : Système de permissions RBAC complet basé sur le CDC.
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
    
    # === Permissions (constantes pour le CDC) ===
    # Ces constantes définissent toutes les actions possibles du système
    PERMISSIONS = {
        # Gestion des caveaux
        'VIEW_CAVEAUX': 'view_caveaux',
        'CREATE_CAVEAUX': 'create_caveaux',
        'UPDATE_CAVEAUX': 'update_caveaux',
        'DELETE_CAVEAUX': 'delete_caveaux',
        
        # Gestion des zones
        'VIEW_ZONES': 'view_zones',
        'CREATE_ZONES': 'create_zones',
        'UPDATE_ZONES': 'update_zones',
        'DELETE_ZONES': 'delete_zones',
        
        # Gestion des concessions
        'VIEW_CONCESSIONS': 'view_concessions',
        'CREATE_CONCESSIONS': 'create_concessions',
        'UPDATE_CONCESSIONS': 'update_concessions',
        'DELETE_CONCESSIONS': 'delete_concessions',
        'GENERATE_CONTRACT_PDF': 'generate_contract_pdf',
        'GENERATE_ATTESTATION_PDF': 'generate_attestation_pdf',
        
        # Gestion des défunts
        'VIEW_DEFUNTS': 'view_defunts',
        'CREATE_DEFUNTS': 'create_defunts',
        'UPDATE_DEFUNTS': 'update_defunts',
        'DELETE_DEFUNTS': 'delete_defunts',
        
        # Gestion des inhumations
        'VIEW_INHUMATIONS': 'view_inhumations',
        'CREATE_INHUMATIONS': 'create_inhumations',
        'UPDATE_INHUMATIONS': 'update_inhumations',
        'DELETE_INHUMATIONS': 'delete_inhumations',
        'GENERATE_PV_INHUMATION_PDF': 'generate_pv_inhumation_pdf',
        
        # Gestion des exhumations
        'VIEW_EXHUMATIONS': 'view_exhumations',
        'CREATE_EXHUMATION_REQUEST': 'create_exhumation_request',
        'VALIDATE_EXHUMATION': 'validate_exhumation',
        'REFUSE_EXHUMATION': 'refuse_exhumation',
        'GENERATE_EXHUMATION_PDF': 'generate_exhumation_pdf',
        
        # Statistiques et rapports
        'VIEW_STATISTICS': 'view_statistics',
        'VIEW_FINANCIAL_STATS': 'view_financial_stats',
        'GENERATE_STATISTICAL_REPORT': 'generate_statistical_report',
        
        # Gestion des utilisateurs (Admin uniquement)
        'MANAGE_USERS': 'manage_users',
        'VIEW_AUDIT_LOGS': 'view_audit_logs',
        
        # Configuration du système
        'MANAGE_SETTINGS': 'manage_settings',
        
        # Accès public (tous les utilisateurs)
        'VIEW_PUBLIC_MAP': 'view_public_map',
    }
    
    # Matrice des permissions par rôle
    ROLE_PERMISSIONS = {
        Role.ADMIN: [
            # Admin a TOUTES les permissions
            'view_caveaux', 'create_caveaux', 'update_caveaux', 'delete_caveaux',
            'view_zones', 'create_zones', 'update_zones', 'delete_zones',
            'view_concessions', 'create_concessions', 'update_concessions', 'delete_concessions',
            'generate_contract_pdf', 'generate_attestation_pdf',
            'view_defunts', 'create_defunts', 'update_defunts', 'delete_defunts',
            'view_inhumations', 'create_inhumations', 'update_inhumations', 'delete_inhumations',
            'generate_pv_inhumation_pdf',
            'view_exhumations', 'create_exhumation_request', 'validate_exhumation', 'refuse_exhumation',
            'generate_exhumation_pdf',
            'view_statistics', 'view_financial_stats', 'generate_statistical_report',
            'manage_users', 'view_audit_logs',
            'manage_settings',
            'view_public_map',
        ],
        Role.FIELD_AGENT: [
            # Agent de terrain : gestion opérationnelle
            'view_caveaux', 'create_caveaux', 'update_caveaux',
            'view_zones',
            'view_concessions', 'create_concessions', 'update_concessions',
            'generate_contract_pdf', 'generate_attestation_pdf',
            'view_defunts', 'create_defunts', 'update_defunts',
            'view_inhumations', 'create_inhumations', 'update_inhumations',
            'generate_pv_inhumation_pdf',
            'view_exhumations', 'create_exhumation_request',
            'view_statistics',
            'view_public_map',
        ],
        Role.SECRETARY: [
            # Secrétariat : gestion administrative
            'view_caveaux', 'create_caveaux', 'update_caveaux',
            'view_zones',
            'view_concessions', 'create_concessions', 'update_concessions',
            'generate_contract_pdf', 'generate_attestation_pdf',
            'view_defunts', 'create_defunts', 'update_defunts',
            'view_inhumations', 'create_inhumations', 'update_inhumations',
            'generate_pv_inhumation_pdf',
            'view_exhumations', 'validate_exhumation', 'refuse_exhumation',
            'generate_exhumation_pdf',
            'view_statistics',
            'view_public_map',
        ],
        Role.CLIENT: [
            # Client : consultation uniquement
            'view_public_map',
            'view_concessions',  # Voir ses propres concessions (filtré dans les vues)
            'create_exhumation_request',  # Demander une exhumation
        ],
    }
    
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
    
    def has_permission(self, permission):
        """
        Vérifie si l'utilisateur a une permission spécifique.
        
        Args:
            permission (str): La permission à vérifier (ex: 'view_caveaux')
        
        Returns:
            bool: True si l'utilisateur a la permission, False sinon
        """
        # Admin et superuser ont toutes les permissions
        if self.is_admin() or self.is_superuser:
            return True
        
        # Vérifier dans la matrice des permissions
        role_permissions = self.ROLE_PERMISSIONS.get(self.role, [])
        return permission in role_permissions
    
    def get_all_permissions(self):
        """Retourne la liste de toutes les permissions de l'utilisateur."""
        if self.is_admin() or self.is_superuser:
            return list(self.PERMISSIONS.values())
        return self.ROLE_PERMISSIONS.get(self.role, [])
    
    # === Méthodes de permissions spécifiques (compatibilité avec l'ancien code) ===
    
    def can_manage_caveaux(self):
        """Vérifie si l'utilisateur peut gérer les caveaux."""
        return self.has_permission('create_caveaux') or self.has_permission('update_caveaux')
    
    def can_validate_reservations(self):
        """Vérifie si l'utilisateur peut valider les réservations."""
        return self.is_admin() or self.is_secretary()
    
    def can_view_financial_stats(self):
        """Vérifie si l'utilisateur peut voir les statistiques financières."""
        return self.has_permission('view_financial_stats')
    
    def can_generate_pdfs(self):
        """Vérifie si l'utilisateur peut générer des PDF."""
        return (self.has_permission('generate_contract_pdf') or 
                self.has_permission('generate_attestation_pdf') or
                self.has_permission('generate_pv_inhumation_pdf') or
                self.has_permission('generate_exhumation_pdf'))
    
    def can_manage_exhumations(self):
        """Vérifie si l'utilisateur peut gérer les exhumations."""
        return (self.has_permission('validate_exhumation') or 
                self.has_permission('refuse_exhumation'))
    
    def can_view_audit_logs(self):
        """Vérifie si l'utilisateur peut voir les logs d'audit."""
        return self.has_permission('view_audit_logs')
    
    def can_manage_users(self):
        """Vérifie si l'utilisateur peut gérer les utilisateurs."""
        return self.has_permission('manage_users')
    
    def can_view_statistics(self):
        """Vérifie si l'utilisateur peut voir les statistiques."""
        return self.has_permission('view_statistics')
    
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