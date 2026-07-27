"""
URLs du portail client (Carte publique + Réservations + Factures + Paiements).
CORRIGÉ : Ajout de toutes les routes nécessaires pour les dashboards et actions.
"""
from django.urls import path
from django.shortcuts import redirect
from . import views
from apps.core import views as core_views

urlpatterns = [
    # Carte publique
    path('', views.carte_publique, name='carte_publique'),
    path('api/carte/', views.api_carte_publique, name='api_carte_publique'),
    
    # Dashboard adaptatif (selon le rôle)
    path('dashboard/', core_views.dashboard, name='dashboard'),
    
    # Réservations
    path('reservation/', views.reservation_form, name='reservation_form'),
    path('reservation/<int:caveau_id>/', views.reservation_form, name='reservation_form_caveau'),
    path('mes-reservations/', views.mes_reservations, name='mes_reservations'),
    
    # Factures et paiements
    path('mes-factures/', views.mes_factures, name='mes_factures'),
    path('facture/<int:facture_id>/', views.facture_detail, name='facture_detail'),
    path('facture/<int:facture_id>/payer/', views.payer_facture, name='payer_facture'),
    
    # Concessions (pour les clients)
    path('mes-concessions/', views.mes_concessions, name='mes_concessions'),
    
    # Exhumations (demande client)
    path('exhumation/demande/', views.demande_exhumation, name='demande_exhumation'),
    
    # Statistiques (redirige vers le rapport PDF pour l'instant)
    path('statistiques/', lambda request: redirect('/cimetiere/rapport-statistique-pdf/'), name='statistiques'),
    
    # Configuration (redirige vers la page de configuration du cimetière)
    path('configuration/', lambda request: redirect('/cimetiere/configurer/'), name='configuration'),
    
    # Audit et Utilisateurs (redirige vers l'admin Django pour l'instant)
    path('audit/', lambda request: redirect('/admin/'), name='audit'),
    path('utilisateurs/', lambda request: redirect('/admin/accounts/user/'), name='utilisateurs'),
]