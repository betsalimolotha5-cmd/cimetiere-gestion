"""
Administration des demandes de réservation (Workflow de validation).
Conforme au CDC : validation → concession → facture → PDF → email → notifications automatiques.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from django.shortcuts import get_object_or_404, redirect
from datetime import timedelta
from decimal import Decimal
from .models import DemandeReservation


def _notifier_client_validation(reservation, concession, facture):
    """
    Envoie une notification automatique au client quand sa demande est validée.
    Conforme au CDC : email de confirmation avec détails de la concession et facture.
    """
    from apps.notifications.services import NotificationService
    from apps.notifications.models import EmailLog
    
    client = reservation.client
    sujet = f"✓ Votre demande de réservation a été validée - {concession.numero_contrat}"
    
    contenu_html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; background-color: #f5f5f5; padding: 20px;">
        <div style="max-width: 600px; margin: auto; background: white; padding: 30px; border-radius: 10px;">
            <h2 style="color: #27ae60;">✓ Votre demande a été validée</h2>
            <p>Bonjour <strong>{client.get_full_name() or client.email}</strong>,</p>
            
            <div style="background: #d4edda; border-left: 4px solid #27ae60; padding: 15px; margin: 20px 0;">
                <p style="margin: 5px 0;"><strong>📋 Votre demande a été approuvée par l'administration.</strong></p>
            </div>
            
            <h3 style="color: #2c3e50;">📍 Détails de votre concession</h3>
            <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 15px 0;">
                <p style="margin: 5px 0;"><strong>N° de contrat :</strong> {concession.numero_contrat}</p>
                <p style="margin: 5px 0;"><strong>Caveau :</strong> {concession.caveau.code}</p>
                <p style="margin: 5px 0;"><strong>Zone :</strong> {concession.caveau.zone.nom if concession.caveau.zone else 'Non définie'}</p>
                <p style="margin: 5px 0;"><strong>Défunt :</strong> {reservation.defunt_prenom} {reservation.defunt_nom}</p>
                <p style="margin: 5px 0;"><strong>Durée :</strong> {concession.duree_annees} ans</p>
                <p style="margin: 5px 0;"><strong>Date de début :</strong> {concession.date_debut.strftime('%d/%m/%Y')}</p>
                <p style="margin: 5px 0;"><strong>Date de fin :</strong> {concession.date_fin.strftime('%d/%m/%Y') if concession.date_fin else 'Non définie'}</p>
            </div>
            
            <h3 style="color: #2c3e50;">💰 Votre facture</h3>
            <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 15px 0;">
                <p style="margin: 5px 0;"><strong>N° de facture :</strong> {facture.numero_facture}</p>
                <p style="margin: 5px 0;"><strong>Montant total :</strong> {facture.montant_total:,.0f} FCFA</p>
                <p style="margin: 5px 0;"><strong>Date d'émission :</strong> {facture.date_emission.strftime('%d/%m/%Y')}</p>
                <p style="margin: 5px 0;"><strong>Date d'échéance :</strong> {facture.date_echeance.strftime('%d/%m/%Y')}</p>
            </div>
            
            <p>Votre facture PDF est en pièce jointe de cet email. Vous pouvez également la consulter et procéder au paiement depuis votre espace client.</p>
            
            <p style="margin-top: 30px;">
                <a href="http://127.0.0.1:8000/portal/mes-factures/" 
                   style="background: #27ae60; color: white; padding: 12px 24px; text-decoration: none; 
                          border-radius: 5px; display: inline-block;">
                    💳 Voir mes factures
                </a>
            </p>
            
            <p style="margin-top: 30px; color: #7f8c8d; font-size: 12px;">
                Pour toute question, n'hésitez pas à nous contacter.
            </p>
        </div>
    </body>
    </html>
    """
    
    # Envoyer l'email avec la facture en pièce jointe
    succes = NotificationService.envoyer_email(
        destinataire=client.email,
        sujet=sujet,
        contenu_html=contenu_html,
        type_email=EmailLog.TypeEmail.AUTRE,
        utilisateur=client
    )
    
    # Créer une notification interne
    NotificationService.creer_notification(
        utilisateur=client,
        titre='Demande de réservation validée',
        message=f'Votre demande pour le caveau {concession.caveau.code} a été validée. '
                f'Concession {concession.numero_contrat} créée.',
        url_lien='/portal/mes-factures/'
    )
    
    return succes


