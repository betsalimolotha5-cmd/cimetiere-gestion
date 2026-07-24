"""
Administration Django pour l'application core (cimetière).
Conforme au CDC : gestion des zones, caveaux, concessions et validation stricte du périmètre GPS.
Configuration optimisée pour Pointe-Noire, République du Congo.
"""
from django.contrib import admin, messages
from django.contrib.gis.geos import Polygon, Point
from django.contrib.gis.db import models as gis_models
from django.contrib.gis.forms import OSMWidget
from django.core.exceptions import ValidationError
from django import forms
from django.utils.html import format_html
from .models import (
    Zone, Caveau, Defunt, Concession, Inhumation,
    ParametreCimetiere, DemandeExhumation
)

# ==============================================================================
# ️ CONFIGURATION DU PÉRIMÈTRE DU CIMETIÈRE (POINTE-NOIRE)
# ==============================================================================
# Coordonnées réelles de Pointe-Noire, République du Congo
# Format GeoDjango : (Longitude, Latitude) -> C'est l'INVERSE de Leaflet/Google Maps !
# Périmètre réaliste pour un cimetière de ~5000m² (100m x 50m)

CIMETIERE_PERIMETRE = Polygon((
    (11.8639, -4.7690),  # Coin Nord-Ouest (Lng, Lat)
    (11.8649, -4.7690),  # Coin Nord-Est
    (11.8649, -4.7694),  # Coin Sud-Est
    (11.8639, -4.7694),  # Coin Sud-Ouest
    (11.8639, -4.7690),  # Fermeture du polygone (doit être identique au 1er point)
), srid=4326)

# Centre du cimetière pour le widget de carte
CIMETIERE_CENTRE_LAT = -4.7692
CIMETIERE_CENTRE_LNG = 11.8644
CIMETIERE_ZOOM_DEFAULT = 17


# ==============================================================================
# ADMIN : CAVEAU (Avec validation STRICTE du périmètre)
# ==============================================================================
class CaveauAdminForm(forms.ModelForm):
    """Formulaire avec validation stricte : le caveau DOIT être dans le périmètre."""
    
    class Meta:
        model = Caveau
        fields = '__all__'
        widgets = {
            'position_gps': OSMWidget(attrs={
                'default_lat': CIMETIERE_CENTRE_LAT,
                'default_lon': CIMETIERE_CENTRE_LNG,
                'default_zoom': CIMETIERE_ZOOM_DEFAULT,
            }),
        }

    def clean_position_gps(self):
        """Validation stricte : le caveau doit être dans le périmètre du cimetière."""
        position = self.cleaned_data.get('position_gps')
        
        if position:
            if not CIMETIERE_PERIMETRE.contains(position):
                raise ValidationError(
                    "❌ Ce caveau est en dehors du périmètre officiel du cimetière de Pointe-Noire. "
                    "Veuillez placer le caveau à l'intérieur des limites définies."
                )
        return position

    def clean(self):
        """Validation globale du formulaire."""
        cleaned_data = super().clean()
        position = cleaned_data.get('position_gps')
        
        if position:
            if not CIMETIERE_PERIMETRE.contains(position):
                raise ValidationError(
                    "❌ Ce caveau est en dehors du périmètre officiel du cimetière. "
                    "Veuillez corriger les coordonnées GPS pour qu'elles soient à l'intérieur des limites."
                )
        return cleaned_data


@admin.register(Caveau)
class CaveauAdmin(admin.ModelAdmin):
    form = CaveauAdminForm  # Utilisation du formulaire avec validation stricte
    list_display = ('code', 'zone', 'statut_badge', 'type_caveau', 'prix_concession', 'position_display')
    list_filter = ('statut', 'type_caveau', 'zone')
    search_fields = ('code', 'zone__nom')
    
    # Configuration du widget de carte pour tous les champs PointField
    formfield_overrides = {
        gis_models.PointField: {
            'widget': OSMWidget(attrs={
                'default_lat': CIMETIERE_CENTRE_LAT,
                'default_lon': CIMETIERE_CENTRE_LNG,
                'default_zoom': CIMETIERE_ZOOM_DEFAULT,
            })
        },
        gis_models.PolygonField: {
            'widget': OSMWidget(attrs={
                'default_lat': CIMETIERE_CENTRE_LAT,
                'default_lon': CIMETIERE_CENTRE_LNG,
                'default_zoom': CIMETIERE_ZOOM_DEFAULT,
            })
        },
    }
    
    @admin.display(description='Statut')
    def statut_badge(self, obj):
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
    
    @admin.display(description='Position GPS')
    def position_display(self, obj):
        if obj.position_gps:
            return f"{obj.position_gps.y:.6f}, {obj.position_gps.x:.6f}"
        return '-'


