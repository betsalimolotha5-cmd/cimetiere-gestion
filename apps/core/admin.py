"""
Administration Django pour l'application core (cimetière).
"""
from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin
from django.utils.html import format_html
from django.contrib import messages
from .models import (
    Zone, Caveau, Defunt, Concession, Inhumation,
    ParametreCimetiere, DemandeExhumation
)


@admin.register(Zone)
class ZoneAdmin(admin.ModelAdmin):
    list_display = ('code', 'nom', 'type_zone', 'est_exploitable', 'superficie', 'capacite_theorique')
    list_filter = ('type_zone', 'est_exploitable')
    search_fields = ('code', 'nom')
    
    def capacite_theorique(self, obj):
        return obj.calculer_capacite_theorique()
    capacite_theorique.short_description = 'Capacité théorique'


@admin.register(Caveau)
class CaveauAdmin(admin.ModelAdmin):
    list_display = ('code', 'zone', 'statut_badge', 'type_caveau', 'prix_concession', 'position')
    list_filter = ('statut', 'type_caveau', 'zone')
    search_fields = ('code', 'zone__nom')
    
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
    statut_badge.short_description = 'Statut'
    
    def position(self, obj):
        if obj.position_gps:
            return f"{obj.position_gps.y:.6f}, {obj.position_gps.x:.6f}"
        return '-'
    position.short_description = 'Position GPS'


@admin.register(Defunt)
class DefuntAdmin(admin.ModelAdmin):
    list_display = ('nom', 'prenom', 'date_deces', 'sexe', 'age_au_deces')
    list_filter = ('sexe', 'date_deces')
    search_fields = ('nom', 'prenom', 'numero_identite')
    
    def age_au_deces(self, obj):
        age = obj.age_au_deces()
        return f"{age} ans" if age else '-'
    age_au_deces.short_description = 'Âge au décès'


@admin.register(Concession)
class ConcessionAdmin(admin.ModelAdmin):
    list_display = ('numero_contrat', 'concessionnaire', 'caveau', 'type_concession', 'statut_badge', 'date_debut', 'date_fin')
    list_filter = ('type_concession', 'statut', 'date_debut')
    search_fields = ('numero_contrat', 'concessionnaire__email', 'caveau__code')
    readonly_fields = ('date_signature', 'date_creation', 'date_modification')
    
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
    statut_badge.short_description = 'Statut'


@admin.register(Inhumation)
class InhumationAdmin(admin.ModelAdmin):
    list_display = ('defunt', 'concession', 'date_inhumation', 'profondeur')
    list_filter = ('date_inhumation',)
    search_fields = ('defunt__nom', 'defunt__prenom', 'concession__numero_contrat')
    readonly_fields = ('date_enregistrement',)


@admin.register(ParametreCimetiere)
class ParametreCimetiereAdmin(admin.ModelAdmin):
    list_display = ('nom', 'superficie_totale', 'longueur_standard_caveau', 'largeur_standard_caveau')
    fieldsets = (
        ('Informations générales', {
            'fields': ('nom', 'adresse', 'coordonnees_centre')
        }),
        ('Dimensions', {
            'fields': ('superficie_totale', 'longueur_standard_caveau', 'largeur_standard_caveau', 'largeur_allee')
        }),
    )


@admin.register(DemandeExhumation)
class DemandeExhumationAdmin(admin.ModelAdmin):
    list_display = ('id', 'nom_demandeur', 'inhumation', 'statut_badge', 'date_demande', 'destination', 'lien_autorisation', 'lien_proces_verbal')
    list_filter = ('statut', 'destination', 'date_demande')
    search_fields = ('nom_demandeur', 'inhumation__defunt__nom', 'inhumation__defunt__prenom')
    readonly_fields = ('date_demande', 'date_validation', 'date_realisation', 'date_modification', 'lien_autorisation_display', 'lien_proces_verbal_display')
    
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
        ('Documents PDF', {
            'fields': ('lien_autorisation_display', 'lien_proces_verbal_display'),
            'description': 'Les documents PDF générés apparaissent ici après génération'
        }),
        ('Fichiers bruts', {
            'fields': ('autorisation_mairie', 'proces_verbal'),
            'classes': ('collapse',)
        }),
        ('Traitement', {
            'fields': ('date_demande', 'date_validation', 'date_realisation', 'valide_par', 'motif_refus')
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['valider_demandes', 'refuser_demandes', 'generer_autorisation_pdf', 'generer_proces_verbal_pdf']
    
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
    statut_badge.short_description = 'Statut'
    
    def lien_autorisation(self, obj):
        """Lien vers l'autorisation PDF dans la liste."""
        if obj.autorisation_mairie:
            return format_html(
                '<a href="{}" target="_blank" style="background: #3498db; color: white; padding: 4px 10px; border-radius: 4px; text-decoration: none; font-size: 11px;">📄 Autorisation</a>',
                obj.autorisation_mairie.url
            )
        return format_html('<span style="color: #95a5a6;">— Non généré —</span>')
    lien_autorisation.short_description = 'Autorisation PDF'
    
    def lien_proces_verbal(self, obj):
        """Lien vers le procès-verbal PDF dans la liste."""
        if obj.proces_verbal:
            return format_html(
                '<a href="{}" target="_blank" style="background: #9b59b6; color: white; padding: 4px 10px; border-radius: 4px; text-decoration: none; font-size: 11px;">📄 Procès-verbal</a>',
                obj.proces_verbal.url
            )
        return format_html('<span style="color: #95a5a6;">— Non généré —</span>')
    lien_proces_verbal.short_description = 'Procès-verbal PDF'
    
    def lien_autorisation_display(self, obj):
        """Affichage dans la fiche détail."""
        if obj.autorisation_mairie:
            return format_html(
                '<a href="{}" target="_blank" style="background: #3498db; color: white; padding: 8px 16px; border-radius: 6px; text-decoration: none; font-weight: bold; display: inline-block;">📄 Télécharger l\'autorisation PDF</a>',
                obj.autorisation_mairie.url
            )
        return format_html('<span style="color: #95a5a6; font-style: italic;">Aucune autorisation générée. Utilisez l\'action "Générer autorisation PDF" ci-dessus.</span>')
    lien_autorisation_display.short_description = 'Autorisation PDF'
    
    def lien_proces_verbal_display(self, obj):
        """Affichage dans la fiche détail."""
        if obj.proces_verbal:
            return format_html(
                '<a href="{}" target="_blank" style="background: #9b59b6; color: white; padding: 8px 16px; border-radius: 6px; text-decoration: none; font-weight: bold; display: inline-block;">📄 Télécharger le procès-verbal PDF</a>',
                obj.proces_verbal.url
            )
        return format_html('<span style="color: #95a5a6; font-style: italic;">Aucun procès-verbal généré. Utilisez l\'action "Générer procès-verbal PDF" ci-dessus.</span>')
    lien_proces_verbal_display.short_description = 'Procès-verbal PDF'
    
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
        else:
            messages.warning(request, 'Aucune demande en attente sélectionnée.')
    
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
        else:
            messages.warning(request, 'Aucune demande en attente sélectionnée.')
    
    @admin.action(description='📄 Générer autorisation PDF')
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
            messages.success(request, f'{count} autorisation(s) générée(s). Rechargez la page pour voir les liens.')
        else:
            messages.warning(request, 'Aucune demande validée sélectionnée.')
    
    @admin.action(description='📄 Générer procès-verbal PDF')
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
            messages.success(request, f'{count} procès-verbal(aux) généré(s). Rechargez la page pour voir les liens.')
        else:
            messages.warning(request, 'Aucune demande validée sélectionnée.')