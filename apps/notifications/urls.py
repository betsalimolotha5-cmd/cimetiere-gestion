"""
Configuration des URLs pour l'application notifications.
"""
from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    # === NOTIFICATIONS ===
    path('', views.NotificationListView.as_view(), name='notification_list'),
    path('non-lues/', views.NotificationNonLuesView.as_view(), name='notification_non_lues'),
    path('<int:pk>/lire/', views.marquer_comme_lue, name='notification_lire'),
    path('toutes-lire/', views.marquer_toutes_comme_lues, name='notifications_toutes_lire'),
    
    # === API JSON ===
    path('api/compter-non-lues/', views.api_compter_non_lues, name='api_compter_non_lues'),
    path('api/liste/', views.api_liste_notifications, name='api_liste_notifications'),
]