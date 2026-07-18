"""
Vues pour l'authentification à double facteur (MFA) par email.
Avec mécanisme anti-crash (timeout explicite) pour éviter les erreurs 502 sur Render.
"""
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.utils.html import strip_tags
from .models import MFACode
from apps.accounts.models import User
import concurrent.futures


def _send_email_safe(subject, message_texte, html_message, from_email, recipient_list, timeout=10):
    """
    Envoie un email avec un timeout explicite de 10 secondes.
    Retourne (True, None) si succès, (False, exception) si échec ou timeout.
    """
    def _do_send():
        send_mail(
            subject=subject,
            message=message_texte,
            html_message=html_message,
            from_email=from_email,
            recipient_list=recipient_list,
            fail_silently=False,
        )
    
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_do_send)
            future.result(timeout=timeout)  # Timeout de 10 secondes
        return True, None
    except concurrent.futures.TimeoutError:
        return False, "Timeout: l'envoi d'email a pris trop de temps (blocage réseau hébergeur)"
    except Exception as e:
        return False, str(e)


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
                send_mail(
                    subject='🔐 Votre code de connexion - Gestion Cimetière',
                    message=f'Bonjour {user.get_full_name() or user.email},\n\nVotre code de vérification est : {code_obj.code}\n\nCe code expire dans 10 minutes.',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=False,
                )
                messages.success(request, f'✅ Un code de vérification a été envoyé à {user.email}.')
            except Exception as e:
                # On force l'affichage de l'erreur exacte dans les logs Render
                print(f"🚨 ERREUR ENVOI EMAIL BREVO : {e}")
                messages.error(request, f'Erreur lors de l\'envoi de l\'email. Vérifiez les logs. Détail: {e}')
                return render(request, 'mfa/login.html')
            <html>
            <body style="font-family: Arial, sans-serif; background-color: #f5f5f5; padding: 20px;">
                <div style="max-width: 500px; margin: auto; background: white; padding: 30px; border-radius: 10px;">
                    <h2 style="color: #2c3e50;">🔐 Vérification de sécurité</h2>
                    <p>Bonjour <strong>{user.get_full_name() or user.email}</strong>,</p>
                    <p>Votre code de vérification est :</p>
                    <div style="background: #667eea; color: white; font-size: 32px; font-weight: bold; 
                                text-align: center; padding: 20px; border-radius: 8px; letter-spacing: 8px;">
                        {code_mfa}
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
            
            # ️ ENVOI D'EMAIL AVEC TIMEOUT EXPLICITE (anti-crash 502)
            success, error = _send_email_safe(
                subject=sujet,
                message_texte=message_texte,
                html_message=message_html,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                timeout=10,
            )
            
            if success:
                messages.success(request, f'✅ Un code de vérification a été envoyé à {user.email}.')
            else:
                # FALLBACK : L'email a échoué ou a timeout → on affiche le code à l'écran
                # C'est la sécurité qui empêche l'erreur 502
                messages.warning(
                    request,
                    f"⚠️ Service email indisponible ({error}). "
                    f"Code de démonstration : {code_mfa}"
                )
            
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
                if 'last_mfa_code' in request.session:
                    del request.session['last_mfa_code']
                
                messages.success(request, f'Bienvenue {user.get_full_name() or user.email} !')
                return redirect('/admin/')
            else:
                messages.error(request, 'Code expiré. Veuillez vous reconnecter.')
                return redirect('login')
                
        except (User.DoesNotExist, MFACode.DoesNotExist):
            messages.error(request, 'Code invalide. Veuillez réessayer.')
    
    # Afficher le code en session pour la démo (si fallback activé)
    last_code = request.session.get('last_mfa_code', '')
    
    return render(request, 'mfa/verification.html', {
        'email': email,
        'demo_code': last_code if last_code else None,
    })


def resend_code_view(request):
    """
    Renvoyer un nouveau code MFA.
    """
    user_id = request.session.get('mfa_user_id')
    email = request.session.get('mfa_email')
    
    if not user_id:
        return redirect('login')
    
    try:
        user = User.objects.get(id=user_id)
        ip_address = get_client_ip(request)
        code_obj = MFACode.generer_code(user, ip_address=ip_address)
        code_mfa = code_obj.code
        
        # Mettre à jour le code en session
        request.session['last_mfa_code'] = code_mfa
        
        sujet = ' Votre nouveau code de connexion'
        message_texte = f"Votre nouveau code de vérification est : {code_mfa}\n\nCe code expire dans 10 minutes."
        message_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <div style="max-width: 500px; margin: auto; background: white; padding: 30px; border-radius: 10px;">
                <h2 style="color: #2c3e50;">🔐 Nouveau code de vérification</h2>
                <p>Bonjour <strong>{user.get_full_name() or user.email}</strong>,</p>
                <div style="background: #667eea; color: white; font-size: 32px; font-weight: bold; 
                            text-align: center; padding: 20px; border-radius: 8px; letter-spacing: 8px;">
                    {code_mfa}
                </div>
                <p style="margin-top: 20px; color: #7f8c8d;">
                    ️ Ce code expire dans <strong>10 minutes</strong>.
                </p>
            </div>
        </body>
        </html>
        """
        
        # 🛡️ ENVOI AVEC TIMEOUT
        success, error = _send_email_safe(
            subject=sujet,
            message_texte=message_texte,
            html_message=message_html,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            timeout=10,
        )
        
        if success:
            messages.success(request, '✅ Un nouveau code a été envoyé à votre email.')
        else:
            messages.warning(
                request,
                f"⚠️ Service email indisponible ({error}). "
                f"Nouveau code : {code_mfa}"
            )
            
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