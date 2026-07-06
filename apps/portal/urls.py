"""
URLs du portail client (Carte publique + Réservations + Factures + Paiements).
"""
from django.urls import path
from . import views

urlpatterns = [
    # Carte publique
    path('', views.carte_publique, name='carte_publique'),
    path('api/carte/', views.api_carte_publique, name='api_carte_publique'),
    
    # Réservations
    path('reservation/<int:caveau_id>/', views.reservation_form, name='reservation_form'),
    path('mes-reservations/', views.mes_reservations, name='mes_reservations'),
    
    # Factures et paiements
    path('mes-factures/', views.mes_factures, name='mes_factures'),
    path('facture/<int:facture_id>/', views.facture_detail, name='facture_detail'),
    path('facture/<int:facture_id>/payer/', views.payer_facture, name='payer_facture'),
]