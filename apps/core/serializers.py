"""
Serializers pour l'API REST.
"""
from rest_framework import serializers
from .models import Zone, Caveau, Concession, Defunt, Inhumation, DemandeExhumation


class ZoneSerializer(serializers.ModelSerializer):
    """Serializer pour les zones."""
    
    class Meta:
        model = Zone
        fields = '__all__'


class CaveauSerializer(serializers.ModelSerializer):
    """Serializer pour les caveaux."""
    zone_nom = serializers.CharField(source='zone.nom', read_only=True)
    
    class Meta:
        model = Caveau
        fields = '__all__'


class DefuntSerializer(serializers.ModelSerializer):
    """Serializer pour les défunts."""
    
    class Meta:
        model = Defunt
        fields = '__all__'


class ConcessionSerializer(serializers.ModelSerializer):
    """Serializer pour les concessions."""
    concessionnaire_nom = serializers.CharField(source='concessionnaire.get_full_name', read_only=True)
    caveau_code = serializers.CharField(source='caveau.code', read_only=True)
    defunt_nom = serializers.SerializerMethodField()
    
    class Meta:
        model = Concession
        fields = '__all__'
    
    def get_defunt_nom(self, obj):
        if obj.defunt:
            return f"{obj.defunt.nom} {obj.defunt.prenom}"
        return None


class InhumationSerializer(serializers.ModelSerializer):
    """Serializer pour les inhumations."""
    defunt_nom = serializers.CharField(source='defunt.get_full_name', read_only=True)
    caveau_code = serializers.CharField(source='concession.caveau.code', read_only=True)
    
    class Meta:
        model = Inhumation
        fields = '__all__'


class DemandeExhumationSerializer(serializers.ModelSerializer):
    """Serializer pour les demandes d'exhumation."""
    defunt_nom = serializers.CharField(source='inhumation.defunt.get_full_name', read_only=True)
    
    class Meta:
        model = DemandeExhumation
        fields = '__all__'