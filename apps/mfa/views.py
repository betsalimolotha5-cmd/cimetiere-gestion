"""
Vues pour l'authentification à double facteur (MFA) par email.
"""
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from .models import MFACode
from apps.accounts.models import User


def login_view(request):
    """Page de connexion avec identifiants email/password."""
    if request.user.is_authenticated:
        return redirect('/admin/')
    
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        
        try:
            user_obj = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request, 'Email ou mot de passe incorrect.')
            return render(request, 'mfa/login.html')
        
        user = authenticate(request, username=user_obj.email, password=password)
        
        if user is not None:
            # 1. Générer le code MFA
            ip_address = get_client_ip(request)
            code_obj = MFACode.generer_code(user, ip_address=ip_address)
            
            # 2. Stocker en session
            request.session['mfa_user_id'] = user.id
            request.session['mfa_email'] = user.email
            
            # 3. Envoyer l'email (avec gestion d'erreur pour éviter le crash 500)
            try:
                send_mail(
                    subject='🔐 Votre code de connexion - Gestion Cimetière',
                    message=f'Bonjour {user.get_full_name() or user.email},\n\nVotre code de vérification est : {code_obj.code}\n\nCe code expire dans 10 minutes.',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=False,
                )
                messages.success(request, f'✅ Un code de vérification a été envoyé à {user.email}.')
            except Exception as e:
                # Affiche l'erreur exacte dans les logs Render pour le débogage
                print(f"🚨 ERREUR ENVOI EMAIL BREVO : {e}")
                messages.error(request, f'Erreur technique lors de l\'envoi. Détail: {e}')
                return render(request, 'mfa/login.html')
            
            return redirect('mfa_verification')
        else:
            messages.error(request, 'Email ou mot de passe incorrect.')
    
    return render(request, 'mfa/login.html')


def verification_view(request):
    """Page de vérification du code MFA à 6 chiffres."""
    user_id = request.session.get('mfa_user_id')
    email = request.session.get('mfa_email')
    
    if not user_id:
        return redirect('login')
    
    if request.method == 'POST':
        code_saisi = request.POST.get('code', '').strip()
        
        if not code_saisi.isdigit() or len(code_saisi) != 6:
            messages.error(request, 'Le code doit contenir exactement 6 chiffres.')
            return render(request, 'mfa/verification.html', {'email': email})
        
        try:
            user = User.objects.get(id=user_id)
            code_obj = MFACode.objects.filter(
                utilisateur=user,
                code=code_saisi,
                utilise=False
            ).latest('date_creation')
            
            if code_obj.est_valide():
                code_obj.utilise = True
                code_obj.save()
                
                login(request, user)
                
                if 'mfa_user_id' in request.session:
                    del request.session['mfa_user_id']
                if 'mfa_email' in request.session:
                    del request.session['mfa_email']
                
                messages.success(request, f'Bienvenue {user.get_full_name() or user.email} !')
                return redirect('/admin/')
            else:
                messages.error(request, 'Code expiré. Veuillez vous reconnecter.')
                return redirect('login')
                
        except (User.DoesNotExist, MFACode.DoesNotExist):
            messages.error(request, 'Code invalide. Veuillez réessayer.')
    
    return render(request, 'mfa/verification.html', {'email': email})


def resend_code_view(request):
    """Renvoyer un nouveau code MFA."""
    user_id = request.session.get('mfa_user_id')
    
    if not user_id:
        return redirect('login')
    
    try:
        user = User.objects.get(id=user_id)
        ip_address = get_client_ip(request)
        code_obj = MFACode.generer_code(user, ip_address=ip_address)
        
        sujet = '🔐 Votre nouveau code de connexion'
        message_texte = f"Votre nouveau code de vérification est : {code_obj.code}\n\nCe code expire dans 10 minutes."
        
        try:
            send_mail(
                subject=sujet,
                message=message_texte,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
            messages.success(request, 'Un nouveau code a été envoyé.')
        except Exception as e:
            print(f"🚨 ERREUR RENVOI EMAIL BREVO : {e}")
            messages.error(request, f'Erreur lors du renvoi. Détail: {e}')
            
    except User.DoesNotExist:
        messages.error(request, 'Erreur. Veuillez vous reconnecter.')
        return redirect('login')
    
    return redirect('mfa_verification')


def logout_view(request):
    """Déconnexion de l'utilisateur."""
    logout(request)
    messages.success(request, 'Vous avez été déconnecté avec succès.')
    return redirect('login')


def get_client_ip(request):
    """Récupère l'adresse IP du client."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')