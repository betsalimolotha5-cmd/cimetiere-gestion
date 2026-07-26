"""
URLs pour la gestion des paiements.
AJOUT : Routes pour les téléchargements PDF (facture et reçu de paiement).
"""
from django.urls import path
from . import views

urlpatterns = [
    # ==================================================================
    # VUES CLIENT (PORTAIL)
    # ==================================================================
    path('mes-factures/', views.mes_factures, name='mes_factures'),
    path('facture/<int:facture_id>/', views.facture_detail, name='facture_detail'),
    path('facture/<int:facture_id>/paiement/', views.paiement_form, name='paiement_form'),
    
    # ==================================================================
    # EXPORTS PDF
    # ==================================================================
    path('facture/<int:facture_id>/pdf/', views.facture_pdf, name='facture_pdf'),
    path('paiement/<int:paiement_id>/recu-pdf/', views.recu_paiement_pdf, name='recu_paiement_pdf'),
]