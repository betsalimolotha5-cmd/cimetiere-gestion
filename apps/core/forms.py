"""
Formulaires pour l'application core.
"""
from django import forms
from .models import ParametreCimetiere


class ParametreCimetiereForm(forms.ModelForm):
    """Formulaire pour les paramètres du cimetière."""
    
    class Meta:
        model = ParametreCimetiere
        fields = [
            'nom',
            'adresse',
            'superficie_totale',
            'longueur_standard_caveau',
            'largeur_standard_caveau',
            'largeur_allee',
        ]
        widgets = {
            'nom': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom du cimetière'
            }),
            'adresse': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Adresse complète du cimetière'
            }),
            'superficie_totale': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': 'Superficie en m²'
            }),
            'longueur_standard_caveau': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': '2.5'
            }),
            'largeur_standard_caveau': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': '1.2'
            }),
            'largeur_allee': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': '3.0'
            }),
        }
        labels = {
            'nom': 'Nom du cimetière',
            'adresse': 'Adresse',
            'superficie_totale': 'Superficie totale (m²)',
            'longueur_standard_caveau': 'Longueur standard d\'un caveau (m)',
            'largeur_standard_caveau': 'Largeur standard d\'un caveau (m)',
            'largeur_allee': 'Largeur des allées (m)',
        }