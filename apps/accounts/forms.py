"""
Formulaires pour la gestion des comptes utilisateurs.
"""
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from .models import User


class LoginForm(forms.Form):
    """Formulaire de connexion."""
    email = forms.EmailField(
        label='Adresse email',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'votre@email.com',
            'autofocus': True,
        })
    )
    password = forms.CharField(
        label='Mot de passe',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '••••••••',
        })
    )
    remember_me = forms.BooleanField(
        label='Se souvenir de moi',
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )


class MFACodeForm(forms.Form):
    """Formulaire de vérification du code MFA."""
    code = forms.CharField(
        label='Code de vérification',
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '000000',
            'autofocus': True,
            'autocomplete': 'one-time-code',
            'inputmode': 'numeric',
            'pattern': '[0-9]*',
        })
    )
    
    def clean_code(self):
        code = self.cleaned_data['code']
        if not code.isdigit():
            raise ValidationError('Le code doit contenir uniquement des chiffres.')
        return code


class ClientRegistrationForm(UserCreationForm):
    """Formulaire d'inscription pour les clients (citoyens)."""
    email = forms.EmailField(
        label='Adresse email',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'votre@email.com',
        })
    )
    first_name = forms.CharField(
        label='Prénom',
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Prénom',
        })
    )
    last_name = forms.CharField(
        label='Nom',
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nom',
        })
    )
    phone = forms.CharField(
        label='Téléphone',
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+243...',
        })
    )
    national_id = forms.CharField(
        label='Numéro d\'identité nationale',
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Numéro d\'identité',
        })
    )
    address = forms.CharField(
        label='Adresse',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Votre adresse complète',
            'rows': 3,
        })
    )
    password1 = forms.CharField(
        label='Mot de passe',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '••••••••',
        })
    )
    password2 = forms.CharField(
        label='Confirmation du mot de passe',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '••••••••',
        })
    )
    
    class Meta:
        model = User
        fields = (
            'email',
            'first_name',
            'last_name',
            'phone',
            'national_id',
            'address',
            'password1',
            'password2',
        )
    
    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise ValidationError('Un compte avec cet email existe déjà.')
        return email
    
    def clean_national_id(self):
        national_id = self.cleaned_data['national_id']
        if User.objects.filter(national_id=national_id).exists():
            raise ValidationError('Un compte avec ce numéro d\'identité existe déjà.')
        return national_id
    
    def clean_phone(self):
        phone = self.cleaned_data['phone']
        # Nettoyage basique du numéro
        phone = phone.replace(' ', '').replace('-', '').replace('.', '')
        if len(phone) < 9:
            raise ValidationError('Numéro de téléphone trop court.')
        return phone
    
    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        
        if password1 and password2 and password1 != password2:
            self.add_error('password2', 'Les mots de passe ne correspondent pas.')
        
        return cleaned_data
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.CLIENT
        user.mfa_enabled = True
        user.username = self.cleaned_data['email']  # Pour compatibilité
        
        if commit:
            user.save()
        return user


class ProfileUpdateForm(forms.ModelForm):
    """Formulaire de mise à jour du profil."""
    
    class Meta:
        model = User
        fields = (
            'first_name',
            'last_name',
            'phone',
            'address',
        )
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class PasswordChangeForm(forms.Form):
    """Formulaire de changement de mot de passe."""
    old_password = forms.CharField(
        label='Ancien mot de passe',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '••••••••',
        })
    )
    new_password = forms.CharField(
        label='Nouveau mot de passe',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '••••••••',
        })
    )
    confirm_password = forms.CharField(
        label='Confirmer le nouveau mot de passe',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '••••••••',
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if new_password and confirm_password and new_password != confirm_password:
            self.add_error('confirm_password', 'Les mots de passe ne correspondent pas.')
        
        if new_password and len(new_password) < 8:
            self.add_error('new_password', 'Le mot de passe doit contenir au moins 8 caractères.')
        
        return cleaned_data


class AdminUserCreateForm(UserCreationForm):
    """Formulaire de création d'utilisateur pour les administrateurs."""
    
    class Meta:
        model = User
        fields = (
            'email',
            'first_name',
            'last_name',
            'role',
            'phone',
            'is_active',
            'is_staff',
        )
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
        }