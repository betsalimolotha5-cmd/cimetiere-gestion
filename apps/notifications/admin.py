"""
Administration Django pour les notifications et emails.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count, Q
from django.utils import timezone
from .models import EmailLog, Notification
from django.db.models import Q
from apps.billing.models import Facture
from apps.core.models import Concession


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    """Administration des logs d'emails."""
    
    list_display = (
        'reference_short',
        'type_email_display',
        'destinataire',
        'utilisateur',
        'sujet_short',
        'statut_display',
        'date_envoi_tente',
        'date_envoi_reussi',
    )
    
    list_filter = (
        'statut',
        'type_email',
        'date_envoi_tente',
        'date_envoi_reussi',
    )
    
    search_fields = (
        'destinataire',
        'sujet',
        'utilisateur__email',
        'utilisateur__first_name',
        'utilisateur__last_name',
        'contenu_html',
        'message_erreur',
    )
    
    readonly_fields = (
        'reference',
        'date_creation',
        'date_envoi_tente',
        'date_envoi_reussi',
    )
    
    date_hierarchy = 'date_envoi_tente'
    
    fieldsets = (
        ('Identification', {
            'fields': ('reference', 'destinataire', 'utilisateur')
        }),
        ('Contenu', {
            'fields': ('type_email', 'sujet', 'contenu_html', 'contenu_texte')
        }),
        ('Pièces jointes', {
            'fields': ('pieces_jointes',),
            'classes': ('collapse',)
        }),
        ('Statut', {
            'fields': ('statut', 'message_erreur')
        }),
        ('Dates', {
            'fields': ('date_envoi_tente', 'date_envoi_reussi', 'date_creation')
        }),
    )
    
    actions = [
        'marquer_comme_envoye',
        'marquer_comme_echec',
    ]
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('utilisateur')
    
    @admin.display(description='Référence')
    def reference_short(self, obj):
        return str(obj.reference)[:8]
    
    @admin.display(description='Type')
    def type_email_display(self, obj):
        colors = {
            'MFA_CODE': 'blue',
            'BIENVENUE': 'green',
            'CONFIRMATION_RESERVATION': 'purple',
            'FACTURE': 'orange',
            'RAPPEL_PAIEMENT': 'red',
            'ALERTE_CONCESSION': 'darkorange',
            'AUTRE': 'gray',
        }
        color = colors.get(obj.type_email, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_type_email_display()
        )
    
    @admin.display(description='Sujet')
    def sujet_short(self, obj):
        if len(obj.sujet) > 50:
            return f"{obj.sujet[:50]}..."
        return obj.sujet
    
    @admin.display(description='Statut')
    def statut_display(self, obj):
        colors = {
            'ENVOYE': 'green',
            'ECHEC': 'red',
            'EN_ATTENTE': 'orange',
        }
        color = colors.get(obj.statut, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_statut_display()
        )
    
    @admin.action(description='Marquer comme envoyé')
    def marquer_comme_envoye(self, request, queryset):
        updated = queryset.filter(statut=EmailLog.StatutEmail.EN_ATTENTE).update(
            statut=EmailLog.StatutEmail.ENVOYE,
            date_envoi_reussi=timezone.now()
        )
        self.message_user(request, f'{updated} email(s) marqué(s) comme envoyé(s).')
    
    @admin.action(description='Marquer comme échec')
    def marquer_comme_echec(self, request, queryset):
        updated = queryset.filter(statut=EmailLog.StatutEmail.EN_ATTENTE).update(
            statut=EmailLog.StatutEmail.ECHEC,
            message_erreur='Marqué manuellement comme échec'
        )
        self.message_user(request, f'{updated} email(s) marqué(s) comme échec.')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """Administration des notifications internes."""
    
    list_display = (
        'titre_short',
        'utilisateur',
        'type_notification_display',
        'priorite_display',
        'lue_display',
        'date_creation',
        'date_lecture',
    )
    
    list_filter = (
        'type_notification',
        'priorite',
        'lue',
        'date_creation',
        'utilisateur',
    )
    
    search_fields = (
        'titre',
        'message',
        'utilisateur__email',
        'utilisateur__first_name',
        'utilisateur__last_name',
    )
    
    readonly_fields = (
        'date_creation',
        'date_lecture',
    )
    
    date_hierarchy = 'date_creation'
    
    fieldsets = (
        ('Destinataire', {
            'fields': ('utilisateur',)
        }),
        ('Contenu', {
            'fields': ('type_notification', 'priorite', 'titre', 'message', 'url_lien')
        }),
        ('Statut', {
            'fields': ('lue', 'date_creation', 'date_lecture')
        }),
    )
    
    actions = [
        'marquer_comme_lue',
        'marquer_comme_non_lue',
        'supprimer_notifications_anciennes',
    ]
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('utilisateur')
    
    @admin.display(description='Titre')
    def titre_short(self, obj):
        if len(obj.titre) > 50:
            return f"{obj.titre[:50]}..."
        return obj.titre
    
    @admin.display(description='Type')
    def type_notification_display(self, obj):
        colors = {
            'INFO': 'blue',
            'SUCCESS': 'green',
            'WARNING': 'orange',
            'ERROR': 'red',
        }
        color = colors.get(obj.type_notification, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_type_notification_display()
        )
    
    @admin.display(description='Priorité')
    def priorite_display(self, obj):
        colors = {
            'BASSE': 'gray',
            'NORMALE': 'blue',
            'HAUTE': 'orange',
            'URGENTE': 'red',
        }
        color = colors.get(obj.priorite, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_priorite_display()
        )
    
    @admin.display(description='Lue', boolean=True)
    def lue_display(self, obj):
        return obj.lue
    
    @admin.action(description='Marquer comme lue')
    def marquer_comme_lue(self, request, queryset):
        updated = queryset.filter(lue=False).update(
            lue=True,
            date_lecture=timezone.now()
        )
        self.message_user(request, f'{updated} notification(s) marquée(s) comme lue(s).')
    
    @admin.action(description='Marquer comme non lue')
    def marquer_comme_non_lue(self, request, queryset):
        updated = queryset.update(
            lue=False,
            date_lecture=None
        )
        self.message_user(request, f'{updated} notification(s) marquée(s) comme non lue(s).')
    
    @admin.action(description='Supprimer les notifications de plus de 30 jours')
    def supprimer_notifications_anciennes(self, request, queryset):
        from datetime import timedelta
        date_limite = timezone.now() - timedelta(days=30)
        
        anciennes = queryset.filter(date_creation__lt=date_limite, lue=True)
        count = anciennes.count()
        anciennes.delete()
        
        self.message_user(request, f'{count} notification(s) ancienne(s) supprimée(s).')


