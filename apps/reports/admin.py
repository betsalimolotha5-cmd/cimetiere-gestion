"""
Admin pour l'application reports.
"""
from django.contrib import admin
from .models import RapportGenere


@admin.register(RapportGenere)
class RapportGenereAdmin(admin.ModelAdmin):
    list_display = ['titre', 'type_rapport', 'format_export', 'genere_par', 'date_generation', 'nombre_lignes']
    list_filter = ['type_rapport', 'format_export', 'date_generation']
    search_fields = ['titre', 'genere_par__email']
    readonly_fields = ['date_generation', 'taille_fichier']
    date_hierarchy = 'date_generation'