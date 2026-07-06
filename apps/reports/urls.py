"""
URLs pour les rapports et statistiques.
"""
from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('financier/', views.rapport_financier, name='rapport_financier'),
    path('occupation/', views.rapport_occupation, name='rapport_occupation'),
    path('concessions/', views.rapport_concessions, name='rapport_concessions'),
    path('notifications/', views.rapport_notifications, name='rapport_notifications'),
    path('export/excel/', views.export_rapport_excel, name='export_rapport_excel'),
    path('export/pdf/', views.export_rapport_pdf, name='export_rapport_pdf'),
]
