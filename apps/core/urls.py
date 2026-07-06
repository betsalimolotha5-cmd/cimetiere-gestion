"""
URLs pour l'application core.
"""
from django.urls import path
from . import views

urlpatterns = [
    # Exports CSV
    path('export/csv/caveaux/', views.export_csv_caveaux, name='export_csv_caveaux'),
    path('export/csv/concessions/', views.export_csv_concessions, name='export_csv_concessions'),
    path('export/csv/defunts/', views.export_csv_defunts, name='export_csv_defunts'),
    path('export/csv/inhumations/', views.export_csv_inhumations, name='export_csv_inhumations'),
    path('export/csv/exhumations/', views.export_csv_exhumations, name='export_csv_exhumations'),
    
    # Exports Excel
    path('export/excel/caveaux/', views.export_excel_caveaux, name='export_excel_caveaux'),
    path('export/excel/concessions/', views.export_excel_concessions, name='export_excel_concessions'),
    path('export/excel/defunts/', views.export_excel_defunts, name='export_excel_defunts'),
    path('export/excel/inhumations/', views.export_excel_inhumations, name='export_excel_inhumations'),
    path('export/excel/exhumations/', views.export_excel_exhumations, name='export_excel_exhumations'),
    path('configurer/', views.configurer_cimetiere, name='configurer_cimetiere'),
]