"""
Vues pour la gestion des comptes utilisateurs et authentification.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import CreateView, UpdateView, TemplateView
from django.urls import reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import pyotp

from .models import User
from .forms import (
    LoginForm,
    MFACodeForm,
    ClientRegistrationForm,
    ProfileUpdateForm,
    PasswordChangeForm,
)


class LoginRequiredMixinCustom(LoginRequiredMixin):
    """Mixin personnalisé avec redirection adaptée."""
    login_url = reverse_lazy('accounts:login')


class LoginView(TemplateView):
    """Vue de connexion avec gestion du MFA."""
    template_name = 'accounts/login.html'
    
    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('accounts:dashboard')
        form = LoginForm()
        return render(request, self.template_name, {'form': form})
    
    def post(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('accounts:dashboard')
        
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            
            user = authenticate(request, email=email, password=password)
            
            if user is not None:
                if not user.is_active:
                    messages.error(request, 'Votre compte est désactivé.')
                    return render(request, self.template_name, {'form': form})
                
                # Stocker l'user_id en session pour la vérification MFA
                request.session['pre_mfa_user_id'] = user.id
                request.session['pre_mfa_backend'] = user.backend
                
                if user.mfa_enabled:
                    # Envoyer le code MFA par email
                    self._send_mfa_code(user)
                    return redirect('accounts:mfa_verify')
                else:
                    # Connexion directe sans MFA
                    login(request, user)
                    self._log_login(request, user)
                    messages.success(request, f'Bienvenue {user.get_short_name()} !')
                    return redirect('accounts:dashboard')
            else:
                messages.error(request, 'Email ou mot de passe incorrect.')
        
        return render(request, self.template_name, {'form': form})
    
    def _send_mfa_code(self, user):
        """Envoie le code MFA par email."""
        token = user.get_mfa_token()
        request = self.request
        
        # Stocker le token en session pour vérification
        request.session['mfa_token'] = token
        
        # Envoyer l'email
        html_message = render_to_string('emails/mfa_code.html', {
            'user': user,
            'code': token,
        })
        plain_message = strip_tags(html_message)
        
        try:
            send_mail(
                subject='Votre code de vérification - Cimetière',
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
            )
            messages.info(request, f'Un code de vérification a été envoyé à {user.email}')
        except Exception as e:
            messages.error(request, f'Erreur lors de l\'envoi de l\'email : {str(e)}')
    
    def _log_login(self, request, user):
        """Enregistre la connexion dans l'audit log."""
        import logging
        logger = logging.getLogger('audit')
        ip = request.META.get('REMOTE_ADDR', 'unknown')
        user.last_login_ip = ip
        user.save(update_fields=['last_login_ip'])
        logger.info(f'LOGIN_SUCCESS: user={user.email}, ip={ip}')


class MFAVerifyView(TemplateView):
    """Vue de vérification du code MFA."""
    template_name = 'accounts/mfa_verify.html'
    
    def get(self, request, *args, **kwargs):
        if 'pre_mfa_user_id' not in request.session:
            return redirect('accounts:login')
        form = MFACodeForm()
        return render(request, self.template_name, {'form': form})
    
    def post(self, request, *args, **kwargs):
        if 'pre_mfa_user_id' not in request.session:
            return redirect('accounts:login')
        
        form = MFACodeForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['code']
            user_id = request.session['pre_mfa_user_id']
            expected_token = request.session.get('mfa_token')
            
            try:
                user = User.objects.get(id=user_id)
                
                # Vérifier le code
                if user.verify_mfa_token(code) or code == expected_token:
                    # Connexion réussie
                    login(request, user, backend=request.session['pre_mfa_backend'])
                    
                    # Nettoyer la session
                    del request.session['pre_mfa_user_id']
                    del request.session['pre_mfa_backend']
                    if 'mfa_token' in request.session:
                        del request.session['mfa_token']
                    
                    user.mfa_verified = True
                    user.save(update_fields=['mfa_verified'])
                    
                    # Log
                    import logging
                    logger = logging.getLogger('audit')
                    ip = request.META.get('REMOTE_ADDR', 'unknown')
                    logger.info(f'MFA_SUCCESS: user={user.email}, ip={ip}')
                    
                    messages.success(request, 'Vérification MFA réussie !')
                    return redirect('accounts:dashboard')
                else:
                    messages.error(request, 'Code MFA incorrect. Veuillez réessayer.')
            except User.DoesNotExist:
                messages.error(request, 'Utilisateur introuvable.')
                return redirect('accounts:login')
        
        return render(request, self.template_name, {'form': form})


