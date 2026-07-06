"""
Configuration des URLs pour l'application accounts.
"""
from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # Authentification
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.ClientRegistrationView.as_view(), name='register'),
    
    # MFA (Authentification à double facteur)
    path('mfa/verify/', views.MFAVerifyView.as_view(), name='mfa_verify'),
    path('mfa/resend/', views.resend_mfa_code, name='mfa_resend'),
    
    # Tableau de bord
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    
    # Profil utilisateur
    path('profile/', views.ProfileUpdateView.as_view(), name='profile'),
    path('password/change/', views.PasswordChangeView.as_view(), name='password_change'),
]