"""
Administration Django pour l'application core (cimetière).
CORRECTION DÉFINITIVE : Suppression du champ 'perimetre' qui n'existe pas dans le modèle ParametreCimetiere.
"""
from django.contrib import admin, messages
from django import forms
from django.utils.html import format_html
from .models import (
    Zone, Caveau, Defunt, Concession, Inhumation,
    ParametreCimetiere, DemandeExhumation
)


# ==============================================================================
# ADMIN : CAVEAU
# ==============================================================================
@admin.register(Caveau)
class CaveauAdmin(admin.ModelAdmin):
    list_display = ('code', 'zone', 'statut_badge', 'type_caveau', 'prix_concession', 'position_display')
    list_filter = ('statut', 'type_caveau', 'zone')
    search_fields = ('code', 'zone__nom')
    
    @admin.display(description='Statut')
    def statut_badge(self, obj):
        try:
            couleurs = {
                'DISPONIBLE': '#27ae60',
                'RESERVE': '#f39c12',
                'OCCUPE': '#e74c3c',
                'NON_EXPLOITABLE': '#95a5a6',
            }
            couleur = couleurs.get(obj.statut, '#95a5a6')
            return format_html(
                '<span style="background: {}; color: white; padding: 4px 12px; '
                'border-radius: 12px; font-size: 11px; font-weight: bold;">{}</span>',
                couleur,
                obj.get_statut_display()
            )
        except Exception:
            return obj.statut if obj.statut else '-'

    @admin.display(description='Position GPS')
    def position_display(self, obj):
        try:
            if hasattr(obj, 'position_gps') and obj.position_gps:
                return f"{obj.position_gps.y:.6f}, {obj.position_gps.x:.6f}"
            elif hasattr(obj, 'coordonnees_gps') and obj.coordonnees_gps:
                return f"{obj.coordonnees_gps.y:.6f}, {obj.coordonnees_gps.x:.6f}"
            return '-'
        except Exception:
            return 'Erreur'


# ==============================================================================
# ADMIN : ZONE
# ==============================================================================
@admin.register(Zone)
class ZoneAdmin(admin.ModelAdmin):
    list_display = ('code', 'nom', 'type_zone', 'est_exploitable', 'superficie', 'capacite_theorique')
    list_filter = ('type_zone', 'est_exploitable')
    search_fields = ('code', 'nom')
    
    @admin.display(description='Capacité théorique')
    def capacite_theorique(self, obj):
        try:
            return obj.calculer_capacite_theorique()
        except Exception:
            return '-'


# ==============================================================================
# ADMIN : DÉFUNT
# ==============================================================================
@admin.register(Defunt)
class DefuntAdmin(admin.ModelAdmin):
    list_display = ('nom', 'prenom', 'date_deces', 'sexe', 'age_au_deces')
    list_filter = ('sexe', 'date_deces')
    search_fields = ('nom', 'prenom', 'numero_identite')
    
    @admin.display(description='Âge au décès')
    def age_au_deces(self, obj):
        try:
            age = obj.age_au_deces()
            return f"{age} ans" if age else '-'
        except Exception:
            return '-'


# ==============================================================================
# ADMIN : CONCESSION
# ==============================================================================
@admin.register(Concession)
class ConcessionAdmin(admin.ModelAdmin):
    list_display = ('numero_contrat', 'concessionnaire', 'caveau', 'type_concession', 'statut_badge', 'date_debut', 'date_fin')
    list_filter = ('type_concession', 'statut', 'date_debut')
    search_fields = ('numero_contrat', 'concessionnaire__email', 'caveau__code')
    readonly_fields = ('date_signature', 'date_creation', 'date_modification')
    
    @admin.display(description='Statut')
    def statut_badge(self, obj):
        try:
            couleurs = {
                'ACTIVE': '#27ae60',
                'EXPIREE': '#e74c3c',
                'RESILIEE': '#95a5a6',
                'RENOUVELEE': '#3498db',
            }
            couleur = couleurs.get(obj.statut, '#95a5a6')
            return format_html(
                '<span style="background: {}; color: white; padding: 4px 12px; '
                'border-radius: 12px; font-size: 11px; font-weight: bold;">{}</span>',
                couleur,
                obj.get_statut_display()
            )
        except Exception:
            return obj.statut if obj.statut else '-'


