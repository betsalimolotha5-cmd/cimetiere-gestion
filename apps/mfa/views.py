"""
Vues pour l'authentification à double facteur (MFA) par email.
"""
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.utils.html import strip_tags
from .models import MFACode
from apps.accounts.models import User


def login_view(request):
    """
    Page de connexion avec identifiants email/password.
    Après validation, un code MFA est envoyé par email.
    """
    # Si déjà connecté, rediriger vers l'admin
    if request.user.is_authenticated:
        return redirect('/admin/')
    
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        
        # Récupérer l'utilisateur par email
        try:
            user_obj = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request, 'Email ou mot de passe incorrect.')
            return render(request, 'mfa/login.html')
        
        # Authentification Django
        user = authenticate(request, username=user_obj.email, password=password)
        
        if user is not None:
            # Générer le code MFA
            ip_address = get_client_ip(request)
            code_obj = MFACode.generer_code(user, ip_address=ip_address)
            
            # Envoyer le code par email
            sujet = '🔐 Votre code de connexion - Gestion Cimetière'
            message_html = f"""
            <html>
            <body style="font-family: Arial, sans-serif; background-color: #f5f5f5; padding: 20px;">
                <div style="max-width: 500px; margin: auto; background: white; padding: 30px; border-radius: 10px;">
                    <h2 style="color: #2c3e50;">🔐 Vérification de sécurité</h2>
                    <p>Bonjour <strong>{user.get_full_name() or user.email}</strong>,</p>
                    <p>Votre code de vérification est :</p>
                    <div style="background: #667eea; color: white; font-size: 32px; font-weight: bold; 
                                text-align: center; padding: 20px; border-radius: 8px; letter-spacing: 8px;">
                        {code_obj.code}
                    </div>
                    <p style="margin-top: 20px; color: #7f8c8d;">
                        ⏱️ Ce code expire dans <strong>10 minutes</strong>.<br>
                        🔒 Ne partagez jamais ce code avec qui que ce soit.
                    </p>
                    <p style="font-size: 12px; color: #95a5a6; margin-top: 30px;">
                        Si vous n'êtes pas à l'origine de cette demande, ignorez cet email.
                    </p>
                </div>
            </body>
            </html>
            """
            message_texte = strip_tags(message_html)
            
            try:
                send_mail(
                    subject=sujet,
                    message=message_texte,
                    html_message=message_html,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=False,
                )
                messages.success(request, 'Un code de vérification a été envoyé à votre adresse email.')
            except Exception as e:
                # En développement avec console backend, on continue quand même
                print(f"[MFA] Code pour {user.email}: {code_obj.code}")
                messages.warning(request, f"Email non envoyé (mode dev). Code: {code_obj.code}")
            
            # Stocker l'ID utilisateur en session pour l'étape suivante
            request.session['mfa_user_id'] = user.id
            request.session['mfa_email'] = user.email
            
            return redirect('mfa_verification')
        else:
            messages.error(request, 'Email ou mot de passe incorrect.')
    
    return render(request, 'mfa/login.html')


def verification_view(request):
    """
    Page de vérification du code MFA à 6 chiffres.
    """
    user_id = request.session.get('mfa_user_id')
    email = request.session.get('mfa_email')
    
    # Si pas de session MFA, rediriger vers login
    if not user_id:
        return redirect('login')
    
    if request.method == 'POST':
        code_saisi = request.POST.get('code', '').strip()
        
        # Vérifier que le code fait bien 6 chiffres
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
                # Marquer le code comme utilisé
                code_obj.utilise = True
                code_obj.save()
                
                # Connecter l'utilisateur
                login(request, user)
                
                # Nettoyer la session MFA
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
    """
    Renvoyer un nouveau code MFA.
    """
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
        except Exception:
            print(f"[MFA] Nouveau code pour {user.email}: {code_obj.code}")
            messages.warning(request, f"Email non envoyé (mode dev). Code: {code_obj.code}")
    except User.DoesNotExist:
        messages.error(request, 'Erreur. Veuillez vous reconnecter.')
        return redirect('login')
    
    return redirect('mfa_verification')


def logout_view(request):
    """
    Déconnexion de l'utilisateur.
    """
    logout(request)
    messages.success(request, 'Vous avez été déconnecté avec succès.')
    return redirect('login')


def get_client_ip(request):
    """Récupère l'adresse IP du client."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')