class NotificationsDashboardAdmin(admin.ModelAdmin):
    """Tableau de bord des notifications (vue personnalisée)."""
    
    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path(
                'dashboard/',
                self.admin_site.admin_view(self.dashboard_view),
                name='notifications_dashboard'
            ),
        ]
        return custom_urls + urls
    
    def dashboard_view(self, request):
        from django.shortcuts import render
        from datetime import timedelta
        
        aujourd = timezone.now()
        il_y_a_7j = aujourd - timedelta(days=7)
        il_y_a_30j = aujourd - timedelta(days=30)
        
        # Statistiques emails
        total_emails = EmailLog.objects.count()
        emails_envoyes = EmailLog.objects.filter(statut=EmailLog.StatutEmail.ENVOYE).count()
        emails_echec = EmailLog.objects.filter(statut=EmailLog.StatutEmail.ECHEC).count()
        emails_attente = EmailLog.objects.filter(statut=EmailLog.StatutEmail.EN_ATTENTE).count()
        emails_7j = EmailLog.objects.filter(date_envoi_tente__gte=il_y_a_7j).count()
        
        # Statistiques notifications
        total_notifications = Notification.objects.count()
        notifications_non_lues = Notification.objects.filter(lue=False).count()
        notifications_urgentes = Notification.objects.filter(priorite=Notification.Priorite.URGENTE, lue=False).count()
        notifications_7j = Notification.objects.filter(date_creation__gte=il_y_a_7j).count()
        
        # Statistiques factures
        factures_en_retard = Facture.objects.filter(
            Q(statut=Facture.StatutFacture.EMISE) | Q(statut=Facture.StatutFacture.PARTIELLEMENT_PAYEE),
            date_echeance__lt=aujourd.date()
        ).count()
        
        factures_impayees = Facture.objects.filter(
            Q(statut=Facture.StatutFacture.EMISE) | Q(statut=Facture.StatutFacture.PARTIELLEMENT_PAYEE)
        ).count()
        
        # Statistiques concessions
        concessions_expirent_bientot = Concession.objects.filter(
            type_concession=Concession.TypeConcession.TEMPORAIRE,
            statut=Concession.StatutConcession.ACTIVE,
            date_fin__isnull=False,
            date_fin__gte=aujourd.date(),
            date_fin__lte=aujourd.date() + timedelta(days=30)
        ).count()
        
        # Derniers emails envoyés
        derniers_emails = EmailLog.objects.all()[:10]
        
        # Dernières notifications
        dernieres_notifications = Notification.objects.filter(lue=False)[:10]
        
        context = {
            'title': 'Tableau de bord des notifications',
            'total_emails': total_emails,
            'emails_envoyes': emails_envoyes,
            'emails_echec': emails_echec,
            'emails_attente': emails_attente,
            'emails_7j': emails_7j,
            'total_notifications': total_notifications,
            'notifications_non_lues': notifications_non_lues,
            'notifications_urgentes': notifications_urgentes,
            'notifications_7j': notifications_7j,
            'factures_en_retard': factures_en_retard,
            'factures_impayees': factures_impayees,
            'concessions_expirent_bientot': concessions_expirent_bientot,
            'derniers_emails': derniers_emails,
            'dernieres_notifications': dernieres_notifications,
        }
        
        return render(request, 'admin/notifications/dashboard.html', context)


