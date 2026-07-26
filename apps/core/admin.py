"""
Administration Django pour l'application core (cimetière).
CORRIGÉ : Ajout de dimensions explicites (width/height) pour forcer l'affichage des cartes.
AJOUT : Téléchargement PDF du contrat de concession, du PV d'inhumation, de l'autorisation et du PV d'exhumation.
"""
from django.contrib import admin, messages
from django.contrib.gis.db import models as gis_models
from django.contrib.gis.forms import OSMWidget
from django import forms
from django.utils.html import format_html
from .models import (
    Zone, Caveau, Defunt, Concession, Inhumation,
    ParametreCimetiere, DemandeExhumation
)

# ==============================================================================
# CONFIGURATION PAR DÉFAUT POUR LA CARTE (Pointe-Noire)
# ==============================================================================
CIMETIERE_CENTRE_LAT = -4.7692
CIMETIERE_CENTRE_LNG = 11.8644
CIMETIERE_ZOOM_DEFAULT = 16


# ==============================================================================
# ADMIN : CAVEAU
# ==============================================================================
@admin.register(Caveau)
class CaveauAdmin(admin.ModelAdmin):
    list_display = ('code', 'zone', 'statut_badge', 'type_caveau', 'prix_concession', 'position_display')
    list_filter = ('statut', 'type_caveau', 'zone')
    search_fields = ('code', 'zone__nom')
    
    formfield_overrides = {
        gis_models.PointField: {
            'widget': OSMWidget(attrs={
                'default_lat': CIMETIERE_CENTRE_LAT,
                'default_lon': CIMETIERE_CENTRE_LNG,
                'default_zoom': CIMETIERE_ZOOM_DEFAULT,
                'map_width': '100%',
                'map_height': '400px',
            })
        },
    }
    
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
    
    formfield_overrides = {
        gis_models.PointField: {
            'widget': OSMWidget(attrs={
                'default_lat': CIMETIERE_CENTRE_LAT,
                'default_lon': CIMETIERE_CENTRE_LNG,
                'default_zoom': CIMETIERE_ZOOM_DEFAULT,
                'map_width': '100%',
                'map_height': '400px',
            })
        },
    }
    
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
    
    fieldsets = (
        ('Informations personnelles', {
            'fields': ('nom', 'prenom', 'date_naissance', 'sexe', 'nationalite')
        }),
        ('Décès', {
            'fields': ('date_deces', 'lieu_deces', 'numero_acte_deces')
        }),
        ('Famille', {
            'fields': ('nom_pere', 'nom_mere')
        }),
        ('Documents', {
            'fields': ('photo', 'numero_identite'),
            'description': '📸 Photo du défunt et numéro d\'identité'
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )
    
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
    list_display = (
        'numero_contrat', 
        'concessionnaire', 
        'caveau', 
        'type_concession', 
        'statut_badge', 
        'date_debut', 
        'date_fin',
        'telecharger_contrat_pdf_link',
    )
    list_filter = ('type_concession', 'statut', 'date_debut')
    search_fields = ('numero_contrat', 'concessionnaire__email', 'caveau__code')
    readonly_fields = ('date_signature', 'date_creation', 'date_modification', 'telecharger_contrat_pdf_button')
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('numero_contrat', 'concessionnaire', 'caveau', 'defunt', 'type_concession', 'duree_annees')
        }),
        ('Dates', {
            'fields': ('date_debut', 'date_fin', 'date_signature', 'statut')
        }),
        ('Finances', {
            'fields': ('montant_total', 'montant_paye')
        }),
        ('Document PDF du contrat', {
            'fields': ('telecharger_contrat_pdf_button',),
            'description': '💡 Cliquez sur le bouton ci-dessous pour télécharger le contrat officiel au format PDF'
        }),
        ('Documents numérisés', {
            'fields': ('document_contrat',),
            'description': '📎 Téléversez ici une copie scannée du contrat signé (optionnel)',
            'classes': ('collapse',),
        }),
        ('Métadonnées', {
            'fields': ('cree_par', 'notes', 'date_creation', 'date_modification'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['telecharger_contrats_pdf_action']
    
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
    
    @admin.display(description='Contrat PDF')
    def telecharger_contrat_pdf_link(self, obj):
        url = f'/core/concession/{obj.id}/contrat-pdf/'
        return format_html(
            '<a href="{}" target="_blank" class="button" style="padding: 5px 10px; background: #6c3483; color: white; text-decoration: none; border-radius: 4px; font-size: 11px; font-weight: bold;">'
            '<i class="fas fa-file-pdf"></i> 📄 Contrat</a>',
            url
        )
    
    @admin.display(description='Télécharger le contrat')
    def telecharger_contrat_pdf_button(self, obj):
        if obj.pk:
            url = f'/core/concession/{obj.id}/contrat-pdf/'
            return format_html(
                '<a href="{}" target="_blank" class="button" style="padding: 12px 24px; background: #6c3483; color: white; text-decoration: none; border-radius: 6px; font-size: 14px; font-weight: bold; display: inline-block;">'
                '<i class="fas fa-download"></i> Télécharger le contrat en PDF</a>',
                url
            )
        return format_html('<p style="color: #999;">Sauvegardez d\'abord la concession pour pouvoir télécharger le PDF.</p>')
    
    @admin.action(description='📄 Télécharger les contrats PDF sélectionnés')
    def telecharger_contrats_pdf_action(self, request, queryset):
        if queryset.count() == 1:
            concession = queryset.first()
            url = f'/core/concession/{concession.id}/contrat-pdf/'
            messages.success(request, f'Contrat PDF prêt pour : {concession.numero_contrat}')
        else:
            links = []
            for concession in queryset:
                url = f'/core/concession/{concession.id}/contrat-pdf/'
                links.append(f'<a href="{url}" target="_blank">{concession.numero_contrat}</a>')
            messages.success(request, f'Contrats PDF prêts pour : {", ".join(links)}')


# ==============================================================================
# ADMIN : INHUMATION
# ==============================================================================
@admin.register(Inhumation)
class InhumationAdmin(admin.ModelAdmin):
    list_display = (
        'defunt', 
        'concession', 
        'date_inhumation', 
        'profondeur',
        'telecharger_pv_pdf_link',
    )
    list_filter = ('date_inhumation',)
    search_fields = ('defunt__nom', 'defunt__prenom', 'concession__numero_contrat')
    readonly_fields = ('date_enregistrement', 'telecharger_pv_pdf_button')
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('defunt', 'concession', 'date_inhumation', 'profondeur', 'numero_place_dans_caveau')
        }),
        ('Document PDF du PV', {
            'fields': ('telecharger_pv_pdf_button',),
            'description': '💡 Cliquez sur le bouton ci-dessous pour télécharger le PV d\'inhumation officiel au format PDF'
        }),
        ('Métadonnées', {
            'fields': ('enregistre_par', 'notes', 'date_enregistrement'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['telecharger_pv_pdf_action']
    
    @admin.display(description='PV PDF')
    def telecharger_pv_pdf_link(self, obj):
        if obj.pk:
            url = f'/core/inhumation/{obj.id}/pv-pdf/'
            return format_html(
                '<a href="{}" target="_blank" class="button" style="padding: 5px 10px; background: #e74c3c; color: white; text-decoration: none; border-radius: 4px; font-size: 11px; font-weight: bold;">'
                '<i class="fas fa-file-pdf"></i> 📄 PV</a>',
                url
            )
        return "-"
    
    @admin.display(description='Télécharger le PV')
    def telecharger_pv_pdf_button(self, obj):
        if obj.pk:
            url = f'/core/inhumation/{obj.id}/pv-pdf/'
            return format_html(
                '<a href="{}" target="_blank" class="button" style="padding: 12px 24px; background: #e74c3c; color: white; text-decoration: none; border-radius: 6px; font-size: 14px; font-weight: bold; display: inline-block;">'
                '<i class="fas fa-download"></i> Télécharger le PV d\'inhumation en PDF</a>',
                url
            )
        return format_html('<p style="color: #999;">Sauvegardez d\'abord l\'inhumation pour pouvoir télécharger le PV.</p>')
    
    @admin.action(description='📄 Télécharger les PV d\'inhumation PDF sélectionnés')
    def telecharger_pv_pdf_action(self, request, queryset):
        if queryset.count() == 1:
            inhumation = queryset.first()
            url = f'/core/inhumation/{inhumation.id}/pv-pdf/'
            messages.success(request, f'PV PDF prêt pour : {inhumation.defunt}')
        else:
            links = []
            for inh in queryset:
                url = f'/core/inhumation/{inh.id}/pv-pdf/'
                links.append(f'<a href="{url}" target="_blank">{inh.defunt}</a>')
            messages.success(request, f'PVs PDF prêts pour : {", ".join(links)}')


# ==============================================================================
# ADMIN : PARAMÈTRES DU CIMETIÈRE
# ==============================================================================
@admin.register(ParametreCimetiere)
class ParametreCimetiereAdmin(admin.ModelAdmin):
    list_display = ('nom', 'superficie_totale', 'longueur_standard_caveau', 'largeur_standard_caveau')
    
    formfield_overrides = {
        gis_models.PointField: {
            'widget': OSMWidget(attrs={
                'default_lat': CIMETIERE_CENTRE_LAT,
                'default_lon': CIMETIERE_CENTRE_LNG,
                'default_zoom': CIMETIERE_ZOOM_DEFAULT,
                'map_width': '100%',
                'map_height': '400px',
            })
        },
    }
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('nom', 'adresse', 'coordonnees_centre')
        }),
        ('Dimensions', {
            'fields': ('superficie_totale', 'longueur_standard_caveau', 'largeur_standard_caveau', 'largeur_allee'),
            'description': '💡 La délimitation du cimetière sera automatiquement calculée et affichée sur la carte en fonction de la superficie totale et du point central.'
        }),
    )
    
    class Media:
        js = ('admin/js/cimetiere_perimetre.js',)


# ==============================================================================
# ADMIN : DEMANDE D'EXHUMATION (AVEC PDF DE L'AUTORISATION ET DU PV)
# ==============================================================================
@admin.register(DemandeExhumation)
class DemandeExhumationAdmin(admin.ModelAdmin):
    list_display = (
        'id', 
        'nom_demandeur', 
        'inhumation', 
        'statut_badge', 
        'date_demande',
        'telecharger_autorisation_pdf_link',
        'telecharger_pv_pdf_link',  # ⭐ NOUVEAU : Bouton PV dans la liste
    )
    list_filter = ('statut', 'date_demande')
    search_fields = ('nom_demandeur', 'inhumation__defunt__nom')
    readonly_fields = (
        'date_demande', 
        'date_validation', 
        'date_realisation', 
        'date_modification',
        'telecharger_autorisation_pdf_button',
        'telecharger_pv_pdf_button'  # ⭐ NOUVEAU
    )
    
    fieldsets = (
        ('Informations de la demande', {
            'fields': ('inhumation', 'demandeur', 'statut')
        }),
        ('Demandeur', {
            'fields': ('nom_demandeur', 'lien_parente', 'telephone_demandeur')
        }),
        ('Détails', {
            'fields': ('motif', 'destination')
        }),
        ('Documents PDF générés', {
            'fields': ('telecharger_autorisation_pdf_button', 'telecharger_pv_pdf_button'),
            'description': '💡 Cliquez sur les boutons ci-dessous pour télécharger les documents officiels au format PDF'
        }),
        ('Documents officiels numérisés', {
            'fields': ('autorisation_mairie', 'proces_verbal'),
            'description': '📎 Téléversez ici les documents officiels scannés (optionnel)',
            'classes': ('collapse',),
        }),
        ('Traitement', {
            'fields': ('date_demande', 'date_validation', 'date_realisation', 'valide_par', 'motif_refus')
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )
    
    actions = [
        'valider_demandes', 
        'refuser_demandes', 
        'telecharger_autorisations_pdf_action',
        'telecharger_pvs_pdf_action'  # ⭐ NOUVEAU
    ]
    
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
    
    # Bouton Autorisation PDF dans la liste
    @admin.display(description='Autorisation PDF')
    def telecharger_autorisation_pdf_link(self, obj):
        if obj.pk:
            url = f'/core/demande-exhumation/{obj.id}/autorisation-pdf/'
            return format_html(
                '<a href="{}" target="_blank" class="button" style="padding: 5px 10px; background: #2980b9; color: white; text-decoration: none; border-radius: 4px; font-size: 11px; font-weight: bold;">'
                '<i class="fas fa-file-pdf"></i> 📄 Auto.</a>',
                url
            )
        return "-"
    
    # Gros bouton Autorisation PDF dans le formulaire de détail
    @admin.display(description='Télécharger l\'autorisation')
    def telecharger_autorisation_pdf_button(self, obj):
        if obj.pk:
            url = f'/core/demande-exhumation/{obj.id}/autorisation-pdf/'
            return format_html(
                '<a href="{}" target="_blank" class="button" style="padding: 10px 20px; background: #2980b9; color: white; text-decoration: none; border-radius: 6px; font-size: 13px; font-weight: bold; display: inline-block;">'
                '<i class="fas fa-download"></i> Télécharger l\'autorisation en PDF</a>',
                url
            )
        return format_html('<p style="color: #999;">Sauvegardez d\'abord la demande pour pouvoir télécharger l\'autorisation.</p>')
    
    # ⭐ NOUVEAU : Bouton PV PDF dans la liste
    @admin.display(description='PV PDF')
    def telecharger_pv_pdf_link(self, obj):
        if obj.pk:
            url = f'/core/demande-exhumation/{obj.id}/pv-exhumation-pdf/'
            return format_html(
                '<a href="{}" target="_blank" class="button" style="padding: 5px 10px; background: #8e44ad; color: white; text-decoration: none; border-radius: 4px; font-size: 11px; font-weight: bold;">'
                '<i class="fas fa-file-pdf"></i> 📄 PV</a>',
                url
            )
        return "-"
    
    # ⭐ NOUVEAU : Gros bouton PV PDF dans le formulaire de détail
    @admin.display(description='Télécharger le PV')
    def telecharger_pv_pdf_button(self, obj):
        if obj.pk:
            url = f'/core/demande-exhumation/{obj.id}/pv-exhumation-pdf/'
            return format_html(
                '<a href="{}" target="_blank" class="button" style="padding: 10px 20px; background: #8e44ad; color: white; text-decoration: none; border-radius: 6px; font-size: 13px; font-weight: bold; display: inline-block;">'
                '<i class="fas fa-download"></i> Télécharger le PV d\'exhumation en PDF</a>',
                url
            )
        return format_html('<p style="color: #999;">Sauvegardez d\'abord la demande pour pouvoir télécharger le PV.</p>')
    
    # Action de masse pour télécharger plusieurs autorisations
    @admin.action(description='📄 Télécharger les autorisations d\'exhumation PDF sélectionnées')
    def telecharger_autorisations_pdf_action(self, request, queryset):
        if queryset.count() == 1:
            demande = queryset.first()
            url = f'/core/demande-exhumation/{demande.id}/autorisation-pdf/'
            messages.success(request, f'Autorisation PDF prête pour la demande #{demande.id}')
        else:
            links = []
            for demande in queryset:
                url = f'/core/demande-exhumation/{demande.id}/autorisation-pdf/'
                links.append(f'<a href="{url}" target="_blank">Demande #{demande.id}</a>')
            messages.success(request, f'Autorisations PDF prêtes pour : {", ".join(links)}')

    # ⭐ NOUVEAU : Action de masse pour télécharger plusieurs PVs
    @admin.action(description='📄 Télécharger les PV d\'exhumation PDF sélectionnés')
    def telecharger_pvs_pdf_action(self, request, queryset):
        if queryset.count() == 1:
            demande = queryset.first()
            url = f'/core/demande-exhumation/{demande.id}/pv-exhumation-pdf/'
            messages.success(request, f'PV PDF prêt pour la demande #{demande.id}')
        else:
            links = []
            for demande in queryset:
                url = f'/core/demande-exhumation/{demande.id}/pv-exhumation-pdf/'
                links.append(f'<a href="{url}" target="_blank">Demande #{demande.id}</a>')
            messages.success(request, f'PVs PDF prêts pour : {", ".join(links)}')
    
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