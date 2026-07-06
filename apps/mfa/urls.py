"""
URLs pour l'authentification MFA.
"""
from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('verification/', views.verification_view, name='mfa_verification'),
    path('renvoyer-code/', views.resend_code_view, name='resend_code'),
    path('logout/', views.logout_view, name='logout'),
] 