# Ajouter un lien vers le dashboard dans l'admin
from django.contrib.admin import AdminSite

original_get_urls = AdminSite.get_urls

def patched_get_urls(self):
    from django.urls import path
    urls = original_get_urls(self)
    dashboard_urls = [
        path('notifications-dashboard/', self.admin_view(self.notifications_dashboard), name='notifications_dashboard'),
    ]
    return dashboard_urls + urls

AdminSite.get_urls = patched_get_urls

def notifications_dashboard(self, request):
    from django.shortcuts import render
    from datetime import timedelta
    
    aujourd = timezone.now()
    il_y_a_7j = aujourd - timedelta(days=7)
    
    context = {
        'title': '📊 Tableau de bord des notifications',
        'total_emails': EmailLog.objects.count(),
        'emails_envoyes': EmailLog.objects.filter(statut='ENVOYE').count(),
        'emails_echec': EmailLog.objects.filter(statut='ECHEC').count(),
        'emails_attente': EmailLog.objects.filter(statut='EN_ATTENTE').count(),
        'emails_7j': EmailLog.objects.filter(date_envoi_tente__gte=il_y_a_7j).count(),
        'total_notifications': Notification.objects.count(),
        'notifications_non_lues': Notification.objects.filter(lue=False).count(),
        'notifications_urgentes': Notification.objects.filter(priorite='URGENTE', lue=False).count(),
        'factures_en_retard': Facture.objects.filter(
            statut__in=['EMISE', 'PARTIELLEMENT_PAYEE'],
            date_echeance__lt=aujourd.date()
        ).count(),
        'concessions_expirent_bientot': Concession.objects.filter(
            type_concession='TEMPORAIRE',
            statut='ACTIVE',
            date_fin__isnull=False,
            date_fin__gte=aujourd.date(),
            date_fin__lte=aujourd.date() + timedelta(days=30)
        ).count(),
        'derniers_emails': EmailLog.objects.all()[:10],
        'dernieres_notifications': Notification.objects.filter(lue=False)[:10],
    }
    
    return render(request, 'admin/notifications/dashboard.html', context)

AdminSite.notifications_dashboard = notifications_dashboard