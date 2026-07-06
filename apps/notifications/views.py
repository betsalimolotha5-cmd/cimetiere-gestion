"""
Vues pour la gestion des notifications.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import ListView
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.utils import timezone
import logging

from .models import Notification
from .services import NotificationService

logger = logging.getLogger('audit')


class NotificationLoginRequiredMixin(LoginRequiredMixin):
    """Mixin personnalisé avec redirection adaptée."""
    login_url = reverse_lazy('accounts:login')


class NotificationListView(NotificationLoginRequiredMixin, ListView):
    """Liste de toutes les notifications de l'utilisateur."""
    model = Notification
    template_name = 'notifications/notification_list.html'
    context_object_name = 'notifications'
    paginate_by = 20
    
    def get_queryset(self):
        return Notification.objects.filter(
            utilisateur=self.request.user
        ).order_by('-priorite', '-date_creation')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['count_non_lues'] = Notification.compter_non_lues(self.request.user)
        return context


class NotificationNonLuesView(NotificationLoginRequiredMixin, ListView):
    """Liste des notifications non lues."""
    model = Notification
    template_name = 'notifications/notification_non_lues.html'
    context_object_name = 'notifications'
    paginate_by = 20
    
    def get_queryset(self):
        return Notification.objects.filter(
            utilisateur=self.request.user,
            lue=False
        ).order_by('-priorite', '-date_creation')


@login_required
def marquer_comme_lue(request, pk):
    """Marque une notification comme lue."""
    notification = get_object_or_404(
        Notification,
        pk=pk,
        utilisateur=request.user
    )
    
    notification.marquer_comme_lue()
    
    # Si la notification a un lien, rediriger vers ce lien
    if notification.url_lien:
        return redirect(notification.url_lien)
    
    return redirect('notifications:notification_list')


@login_required
def marquer_toutes_comme_lues(request):
    """Marque toutes les notifications comme lues."""
    if request.method == 'POST':
        NotificationService.marquer_toutes_comme_lues(request.user)
        messages.success(request, 'Toutes les notifications ont été marquées comme lues.')
    
    return redirect('notifications:notification_list')


# === API JSON ===

@login_required
def api_compter_non_lues(request):
    """API JSON pour compter les notifications non lues."""
    count = Notification.compter_non_lues(request.user)
    return JsonResponse({'count': count})


@login_required
def api_liste_notifications(request):
    """API JSON pour lister les notifications."""
    limit = int(request.GET.get('limit', 10))
    non_lues_only = request.GET.get('non_lues_only', 'false').lower() == 'true'
    
    queryset = Notification.objects.filter(utilisateur=request.user)
    
    if non_lues_only:
        queryset = queryset.filter(lue=False)
    
    notifications = queryset.order_by('-priorite', '-date_creation')[:limit]
    
    data = []
    for notif in notifications:
        data.append({
            'id': notif.id,
            'titre': notif.titre,
            'message': notif.message,
            'type': notif.type_notification,
            'priorite': notif.priorite,
            'lue': notif.lue,
            'url_lien': notif.url_lien,
            'date_creation': notif.date_creation.isoformat(),
        })
    
    return JsonResponse({
        'notifications': data,
        'total_non_lues': Notification.compter_non_lues(request.user),
    })