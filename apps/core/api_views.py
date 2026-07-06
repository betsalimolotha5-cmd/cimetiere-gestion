"""
Vues API REST pour l'application core.
"""
from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated
from .models import Zone, Caveau, Concession, Defunt, Inhumation, DemandeExhumation
from .serializers import (
    ZoneSerializer,
    CaveauSerializer,
    ConcessionSerializer,
    DefuntSerializer,
    InhumationSerializer,
    DemandeExhumationSerializer,
)


class ZoneViewSet(viewsets.ModelViewSet):
    """API endpoint pour les zones."""
    queryset = Zone.objects.all()
    serializer_class = ZoneSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['code', 'nom']
    ordering_fields = ['code', 'nom']


class CaveauViewSet(viewsets.ModelViewSet):
    """API endpoint pour les caveaux."""
    queryset = Caveau.objects.select_related('zone').all()
    serializer_class = CaveauSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['code', 'zone__nom']
    filterset_fields = ['statut', 'zone']
    ordering_fields = ['code', 'statut']


class DefuntViewSet(viewsets.ModelViewSet):
    """API endpoint pour les défunts."""
    queryset = Defunt.objects.all()
    serializer_class = DefuntSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['nom', 'prenom']
    ordering_fields = ['nom', 'date_deces']


class ConcessionViewSet(viewsets.ModelViewSet):
    """API endpoint pour les concessions."""
    queryset = Concession.objects.select_related('concessionnaire', 'caveau', 'defunt').all()
    serializer_class = ConcessionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['numero_contrat', 'concessionnaire__email']
    filterset_fields = ['statut', 'type_concession']
    ordering_fields = ['date_debut', 'statut']


class InhumationViewSet(viewsets.ModelViewSet):
    """API endpoint pour les inhumations."""
    queryset = Inhumation.objects.select_related('defunt', 'concession', 'concession__caveau').all()
    serializer_class = InhumationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['date_inhumation']


class DemandeExhumationViewSet(viewsets.ModelViewSet):
    """API endpoint pour les demandes d'exhumation."""
    queryset = DemandeExhumation.objects.select_related('inhumation', 'inhumation__defunt').all()
    serializer_class = DemandeExhumationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    filterset_fields = ['statut']
    ordering_fields = ['date_demande', 'statut']