# ==============================================================================
# ADMIN : ZONE
# ==============================================================================
@admin.register(Zone)
class ZoneAdmin(admin.ModelAdmin):
    list_display = ('code', 'nom', 'type_zone', 'est_exploitable', 'superficie', 'capacite_theorique')
    list_filter = ('type_zone', 'est_exploitable')
    search_fields = ('code', 'nom')
    
    formfield_overrides = {
        gis_models.PolygonField: {
            'widget': OSMWidget(attrs={
                'default_lat': CIMETIERE_CENTRE_LAT,
                'default_lon': CIMETIERE_CENTRE_LNG,
                'default_zoom': CIMETIERE_ZOOM_DEFAULT,
            })
        },
    }
    
    @admin.display(description='Capacité théorique')
    def capacite_theorique(self, obj):
        return obj.calculer_capacite_theorique()


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
        age = obj.age_au_deces()
        return f"{age} ans" if age else '-'


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
# ADMIN : PARAMÈTRES DU CIMETIÈRE (Avec valeurs par défaut)
# ==============================================================================
class ParametreCimetiereAdminForm(forms.ModelForm):
    """Formulaire avec valeurs par défaut pour Pointe-Noire."""
    
    class Meta:
        model = ParametreCimetiere
        fields = '__all__'
        widgets = {
            'coordonnees_centre': OSMWidget(attrs={
                'default_lat': CIMETIERE_CENTRE_LAT,
                'default_lon': CIMETIERE_CENTRE_LNG,
                'default_zoom': CIMETIERE_ZOOM_DEFAULT,
            }),
            'perimetre': OSMWidget(attrs={
                'default_lat': CIMETIERE_CENTRE_LAT,
                'default_lon': CIMETIERE_CENTRE_LNG,
                'default_zoom': CIMETIERE_ZOOM_DEFAULT,
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Valeurs par défaut si le formulaire est vide (création)
        if not self.instance.pk:
            if not self.instance.superficie_totale:
                self.instance.superficie_totale = 5000  # 5000m² par défaut


@admin.register(ParametreCimetiere)
class ParametreCimetiereAdmin(admin.ModelAdmin):
    form = ParametreCimetiereAdminForm
    list_display = ('nom', 'superficie_totale', 'longueur_standard_caveau', 'largeur_standard_caveau')
    
    formfield_overrides = {
        gis_models.PointField: {
            'widget': OSMWidget(attrs={
                'default_lat': CIMETIERE_CENTRE_LAT,
                'default_lon': CIMETIERE_CENTRE_LNG,
                'default_zoom': CIMETIERE_ZOOM_DEFAULT,
            })
        },
        gis_models.PolygonField: {
            'widget': OSMWidget(attrs={
                'default_lat': CIMETIERE_CENTRE_LAT,
                'default_lon': CIMETIERE_CENTRE_LNG,
                'default_zoom': CIMETIERE_ZOOM_DEFAULT,
            })
        },
    }
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('nom', 'adresse', 'coordonnees_centre')
        }),
        ('Périmètre du cimetière', {
            'fields': ('perimetre',),
            'description': 'Définissez les limites exactes du cimetière sur la carte. Superficie recommandée : 5000m²'
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
    list_display = ('id', 'nom_demandeur', 'inhumation', 'statut_badge', 'date_demande', 'destination', 'lien_autorisation', 'lien_proces_verbal')
    list_filter = ('statut', 'destination', 'date_demande')
    search_fields = ('nom_demandeur', 'inhumation__defunt__nom', 'inhumation__defunt__prenom')
    readonly_fields = ('date_demande', 'date_validation', 'date_realisation', 'date_modification', 'lien_autorisation_display', 'lien_proces_verbal_display')
    
    fieldsets = (
        ('Informations de la demande', {'fields': ('inhumation', 'demandeur', 'statut')}),
        ('Demandeur', {'fields': ('nom_demandeur', 'lien_parente', 'telephone_demandeur')}),
        ('Détails', {'fields': ('motif', 'destination')}),
        ('Documents PDF', {'fields': ('lien_autorisation_display', 'lien_proces_verbal_display'), 'description': 'Les documents PDF générés apparaissent ici après génération'}),
        ('Fichiers bruts', {'fields': ('autorisation_mairie', 'proces_verbal'), 'classes': ('collapse',)}),
        ('Traitement', {'fields': ('date_demande', 'date_validation', 'date_realisation', 'valide_par', 'motif_refus')}),
        ('Notes', {'fields': ('notes',), 'classes': ('collapse',)}),
    )
    
    actions = ['valider_demandes', 'refuser_demandes', 'generer_autorisation_pdf', 'generer_proces_verbal_pdf']
    
    @admin.display(description='Statut')
    def statut_badge(self, obj):
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
    
    @admin.display(description='Autorisation PDF')
    def lien_autorisation(self, obj):
        if obj.autorisation_mairie:
            return format_html('<a href="{}" target="_blank" style="background: #3498db; color: white; padding: 4px 10px; border-radius: 4px; text-decoration: none; font-size: 11px;">📄 Voir</a>', obj.autorisation_mairie.url)
        return format_html('<span style="color: #95a5a6;">— Non généré —</span>')

    @admin.display(description='Procès-verbal PDF')
    def lien_proces_verbal(self, obj):
        if obj.proces_verbal:
            return format_html('<a href="{}" target="_blank" style="background: #9b59b6; color: white; padding: 4px 10px; border-radius: 4px; text-decoration: none; font-size: 11px;">📄 Voir</a>', obj.proces_verbal.url)
        return format_html('<span style="color: #95a5a6;">— Non généré —</span>')

    @admin.display(description='Autorisation PDF (Détail)')
    def lien_autorisation_display(self, obj):
        if obj.autorisation_mairie:
            return format_html('<a href="{}" target="_blank" style="background: #3498db; color: white; padding: 8px 16px; border-radius: 6px; text-decoration: none; font-weight: bold; display: inline-block;">📄 Télécharger l\'autorisation PDF</a>', obj.autorisation_mairie.url)
        return format_html('<span style="color: #95a5a6; font-style: italic;">Aucune autorisation générée.</span>')

    @admin.display(description='Procès-verbal PDF (Détail)')
    def lien_proces_verbal_display(self, obj):
        if obj.proces_verbal:
            return format_html('<a href="{}" target="_blank" style="background: #9b59b6; color: white; padding: 8px 16px; border-radius: 6px; text-decoration: none; font-weight: bold; display: inline-block;">📄 Télécharger le procès-verbal PDF</a>', obj.proces_verbal.url)
        return format_html('<span style="color: #95a5a6; font-style: italic;">Aucun procès-verbal généré.</span>')
    
    @admin.action(description='✓ Valider les demandes sélectionnées')
    def valider_demandes(self, request, queryset):
        count = 0
        for demande in queryset.filter(statut=DemandeExhumation.StatutDemande.EN_ATTENTE):
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
        for demande in queryset.filter(statut=DemandeExhumation.StatutDemande.EN_ATTENTE):
            try:
                demande.refuser('Refusé par l\'administration', request.user)
                count += 1
            except Exception as e:
                messages.error(request, f'Erreur #{demande.id}: {str(e)}')
        if count > 0:
            messages.success(request, f'{count} demande(s) refusée(s).')
    
    @admin.action(description=' Générer autorisation PDF')
    def generer_autorisation_pdf(self, request, queryset):
        from apps.billing.pdf_generator import generer_autorisation_exhumation
        count = 0
        for demande in queryset.filter(statut=DemandeExhumation.StatutDemande.VALIDEE):
            try:
                pdf_path = generer_autorisation_exhumation(demande)
                demande.autorisation_mairie = pdf_path
                demande.save(update_fields=['autorisation_mairie'])
                count += 1
            except Exception as e:
                messages.error(request, f'Erreur #{demande.id}: {str(e)}')
        if count > 0:
            messages.success(request, f'{count} autorisation(s) générée(s).')

    @admin.action(description=' Générer procès-verbal PDF')
    def generer_proces_verbal_pdf(self, request, queryset):
        from apps.billing.pdf_generator import generer_proces_verbal_exhumation
        count = 0
        for demande in queryset.filter(statut=DemandeExhumation.StatutDemande.VALIDEE):
            try:
                pdf_path = generer_proces_verbal_exhumation(demande)
                demande.proces_verbal = pdf_path
                demande.save(update_fields=['proces_verbal'])
                count += 1
            except Exception as e:
                messages.error(request, f'Erreur #{demande.id}: {str(e)}')
        if count > 0:
            messages.success(request, f'{count} procès-verbal(aux) généré(s).')