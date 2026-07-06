"""
Administration Django pour le modèle User.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Administration personnalisée pour le modèle User."""
    
    # Colonnes affichées dans la liste
    list_display = (
        'email',
        'get_full_name',
        'role',
        'mfa_enabled',
        'is_active',
        'is_staff',
        'date_joined',
        'last_login',
    )
    
    # Filtres latéraux
    list_filter = (
        'role',
        'is_active',
        'is_staff',
        'mfa_enabled',
        'email_verified',
        'date_joined',
    )
    
    # Barre de recherche
    search_fields = (
        'email',
        'first_name',
        'last_name',
        'phone',
        'employee_id',
        'national_id',
    )
    
    # Ordre par défaut
    ordering = ('-date_joined',)
    
    # Actions groupées
    actions = [
        'activate_users',
        'deactivate_users',
        'enable_mfa_for_users',
        'disable_mfa_for_users',
    ]
    
    # Lecture seule pour les champs sensibles
    readonly_fields = (
        'date_joined',
        'last_login',
        'last_login_ip',
        'mfa_secret',
    )
    
    # Organisation des champs par sections
    fieldsets = (
        (_('Informations de connexion'), {
            'fields': ('email', 'password'),
        }),
        (_('Informations personnelles'), {
            'fields': ('first_name', 'last_name', 'phone', 'address'),
        }),
        (_('Rôle et permissions'), {
            'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Sécurité MFA'), {
            'fields': ('mfa_enabled', 'mfa_verified', 'mfa_secret'),
            'classes': ('collapse',),
        }),
        (_('Informations professionnelles'), {
            'fields': ('employee_id', 'assignment_zone'),
            'classes': ('collapse',),
            'description': _('Uniquement pour les agents de terrain'),
        }),
        (_('Identification'), {
            'fields': ('national_id',),
            'classes': ('collapse',),
            'description': _('Uniquement pour les clients'),
        }),
        (_('Métadonnées'), {
            'fields': ('date_joined', 'last_login', 'last_login_ip', 'email_verified'),
        }),
    )
    
    # Configuration du formulaire de création
    add_fieldsets = (
        (_('Créer un nouvel utilisateur'), {
            'classes': ('wide',),
            'fields': (
                'email',
                'password1',
                'password2',
                'first_name',
                'last_name',
                'role',
                'phone',
                'is_active',
                'is_staff',
            ),
        }),
    )
    
    # === Actions groupées ===
    
    @admin.action(description=_('Activer les utilisateurs sélectionnés'))
    def activate_users(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} utilisateur(s) activé(s).')
    
    @admin.action(description=_('Désactiver les utilisateurs sélectionnés'))
    def deactivate_users(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} utilisateur(s) désactivé(s).')
    
    @admin.action(description=_('Activer le MFA pour les utilisateurs sélectionnés'))
    def enable_mfa_for_users(self, request, queryset):
        updated = queryset.update(mfa_enabled=True)
        self.message_user(request, f'MFA activé pour {updated} utilisateur(s).')
    
    @admin.action(description=_('Désactiver le MFA pour les utilisateurs sélectionnés'))
    def disable_mfa_for_users(self, request, queryset):
        updated = queryset.update(mfa_enabled=False)
        self.message_user(request, f'MFA désactivé pour {updated} utilisateur(s).')
    
    # === Méthodes personnalisées pour l'affichage ===
    
    @admin.display(description=_('Nom complet'), ordering='last_name')
    def get_full_name(self, obj):
        return obj.get_full_name()