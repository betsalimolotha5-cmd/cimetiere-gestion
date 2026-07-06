"""
URLs pour la gestion des paiements.
"""
from django.urls import path
from . import views

urlpatterns = [
    path('mes-factures/', views.mes_factures, name='mes_factures'),
    path('facture/<int:facture_id>/', views.facture_detail, name='facture_detail'),
    path('facture/<int:facture_id>/paiement/', views.paiement_form, name='paiement_form'),
]