"""
URLs pour l'API REST.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import (
    ZoneViewSet,
    CaveauViewSet,
    DefuntViewSet,
    ConcessionViewSet,
    InhumationViewSet,
    DemandeExhumationViewSet,
)

router = DefaultRouter()
router.register(r'zones', ZoneViewSet)
router.register(r'caveaux', CaveauViewSet)
router.register(r'defunts', DefuntViewSet)
router.register(r'concessions', ConcessionViewSet)
router.register(r'inhumations', InhumationViewSet)
router.register(r'exhumations', DemandeExhumationViewSet)

urlpatterns = [
    path('', include(router.urls)),
]