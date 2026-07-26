"""
URLs pour l'application core.
AJOUT : Routes pour les téléchargements PDF, le rapport statistique et les QR Codes des caveaux.
"""
from django.urls import path
from . import views

urlpatterns = [
    # ==================================================================
    # EXPORTS CSV
    # ==================================================================
    path('export/csv/caveaux/', views.export_csv_caveaux, name='export_csv_caveaux'),
    path('export/csv/concessions/', views.export_csv_concessions, name='export_csv_concessions'),
    path('export/csv/defunts/', views.export_csv_defunts, name='export_csv_defunts'),
    path('export/csv/inhumations/', views.export_csv_inhumations, name='export_csv_inhumations'),
    path('export/csv/exhumations/', views.export_csv_exhumations, name='export_csv_exhumations'),
    
    # ==================================================================
    # EXPORTS EXCEL
    # ==================================================================
    path('export/excel/caveaux/', views.export_excel_caveaux, name='export_excel_caveaux'),
    path('export/excel/concessions/', views.export_excel_concessions, name='export_excel_concessions'),
    path('export/excel/defunts/', views.export_excel_defunts, name='export_excel_defunts'),
    path('export/excel/inhumations/', views.export_excel_inhumations, name='export_excel_inhumations'),
    path('export/excel/exhumations/', views.export_excel_exhumations, name='export_excel_exhumations'),
    
    # ==================================================================
    # EXPORTS PDF
    # ==================================================================
    path('concession/<int:concession_id>/contrat-pdf/', views.contrat_concession_pdf, name='contrat_concession_pdf'),
    path('concession/<int:concession_id>/attestation-pdf/', views.attestation_concession_pdf, name='attestation_concession_pdf'),
    path('inhumation/<int:inhumation_id>/pv-pdf/', views.pv_inhumation_pdf, name='pv_inhumation_pdf'),
    path('demande-exhumation/<int:demande_id>/autorisation-pdf/', views.autorisation_exhumation_pdf, name='autorisation_exhumation_pdf'),
    path('demande-exhumation/<int:demande_id>/pv-exhumation-pdf/', views.pv_exhumation_pdf, name='pv_exhumation_pdf'),
    path('rapport-statistique-pdf/', views.rapport_statistique_pdf, name='rapport_statistique_pdf'),
    
    # ==================================================================
    # QR CODES CAVEAUX
    # ==================================================================
    path('caveau/<int:caveau_id>/qr-code/', views.qr_code_caveau, name='qr_code_caveau'),
    path('caveau/<int:caveau_id>/qr-info/', views.qr_info_caveau, name='qr_info_caveau'),
    
    # ==================================================================
    # CONFIGURATION
    # ==================================================================
    path('configurer/', views.configurer_cimetiere, name='configurer_cimetiere'),
    
    # ==================================================================
    # INITIALISATION (Temporaire, pour le déploiement)
    # ==================================================================
    path('init-db/', views.init_db, name='init_db'),
]