def _notifier_client_refus(reservation, motif):
    """
    Envoie une notification automatique au client quand sa demande est refusée.
    """
    from apps.notifications.services import NotificationService
    from apps.notifications.models import EmailLog
    
    client = reservation.client
    sujet = f"✗ Votre demande de réservation a été refusée - Caveau {reservation.caveau.code}"
    
    contenu_html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; background-color: #f5f5f5; padding: 20px;">
        <div style="max-width: 600px; margin: auto; background: white; padding: 30px; border-radius: 10px;">
            <h2 style="color: #e74c3c;">✗ Votre demande a été refusée</h2>
            <p>Bonjour <strong>{client.get_full_name() or client.email}</strong>,</p>
            
            <div style="background: #f8d7da; border-left: 4px solid #e74c3c; padding: 15px; margin: 20px 0;">
                <p style="margin: 5px 0;"><strong>Votre demande de réservation pour le caveau {reservation.caveau.code} a été refusée.</strong></p>
            </div>
            
            <h3 style="color: #2c3e50;">Détails de la demande</h3>
            <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 15px 0;">
                <p style="margin: 5px 0;"><strong>Caveau :</strong> {reservation.caveau.code}</p>
                <p style="margin: 5px 0;"><strong>Zone :</strong> {reservation.caveau.zone.nom if reservation.caveau.zone else 'Non définie'}</p>
                <p style="margin: 5px 0;"><strong>Défunt :</strong> {reservation.defunt_prenom} {reservation.defunt_nom}</p>
                <p style="margin: 5px 0;"><strong>Date de la demande :</strong> {reservation.date_demande.strftime('%d/%m/%Y') if reservation.date_demande else '-'}</p>
            </div>
            
            <h3 style="color: #2c3e50;">Motif du refus</h3>
            <div style="background: #fff3cd; padding: 15px; border-radius: 8px; margin: 15px 0;">
                <p>{motif}</p>
            </div>
            
            <p>Si vous avez des questions, n'hésitez pas à contacter l'administration.</p>
            
            <p style="margin-top: 30px;">
                <a href="http://127.0.0.1:8000/portal/" 
                   style="background: #667eea; color: white; padding: 12px 24px; text-decoration: none; 
                          border-radius: 5px; display: inline-block;">
                    🗺️ Voir la carte
                </a>
            </p>
            
            <p style="margin-top: 30px; color: #7f8c8d; font-size: 12px;">
                Pour toute question, n'hésitez pas à nous contacter.
            </p>
        </div>
    </body>
    </html>
    """
    
    succes = NotificationService.envoyer_email(
        destinataire=client.email,
        sujet=sujet,
        contenu_html=contenu_html,
        type_email=EmailLog.TypeEmail.AUTRE,
        utilisateur=client
    )
    
    NotificationService.creer_notification(
        utilisateur=client,
        titre='Demande de réservation refusée',
        message=f'Votre demande pour le caveau {reservation.caveau.code} a été refusée.',
        url_lien='/portal/mes-reservations/'
    )
    
    return succes


def _traiter_validation(reservation, user):
    """
    Logique commune de validation :
    1. Valider la demande
    2. Réserver le caveau
    3. Créer le défunt
    4. Créer la concession
    5. Créer la facture
    6. Générer le PDF
    7. Envoyer la facture par email
    8. Envoyer notification de validation au client
    
    Retourne un dict avec les résultats et messages.
    """
    from apps.core.models import Concession, Defunt
    from apps.billing.models import Facture
    from apps.billing.pdf_generator import generer_facture_pdf, envoyer_facture_par_email
    
    resultats = {
        'concession': None,
        'facture': None,
        'pdf_ok': False,
        'email_ok': False,
        'notification_ok': False,
        'erreurs': [],
    }
    
    # 1. Valider la demande
    reservation.valider(user)
    
    # 2. Réserver le caveau
    caveau = reservation.caveau
    caveau.statut = 'RESERVE'
    caveau.save()
    
    # 3. Créer le défunt s'il n'existe pas
    defunt, _ = Defunt.objects.get_or_create(
        nom=reservation.defunt_nom,
        prenom=reservation.defunt_prenom,
        defaults={'date_deces': reservation.date_deces}
    )
    
    # 4. Créer la concession
    numero_contrat = f"CONC-{timezone.now().year}-{reservation.id:05d}"
    duree_annees = 30
    montant_total = caveau.prix_concession or Decimal('50000')
    
    concession = Concession.objects.create(
        numero_contrat=numero_contrat,
        concessionnaire=reservation.client,
        caveau=caveau,
        defunt=defunt,
        type_concession=Concession.TypeConcession.TEMPORAIRE,
        duree_annees=duree_annees,
        date_debut=timezone.now().date(),
        montant_total=montant_total,
        montant_paye=Decimal('0'),
        statut=Concession.StatutConcession.ACTIVE,
        cree_par=user,
        notes=f"Créée automatiquement suite à la réservation {reservation.id}"
    )
    resultats['concession'] = concession
    
    # 5. Créer la facture
    numero_facture = f"FACT-{timezone.now().year}-{reservation.id:05d}"
    facture = Facture.objects.create(
        numero_facture=numero_facture,
        concession=concession,
        client=reservation.client,
        montant_ht=montant_total,
        taux_tva=Decimal('0'),
        date_emission=timezone.now().date(),
        date_echeance=timezone.now().date() + timedelta(days=30),
        statut=Facture.StatutFacture.EMISE,
        description=f"Concession funéraire - Caveau {caveau.code} - {defunt.prenom} {defunt.nom}",
        cree_par=user
    )
    resultats['facture'] = facture
    
    # 6. Générer le PDF
    try:
        pdf_path = generer_facture_pdf(facture)
        facture.fichier_pdf = pdf_path
        facture.save(update_fields=['fichier_pdf'])
        resultats['pdf_ok'] = True
    except Exception as e:
        resultats['erreurs'].append(f'PDF: {str(e)}')
    
    # 7. Envoyer la facture par email
    try:
        if envoyer_facture_par_email(facture):
            facture.email_envoye = True
            facture.date_envoi_email = timezone.now()
            facture.save(update_fields=['email_envoye', 'date_envoi_email'])
            resultats['email_ok'] = True
    except Exception as e:
        resultats['erreurs'].append(f'Email facture: {str(e)}')
    
    # 8. Envoyer notification de validation au client
    try:
        if _notifier_client_validation(reservation, concession, facture):
            resultats['notification_ok'] = True
    except Exception as e:
        resultats['erreurs'].append(f'Notification: {str(e)}')
    
    return resultats


@admin.action(description='✓ Valider les demandes sélectionnées (concession + facture + PDF + email + notification)')
def valider_reservations(modeladmin, request, queryset):
    """Action admin pour valider plusieurs demandes en masse (conforme au CDC)."""
    count = 0
    erreurs_count = 0
    
    for reservation in queryset.filter(statut=DemandeReservation.Statut.EN_ATTENTE):
        try:
            resultats = _traiter_validation(reservation, request.user)
            count += 1
            
            if resultats['erreurs']:
                erreurs_count += 1
                messages.warning(
                    request,
                    f'Demande #{reservation.id} validée mais avec erreurs: {", ".join(resultats["erreurs"])}'
                )
        except Exception as e:
            erreurs_count += 1
            messages.error(
                request,
                f'Erreur lors de la validation de la demande #{reservation.id}: {str(e)}'
            )
    
    if count > 0:
        messages.success(
            request,
            f'✓ {count} demande(s) validée(s). Concession + Facture + PDF + Notification créés automatiquement.'
        )
    if count == 0:
        messages.warning(request, 'Aucune demande en attente sélectionnée.')


@admin.action(description='✗ Refuser les demandes sélectionnées (avec notification)')
def refuser_reservations(modeladmin, request, queryset):
    """Action admin pour refuser plusieurs demandes avec notification au client."""
    count = 0
    motif = 'Refusé par l\'administration'
    
    for reservation in queryset.filter(statut=DemandeReservation.Statut.EN_ATTENTE):
        try:
            reservation.refuser(request.user, motif=motif)
            _notifier_client_refus(reservation, motif)
            count += 1
        except Exception as e:
            messages.error(request, f'Erreur #{reservation.id}: {str(e)}')
    
    if count > 0:
        messages.success(request, f'{count} demande(s) refusée(s). Clients notifiés par email.')
    else:
        messages.warning(request, 'Aucune demande en attente sélectionnée.')


@admin.register(DemandeReservation)
class DemandeReservationAdmin(admin.ModelAdmin):
    """Administration des demandes de réservation avec workflow conforme au CDC."""

    list_display = (
        'id',
        'caveau_code',
        'zone',
        'defunt_complet',
        'client_info',
        'statut_badge',
        'date_demande',
        'date_traitement',
        'traite_par',
        'actions_detail',
    )

    list_filter = (
        'statut',
        'date_demande',
        'date_traitement',
        'caveau__zone',
    )

    search_fields = (
        'caveau__code',
        'defunt_nom',
        'defunt_prenom',
        'client__email',
        'client__first_name',
        'client__last_name',
        'telephone_contact',
    )

    readonly_fields = (
        'client',
        'caveau',
        'defunt_nom',
        'defunt_prenom',
        'date_deces',
        'lien_parente',
        'telephone_contact',
        'statut',
        'date_demande',
        'date_traitement',
        'traite_par',
        'motif_refus',
        'date_creation',
        'date_modification',
    )

    fieldsets = (
        ('📋 Informations de la demande', {
            'fields': ('client', 'caveau', 'statut')
        }),
        ('👤 Informations sur le défunt', {
            'fields': ('defunt_nom', 'defunt_prenom', 'date_deces', 'lien_parente')
        }),
        ('📞 Coordonnées du demandeur', {
            'fields': ('telephone_contact',)
        }),
        ('⚙️ Traitement', {
            'fields': ('date_demande', 'date_traitement', 'traite_par', 'motif_refus')
        }),
        ('📅 Métadonnées', {
            'fields': ('date_creation', 'date_modification'),
            'classes': ('collapse',)
        }),
    )

    date_hierarchy = 'date_demande'
    ordering = ('-date_demande',)
    list_per_page = 25
    actions = [valider_reservations, refuser_reservations]

    @admin.display(description='Caveau', ordering='caveau__code')
    def caveau_code(self, obj):
        url = reverse('admin:core_caveau_change', args=[obj.caveau.id])
        return format_html('<a href="{}"><strong>{}</strong></a>', url, obj.caveau.code)

    @admin.display(description='Zone', ordering='caveau__zone__nom')
    def zone(self, obj):
        return obj.caveau.zone.nom if obj.caveau.zone else '-'

    @admin.display(description='Défunt', ordering='defunt_nom')
    def defunt_complet(self, obj):
        return f"{obj.defunt_prenom} {obj.defunt_nom}"

    @admin.display(description='Client', ordering='client__email')
    def client_info(self, obj):
        nom = obj.client.get_full_name() or obj.client.email
        return format_html(
            '{}<br><small style="color: #7f8c8d;">{}</small>',
            nom,
            obj.telephone_contact
        )

    @admin.display(description='Statut', ordering='statut')
    def statut_badge(self, obj):
        couleurs = {
            'EN_ATTENTE': ('#f39c12', '⏳ En attente'),
            'VALIDEE': ('#e74c3c', '✓ Validée'),
            'REFUSEE': ('#c0392b', '✗ Refusée'),
            'ANNULEE': ('#95a5a6', '⊘ Annulée'),
        }
        couleur, label = couleurs.get(obj.statut, ('#95a5a6', obj.statut))
        return format_html(
            '<span style="background: {}; color: white; padding: 4px 12px; '
            'border-radius: 12px; font-size: 11px; font-weight: bold;">{}</span>',
            couleur,
            label
        )

    @admin.display(description='Actions')
    def actions_detail(self, obj):
        if obj.statut == DemandeReservation.Statut.EN_ATTENTE:
            return format_html(
                '<a href="{}" style="background: #27ae60; color: white; padding: 4px 10px; '
                'border-radius: 4px; text-decoration: none; font-size: 11px; margin-right: 5px;">'
                '✓ Valider</a>',
                reverse('admin:portal_demandereservation_valider', args=[obj.id])
            )
        return '-'

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:reservation_id>/valider/',
                self.admin_site.admin_view(self.valider_view),
                name='portal_demandereservation_valider'
            ),
            path(
                '<int:reservation_id>/refuser/',
                self.admin_site.admin_view(self.refuser_view),
                name='portal_demandereservation_refuser'
            ),
        ]
        return custom_urls + urls

    def valider_view(self, request, reservation_id):
        """Vue pour valider une demande avec workflow complet conforme au CDC."""
        reservation = get_object_or_404(DemandeReservation, id=reservation_id)
        
        if reservation.statut != DemandeReservation.Statut.EN_ATTENTE:
            messages.error(request, 'Cette demande n\'est plus en attente.')
            return redirect(reverse('admin:portal_demandereservation_changelist'))
        
        try:
            resultats = _traiter_validation(reservation, request.user)
            
            if resultats['pdf_ok'] and resultats['email_ok'] and resultats['notification_ok']:
                messages.success(
                    request,
                    f'✓ Demande validée. Concession {resultats["concession"].numero_contrat} créée, '
                    f'facture {resultats["facture"].numero_facture} générée, envoyée par email et '
                    f'notification envoyée à {reservation.client.email}.'
                )
            elif resultats['pdf_ok'] and resultats['email_ok']:
                messages.warning(
                    request,
                    f'✓ Demande validée et facture envoyée, mais notification échouée.'
                )
            elif resultats['pdf_ok']:
                messages.warning(
                    request,
                    f'✓ Demande validée et facture générée, mais envoi email/notification échoué.'
                )
            else:
                messages.warning(
                    request,
                    f'✓ Demande validée et concession créée, mais erreurs: '
                    f'{", ".join(resultats["erreurs"])}'
                )
        except Exception as e:
            messages.error(request, f'Erreur lors de la validation: {str(e)}')
        
        return redirect(reverse('admin:portal_demandereservation_changelist'))

    def refuser_view(self, request, reservation_id):
        """Vue pour refuser une demande avec notification au client."""
        reservation = get_object_or_404(DemandeReservation, id=reservation_id)
        
        if reservation.statut != DemandeReservation.Statut.EN_ATTENTE:
            messages.error(request, 'Cette demande n\'est plus en attente.')
            return redirect(reverse('admin:portal_demandereservation_changelist'))
        
        try:
            motif = request.POST.get('motif', 'Refusé par l\'administration')
            reservation.refuser(request.user, motif=motif)
            
            # Notifier le client
            try:
                _notifier_client_refus(reservation, motif)
                messages.warning(
                    request,
                    f'La demande pour le caveau {reservation.caveau.code} a été refusée. '
                    f'Client notifié par email.'
                )
            except Exception as e:
                messages.warning(
                    request,
                    f'La demande a été refusée mais la notification au client a échoué: {str(e)}'
                )
        except Exception as e:
            messages.error(request, f'Erreur lors du refus: {str(e)}')
        
        return redirect(reverse('admin:portal_demandereservation_changelist'))