"""
Administration des codes MFA.
"""
from django.contrib import admin
from django.utils import timezone
from .models import MFACode


@admin.register(MFACode)
class MFACodeAdmin(admin.ModelAdmin):
    """Administration des codes MFA."""

    list_display = (
        'utilisateur',
        'code_masque',
        'date_creation',
        'date_expiration',
        'est_valide_display',
        'utilise',
        'ip_address',
    )

    list_filter = (
        'utilise',
        'date_creation',
        'date_expiration',
    )

    search_fields = (
        'utilisateur__email',
        'utilisateur__first_name',
        'utilisateur__last_name',
        'code',
        'ip_address',
    )

    readonly_fields = (
        'utilisateur',
        'code',
        'date_creation',
        'date_expiration',
        'utilise',
        'ip_address',
    )

    fieldsets = (
        ('Informations', {
            'fields': ('utilisateur', 'code', 'ip_address')
        }),
        ('Dates', {
            'fields': ('date_creation', 'date_expiration')
        }),
        ('Statut', {
            'fields': ('utilise',)
        }),
    )

    @admin.display(description='Code')
    def code_masque(self, obj):
        """Affiche le code masqué pour la sécurité."""
        if obj.code:
            return '••••' + obj.code[-2:]
        return '-'

    @admin.display(description='Valide ?', boolean=True)
    def est_valide_display(self, obj):
        """Affiche si le code est encore valide."""
        return obj.est_valide()

    def has_add_permission(self, request):
        """Empêche l'ajout manuel de codes MFA."""
        return False

    def has_change_permission(self, request, obj=None):
        """Empêche la modification des codes MFA."""
        return False 
