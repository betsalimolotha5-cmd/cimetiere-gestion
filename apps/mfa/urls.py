from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('verification/', views.verification_view, name='mfa_verification'),
    path('resend-code/', views.resend_code_view, name='resend_code'),  # ⭐ Corrigé pour matcher ton template
    path('logout/', views.logout_view, name='logout'),
]