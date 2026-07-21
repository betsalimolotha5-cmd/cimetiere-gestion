"""
Vues pour l'authentification à double facteur (MFA) par email.
Conforme au CDC : robuste, sans crash, avec affichage persistant du code de démo.
"""
import requests
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.conf import settings
from django.db.utils import OperationalError  # ⭐ AJOUTÉ : Pour gérer les coupures DB Neon
from .models import MFACode
from apps.accounts.models import User


def get_client_ip(request):
    """Récupère l'adresse IP du client."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def send_mfa_email_via_api(user, code):
    """Envoie le code MFA via l'API HTTPS de Brevo (Port 443)."""
    print(f"📧 [MFA] Tentative d'envoi du code {code} à {user.email}")
    
    url = "https://api.brevo.com/v3/smtp/email"
    api_key = getattr(settings, 'BREVO_API_KEY', '')
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'betsalimolotha5@gmail.com')
    
    if not api_key or api_key == 'ta_cle_api_ici':
        print("❌ [MFA] ERREUR : BREVO_API_KEY manquante.")
        return False

    headers = {
        "accept": "application/json",
        "api-key": api_key,
        "content-type": "application/json"
    }
    
    payload = {
        "sender": {"name": "Gestion Cimetière", "email": from_email},
        "to": [{"email": user.email}],
        "subject": "🔐 Votre code de connexion sécurisé",
        "htmlContent": f"<p>Bonjour,</p><p>Votre code est : <strong>{code}</strong></p><p>Expire dans 10 min.</p>"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code in [200, 201]:
            print(f"✅ [MFA] SUCCÈS : Email envoyé (Status: {response.status_code})")
            return True
        else:
            print(f"❌ [MFA] ÉCHEC BREVO : Status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ [MFA] ÉCHEC CRITIQUE : {str(e)}")
        return False


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
            ip_address = get_client_ip(request)
            code_obj = MFACode.generer_code(user, ip_address=ip_address)
            
            request.session['mfa_user_id'] = user.id
            request.session['mfa_email'] = user.email
            
            # Nettoyage de l'ancien code de démo s'il existe
            if 'mfa_demo_code' in request.session:
                del request.session['mfa_demo_code']
            
            email_sent = send_mfa_email_via_api(user, code_obj.code)
            
            if email_sent:
                messages.success(request, f'✅ Un code de vérification a été envoyé à {user.email}.')
            else:
                # ⭐ ASTUCE : On sauvegarde le code dans la session pour l'afficher en gros sur la page suivante
                request.session['mfa_demo_code'] = code_obj.code
                messages.warning(request, '⚠️ Restriction hébergeur : Email filtré. Voir le code ci-dessous.')
            
            return redirect('mfa_verification')
        else:
            messages.error(request, 'Email ou mot de passe incorrect.')
    
    return render(request, 'mfa/login.html')


def verification_view(request):
    """Page de vérification du code MFA à 6 chiffres, blindée contre les coupures DB."""
    try:
        # ⭐ On enveloppe tout dans un try/except pour capturer les coupures Neon
        user_id = request.session.get('mfa_user_id')
        email = request.session.get('mfa_email')
        
        # ⭐ On récupère le code de démo (et on le retire de la session pour qu'il ne s'affiche qu'une fois)
        demo_code = request.session.pop('mfa_demo_code', None)
        
        if not user_id:
            return redirect('login')
        
        if request.method == 'POST':
            code_saisi = request.POST.get('code', '').strip()
            
            if not code_saisi.isdigit() or len(code_saisi) != 6:
                messages.error(request, 'Le code doit contenir exactement 6 chiffres.')
                return render(request, 'mfa/verification.html', {'email': email, 'demo_code': demo_code})
            
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
        return render(request, 'mfa/verification.html', {'email': email, 'demo_code': demo_code})
    
    except OperationalError:
        # ⭐ GESTION DES COUPURES NEON : La DB s'est endormie.
        # On nettoie la session et on renvoie au login pour forcer une connexion saine.
        request.session.flush()
        messages.warning(request, '⚠️ La base de données était en veille. Veuillez vous reconnecter.')
        return redirect('login')
    
    # Fallback par défaut si rien ne matche (ex: méthode GET)
    return render(request, 'mfa/verification.html', {'email': email, 'demo_code': demo_code})


def resend_code_view(request):
    """Renvoyer un nouveau code MFA."""
    user_id = request.session.get('mfa_user_id')
    
    if not user_id:
        return redirect('login')
    
    try:
        user = User.objects.get(id=user_id)
        ip_address = get_client_ip(request)
        code_obj = MFACode.generer_code(user, ip_address=ip_address)
        
        email_sent = send_mfa_email_via_api(user, code_obj.code)
        
        if email_sent:
            messages.success(request, 'Un nouveau code a été envoyé par email.')
        else:
            # ⭐ Sauvegarde pour affichage persistant
            request.session['mfa_demo_code'] = code_obj.code
            messages.warning(request, '⚠️ Restriction hébergeur. Voir le code sur la page de vérification.')
            
    except User.DoesNotExist:
        messages.error(request, 'Erreur. Veuillez vous reconnecter.')
        return redirect('login')
    
    return redirect('mfa_verification')


def logout_view(request):
    """Déconnexion de l'utilisateur."""
    logout(request)
    messages.success(request, 'Vous avez été déconnecté avec succès.')
    return redirect('login')