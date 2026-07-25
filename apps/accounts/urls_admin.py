"""
URLs pour les API Admin de l'application accounts.
Version sécurisée pour éviter l'erreur 'Router' object has no attribute 'urls'.
"""
from django.urls import path

# Liste vide pour éviter tout conflit ou erreur d'importation.
# Les routes admin de accounts doivent être gérées via l'instance principale 
# de l'API (ex: Django Ninja) et non via un include Django standard.

urlpatterns = []