# ==============================================================================
# ADMIN : INHUMATION
# ==============================================================================
@admin.register(Inhumation)
class InhumationAdmin(admin.ModelAdmin):
    list_display = ('defunt', 'concession', 'date_inhumation', 'profondeur')
    list_filter = ('date_inhumation',)
    search_fields = ('defunt__nom', 'defunt__prenom', 'concession__numero_contrat')
    readonly_fields = ('date_enregistrement',)


# ==============================================================================
# ADMIN : PARAMÈTRES DU CIMETIÈRE (CORRIGÉ DÉFINITIVEMENT)
# ==============================================================================
@admin.register(ParametreCimetiere)
class ParametreCimetiereAdmin(admin.ModelAdmin):
    list_display = ('nom', 'superficie_totale', 'longueur_standard_caveau', 'largeur_standard_caveau')
    
    # CORRECTION : Nous n'incluons QUE les champs qui existent réellement dans le modèle.
    # Le champ 'perimetre' a été supprimé car il n'existe pas dans models.py (seul 'coordonnees_centre' existe).
    fieldsets = (
        ('Informations générales', {
            'fields': ('nom', 'adresse', 'coordonnees_centre')
        }),
        ('Dimensions', {
            'fields': ('superficie_totale', 'longueur_standard_caveau', 'largeur_standard_caveau', 'largeur_allee')
        }),
    )


# ==============================================================================
# ADMIN : DEMANDE D'EXHUMATION
# ==============================================================================
@admin.register(DemandeExhumation)
class DemandeExhumationAdmin(admin.ModelAdmin):
    list_display = ('id', 'nom_demandeur', 'inhumation', 'statut_badge', 'date_demande')
    list_filter = ('statut', 'date_demande')
    search_fields = ('nom_demandeur', 'inhumation__defunt__nom')
    readonly_fields = ('date_demande', 'date_validation', 'date_realisation', 'date_modification')
    
    fieldsets = (
        ('Informations de la demande', {'fields': ('inhumation', 'demandeur', 'statut')}),
        ('Demandeur', {'fields': ('nom_demandeur', 'lien_parente', 'telephone_demandeur')}),
        ('Détails', {'fields': ('motif', 'destination')}),
        ('Traitement', {'fields': ('date_demande', 'date_validation', 'date_realisation', 'valide_par', 'motif_refus')}),
        ('Notes', {'fields': ('notes',), 'classes': ('collapse',)}),
    )
    
    actions = ['valider_demandes', 'refuser_demandes']
    
    @admin.display(description='Statut')
    def statut_badge(self, obj):
        try:
            couleurs = {
                'EN_ATTENTE': '#f39c12',
                'VALIDEE': '#27ae60',
                'REFUSEE': '#e74c3c',
                'REALISEE': '#3498db',
            }
            couleur = couleurs.get(obj.statut, '#95a5a6')
            return format_html(
                '<span style="background: {}; color: white; padding: 4px 12px; '
                'border-radius: 12px; font-size: 11px; font-weight: bold;">{}</span>',
                couleur,
                obj.get_statut_display()
            )
        except Exception:
            return obj.statut if obj.statut else '-'
    
    @admin.action(description='✓ Valider les demandes sélectionnées')
    def valider_demandes(self, request, queryset):
        count = 0
        for demande in queryset.filter(statut='EN_ATTENTE'):
            try:
                demande.valider(request.user)
                count += 1
            except Exception as e:
                messages.error(request, f'Erreur #{demande.id}: {str(e)}')
        if count > 0:
            messages.success(request, f'{count} demande(s) validée(s).')
    
    @admin.action(description='✗ Refuser les demandes sélectionnées')
    def refuser_demandes(self, request, queryset):
        count = 0
        for demande in queryset.filter(statut='EN_ATTENTE'):
            try:
                demande.refuser('Refusé par l\'administration', request.user)
                count += 1
            except Exception as e:
                messages.error(request, f'Erreur #{demande.id}: {str(e)}')
        if count > 0:
            messages.success(request, f'{count} demande(s) refusée(s).')