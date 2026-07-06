"""
Administration Django pour la facturation et les paiements.
Conforme au CDC : validation paiement → notification client automatique.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.contrib import messages
from .models import Facture, Paiement, TransactionFinanciere


@admin.register(Facture)
class FactureAdmin(admin.ModelAdmin):
    list_display = (
        'numero_facture',
        'concession',
        'client',
        'montant_total_display',
        'montant_paye_display',
        'statut_display',
        'date_emission',
        'date_echeance',
        'pdf_link',
    )
    list_filter = ('statut', 'date_emission', 'date_echeance')
    search_fields = ('numero_facture', 'concession__numero_contrat', 'client__email')
    readonly_fields = ('date_emission', 'date_creation', 'date_modification', 'cree_par')
    date_hierarchy = 'date_emission'
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('numero_facture', 'concession', 'client', 'description')
        }),
        ('Montants', {
            'fields': ('montant_ht', 'taux_tva', 'montant_tva', 'montant_total', 'montant_paye', 'montant_restant', 'statut')
        }),
        ('Dates', {
            'fields': ('date_emission', 'date_echeance', 'date_paiement_complet')
        }),
        ('Document PDF', {
            'fields': ('fichier_pdf', 'email_envoye', 'date_envoi_email')
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Métadonnées', {
            'fields': ('date_creation', 'date_modification', 'cree_par'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['generer_pdf', 'marquer_comme_payee']
    
    def montant_total_display(self, obj):
        montant = float(obj.montant_total) if obj.montant_total else 0
        montant_formate = f"{montant:,.0f}".replace(',', ' ')
        return f"{montant_formate} FCFA"
    montant_total_display.short_description = 'Montant total'
    montant_total_display.admin_order_field = 'montant_total'
    
    def montant_paye_display(self, obj):
        montant = float(obj.montant_paye) if obj.montant_paye else 0
        total = float(obj.montant_total) if obj.montant_total else 0
        
        if total == 0:
            color = 'gray'
        elif montant >= total:
            color = 'green'
        elif montant > 0:
            color = 'orange'
        else:
            color = 'red'
        
        montant_formate = f"{montant:,.0f}".replace(',', ' ')
        html = f'<span style="color: {color}; font-weight: bold;">{montant_formate} FCFA</span>'
        return format_html(html)
    montant_paye_display.short_description = 'Montant payé'
    montant_paye_display.admin_order_field = 'montant_paye'
    
    def statut_display(self, obj):
        colors = {
            'BROUILLON': 'gray',
            'EMISE': 'orange',
            'PARTIELLEMENT_PAYEE': 'blue',
            'PAYEE': 'green',
            'ANNULEE': 'red',
        }
        color = colors.get(obj.statut, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_statut_display()
        )
    statut_display.short_description = 'Statut'
    statut_display.admin_order_field = 'statut'
    
    def pdf_link(self, obj):
        """Lien vers le PDF si existant."""
        if obj.fichier_pdf:
            return format_html(
                '<a href="{}" target="_blank">📄 Voir PDF</a>',
                obj.fichier_pdf.url
            )
        return format_html('<span style="color: gray;">—</span>')
    pdf_link.short_description = 'PDF'
    
    @admin.action(description='📄 Générer les PDF des factures sélectionnées')
    def generer_pdf(self, request, queryset):
        from .pdf_generator import generer_facture_pdf
        generated = 0
        for facture in queryset:
            try:
                pdf_path = generer_facture_pdf(facture)
                facture.fichier_pdf = pdf_path
                facture.save(update_fields=['fichier_pdf'])
                generated += 1
            except Exception as e:
                self.message_user(request, f'Erreur pour {facture.numero_facture}: {str(e)}', level='error')
        self.message_user(request, f'{generated} PDF généré(s).')
    
    @admin.action(description='✓ Marquer comme payée')
    def marquer_comme_payee(self, request, queryset):
        updated = 0
        for facture in queryset:
            facture.statut = 'PAYEE'
            facture.montant_paye = facture.montant_total
            facture.date_paiement_complet = timezone.now().date()
            facture.save()
            updated += 1
        self.message_user(request, f'{updated} facture(s) marquée(s) comme payée(s).')


@admin.register(Paiement)
class PaiementAdmin(admin.ModelAdmin):
    list_display = (
        'numero_transaction',
        'facture',
        'client',
        'montant_display',
        'mode_paiement',
        'statut_display',
        'date_paiement',
    )
    list_filter = ('mode_paiement', 'statut', 'date_paiement')
    search_fields = ('numero_transaction', 'facture__numero_facture', 'client__email')
    readonly_fields = ('date_paiement', 'date_creation', 'date_modification')
    date_hierarchy = 'date_paiement'
    
    fieldsets = (
        ('Informations du paiement', {
            'fields': ('facture', 'client', 'montant', 'mode_paiement', 'statut')
        }),
        ('Détails de transaction', {
            'fields': ('reference_transaction', 'numero_telephone', 'date_paiement')
        }),
        ('Validation', {
            'fields': ('date_validation', 'valide_par')
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['valider_paiements', 'refuser_paiements']
    
    def montant_display(self, obj):
        montant = float(obj.montant) if obj.montant else 0
        montant_formate = f"{montant:,.0f}".replace(',', ' ')
        return f"{montant_formate} FCFA"
    montant_display.short_description = 'Montant'
    montant_display.admin_order_field = 'montant'
    
    def statut_display(self, obj):
        colors = {
            'EN_ATTENTE': 'orange',
            'VALIDE': 'green',
            'REFUSE': 'red',
            'REMBOURSE': 'gray',
        }
        color = colors.get(obj.statut, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_statut_display()
        )
    statut_display.short_description = 'Statut'
    statut_display.admin_order_field = 'statut'
    
    @admin.action(description='✓ Valider les paiements sélectionnés (avec notification client)')
    def valider_paiements(self, request, queryset):
        """Valide les paiements et notifie automatiquement les clients."""
        count = 0
        for paiement in queryset.filter(statut=Paiement.StatutPaiement.EN_ATTENTE):
            try:
                paiement.valider(request.user)
                count += 1
                
                # Notifier le client
                try:
                    from apps.notifications.services import NotificationService
                    NotificationService.creer_notification(
                        utilisateur=paiement.client,
                        titre='✓ Paiement validé',
                        message=f'Votre paiement de {paiement.montant:,.0f} FCFA pour la facture '
                                f'{paiement.facture.numero_facture} a été validé. Merci !',
                        url_lien=f'/portal/facture/{paiement.facture.id}/'
                    )
                except Exception as e:
                    # Ne pas bloquer si la notification échoue
                    pass
            except Exception as e:
                messages.error(request, f'Erreur #{paiement.id}: {str(e)}')
        
        if count > 0:
            messages.success(request, f'{count} paiement(s) validé(s). Clients notifiés.')
        else:
            messages.warning(request, 'Aucun paiement en attente sélectionné.')
    
    @admin.action(description='✗ Refuser les paiements sélectionnés')
    def refuser_paiements(self, request, queryset):
        """Refuse les paiements et notifie les clients."""
        count = 0
        motif = 'Refusé par l\'administration'
        
        for paiement in queryset.filter(statut=Paiement.StatutPaiement.EN_ATTENTE):
            try:
                paiement.refuser(motif, request.user)
                count += 1
                
                # Notifier le client
                try:
                    from apps.notifications.services import NotificationService
                    NotificationService.creer_notification(
                        utilisateur=paiement.client,
                        titre='✗ Paiement refusé',
                        message=f'Votre paiement de {paiement.montant:,.0f} FCFA pour la facture '
                                f'{paiement.facture.numero_facture} a été refusé. '
                                f'Motif : {motif}',
                        url_lien=f'/portal/facture/{paiement.facture.id}/'
                    )
                except Exception as e:
                    pass
            except Exception as e:
                messages.error(request, f'Erreur #{paiement.id}: {str(e)}')
        
        if count > 0:
            messages.warning(request, f'{count} paiement(s) refusé(s). Clients notifiés.')
        else:
            messages.warning(request, 'Aucun paiement en attente sélectionné.')


@admin.register(TransactionFinanciere)
class TransactionFinanciereAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'type_transaction',
        'montant_display',
        'sens',
        'reference',
        'date_transaction',
    )
    list_filter = ('type_transaction', 'sens', 'date_transaction')
    search_fields = ('description', 'reference')
    readonly_fields = ('date_transaction', 'date_creation')
    date_hierarchy = 'date_transaction'
    
    fieldsets = (
        ('Informations de la transaction', {
            'fields': ('type_transaction', 'montant', 'sens')
        }),
        ('Liens', {
            'fields': ('facture', 'paiement', 'client')
        }),
        ('Détails', {
            'fields': ('description', 'date_transaction', 'enregistre_par')
        }),
    )
    
    def montant_display(self, obj):
        montant = float(obj.montant) if obj.montant else 0
        montant_formate = f"{montant:,.0f}".replace(',', ' ')
        return f"{montant_formate} FCFA"
    montant_display.short_description = 'Montant'
    montant_display.admin_order_field = 'montant'