class ClientRegistrationView(CreateView):
    """Vue d'inscription pour les clients (citoyens)."""
    model = User
    form_class = ClientRegistrationForm
    template_name = 'accounts/register.html'
    success_url = reverse_lazy('accounts:login')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        user = self.object
        
        # Forcer le rôle client
        user.role = User.Role.CLIENT
        user.mfa_enabled = True  # MFA obligatoire pour les clients
        user.save()
        
        # Envoyer email de bienvenue
        self._send_welcome_email(user)
        
        # Log
        import logging
        logger = logging.getLogger('audit')
        logger.info(f'USER_REGISTERED: user={user.email}, role=CLIENT')
        
        messages.success(
            self.request,
            'Inscription réussie ! Vous pouvez maintenant vous connecter.'
        )
        return response
    
    def _send_welcome_email(self, user):
        """Envoie l'email de bienvenue."""
        html_message = render_to_string('emails/welcome.html', {
            'user': user,
        })
        plain_message = strip_tags(html_message)
        
        try:
            send_mail(
                subject='Bienvenue sur la plateforme de gestion du cimetière',
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=True,
            )
        except Exception:
            pass


class DashboardView(LoginRequiredMixinCustom, TemplateView):
    """Vue du tableau de bord après connexion."""
    template_name = 'accounts/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        context['user'] = user
        context['role'] = user.get_role_display()
        context['can_manage_caveaux'] = user.can_manage_caveaux()
        context['can_validate_reservations'] = user.can_validate_reservations()
        context['can_view_financial_stats'] = user.can_view_financial_stats()
        
        return context


class ProfileUpdateView(LoginRequiredMixinCustom, UpdateView):
    """Vue de mise à jour du profil utilisateur."""
    model = User
    form_class = ProfileUpdateForm
    template_name = 'accounts/profile.html'
    success_url = reverse_lazy('accounts:profile')
    
    def get_object(self, queryset=None):
        return self.request.user
    
    def form_valid(self, form):
        messages.success(self.request, 'Profil mis à jour avec succès.')
        return super().form_valid(form)


class PasswordChangeView(LoginRequiredMixinCustom, TemplateView):
    """Vue de changement de mot de passe."""
    template_name = 'accounts/password_change.html'
    
    def get(self, request, *args, **kwargs):
        form = PasswordChangeForm()
        return render(request, self.template_name, {'form': form})
    
    def post(self, request, *args, **kwargs):
        form = PasswordChangeForm(request.POST)
        if form.is_valid():
            user = request.user
            old_password = form.cleaned_data['old_password']
            new_password = form.cleaned_data['new_password']
            
            if user.check_password(old_password):
                user.set_password(new_password)
                user.save()
                
                # Reconnecter l'utilisateur
                login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                
                messages.success(request, 'Mot de passe modifié avec succès.')
                return redirect('accounts:profile')
            else:
                messages.error(request, 'Ancien mot de passe incorrect.')
        
        return render(request, self.template_name, {'form': form})


@login_required
def logout_view(request):
    """Vue de déconnexion."""
    import logging
    logger = logging.getLogger('audit')
    logger.info(f'LOGOUT: user={request.user.email}')
    
    logout(request)
    messages.info(request, 'Vous avez été déconnecté.')
    return redirect('accounts:login')


@require_POST
@login_required
def resend_mfa_code(request):
    """Renvoie le code MFA par email (API AJAX)."""
    user = request.user
    
    if not user.mfa_enabled:
        return JsonResponse({'success': False, 'error': 'MFA non activé'}, status=400)
    
    token = user.get_mfa_token()
    request.session['mfa_token'] = token
    
    html_message = render_to_string('emails/mfa_code.html', {
        'user': user,
        'code': token,
    })
    plain_message = strip_tags(html_message)
    
    try:
        send_mail(
            subject='Votre nouveau code de vérification',
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        return JsonResponse({'success': True, 'message': 'Code renvoyé'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)