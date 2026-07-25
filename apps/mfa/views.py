"""
Vues pour l'authentification à double facteur (MFA) par email.
Conforme au CDC : robuste, sans crash, avec fallback de démo.
CORRECTION DÉFINITIVE : 
  1. Gestion blindée du backend d'authentification pour éviter les redirections vers /login
  2. Ajout du rôle "Secrétaire" dans la logique de redirection
"""
import requests
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.conf import settings
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
    
    api_key = getattr(settings, 'BREVO_API_KEY', '')
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'betsalimolotha5@gmail.com')
    
    if not api_key or not api_key.startswith('xkeysib-'):
        print("❌ [MFA] ERREUR : La clé API est invalide ou manquante.")
        return False

    url = "https://api.brevo.com/v3/smtp/email"
    headers = {
        "accept": "application/json",
        "api-key": api_key,
        "content-type": "application/json"
    }
    
    payload = {
        "sender": {"name": "Gestion Cimetière", "email": from_email},
        "to": [{"email": user.email}],
        "subject": "🔐 Votre code de connexion sécurisé",
        "htmlContent": f"""
        <div style="font-family: Arial, sans-serif; padding: 25px; background-color: #f9f9f9; border-radius: 8px;">
            <h2 style="color: #2c5f2d; margin-top: 0;">Code de vérification</h2>
            <p>Bonjour {user.get_full_name() or user.email},</p>
            <p>Pour finaliser votre connexion, veuillez utiliser le code suivant :</p>
            <h1 style="background: #ffffff; padding: 20px; text-align: center; letter-spacing: 8px; font-size: 36px; border: 2px dashed #2c5f2d; border-radius: 8px; margin: 20px 0; color: #2c5f2d;">{code}</h1>
            <p style="color: #666; font-size: 14px;">Ce code est valable 10 minutes. Ne le partagez avec personne.</p>
        </div>
        """
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        print(f"📬 [MFA] Réponse HTTP Brevo : {response.status_code}")
        
        if response.status_code not in [200, 201]:
            print(f"❌ [MFA] DÉTAILS DU REJET BREVO : {response.text}")
            return False
            
        print(f"✅ [MFA] SUCCÈS : Email envoyé avec succès à {user.email}")
        return True
        
    except requests.exceptions.Timeout:
        print("❌ [MFA] ÉCHEC : Timeout de la connexion à Brevo")
        return False
    except Exception as e:
        print(f"❌ [MFA] EXCEPTION SYSTÈME : {str(e)}")
        return False


def login_view(request):
    """Page de connexion avec identifiants email/password."""
    if request.user.is_authenticated:
        return redirect('carte_publique')
    
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
            # ⭐ CORRECTION BLINDÉE : Récupérer le backend avec une valeur par défaut sécurisée
            backend = getattr(user, 'backend', 'django.contrib.auth.backends.ModelBackend')
            
            request.session['mfa_user_id'] = user.id
            request.session['mfa_email'] = user.email
            request.session['mfa_auth_backend'] = backend  # Sauvegarde robuste
            
            ip_address = get_client_ip(request)
            code_obj = MFACode.generer_code(user, ip_address=ip_address)
            
            email_sent = send_mfa_email_via_api(user, code_obj.code)
            
            if email_sent:
                messages.success(request, f'✅ Un code de vérification a été envoyé à {user.email}.')
            else:
                messages.warning(
                    request, 
                    f'⚠️ Restriction de l\'hébergeur : l\'email a été filtré. Code de secours : {code_obj.code}'
                )
            
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
                
                # ⭐ CORRECTION BLINDÉE : Restaurer le backend AVANT login() avec fallback
                auth_backend = request.session.get('mfa_auth_backend', 'django.contrib.auth.backends.ModelBackend')
                user.backend = auth_backend
                
                # Connexion effective de l'utilisateur
                login(request, user)
                
                # Nettoyage de la session MFA
                for key in ['mfa_user_id', 'mfa_email', 'mfa_auth_backend']:
                    if key in request.session:
                        del request.session[key]
                
                messages.success(request, f'Bienvenue {user.get_full_name() or user.email} !')
                
                # ⭐ REDIRECTION INTELLIGENTE SELON LE RÔLE (CORRECTION : Ajout du rôle Secrétaire)
                if user.is_staff:
                    return redirect('dashboard_admin')
                
                # Vérification du rôle Agent
                user_groups = user.groups.values_list('name', flat=True)
                if 'Agents' in user_groups or 'Agent' in user_groups:
                    return redirect('dashboard_agent')
                
                # Vérification du rôle Secrétaire
                if 'Secretaires' in user_groups or 'Secrétaire' in user_groups:
                    return redirect('dashboard_secretary')  # Ajout du rôle Secrétaire
                
                # Par défaut : Client -> Carte publique
                return redirect('carte_publique')
                
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
        
        email_sent = send_mfa_email_via_api(user, code_obj.code)
        
        if email_sent:
            messages.success(request, 'Un nouveau code a été envoyé par email.')
        else:
            messages.warning(request, f'⚠️ Restriction hébergeur. Code de secours : {code_obj.code}')
            
    except User.DoesNotExist:
        messages.error(request, 'Erreur. Veuillez vous reconnecter.')
        return redirect('login')
    
    return redirect('mfa_verification')


def register_view(request):
    """Page de création de compte utilisateur."""
    if request.user.is_authenticated:
        return redirect('carte_publique')
    
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        password = request.POST.get('password', '')
        password_confirm = request.POST.get('password_confirm', '')
        
        erreurs = []
        if not email:
            erreurs.append("L'email est obligatoire.")
        elif User.objects.filter(email=email).exists():
            erreurs.append("Un compte existe déjà avec cet email.")
        if not first_name:
            erreurs.append("Le prénom est obligatoire.")
        if not last_name:
            erreurs.append("Le nom est obligatoire.")
        if not password:
            erreurs.append("Le mot de passe est obligatoire.")
        elif len(password) < 8:
            erreurs.append("Le mot de passe doit contenir au moins 8 caractères.")
        if password != password_confirm:
            erreurs.append("Les mots de passe ne correspondent pas.")
        
        if erreurs:
            for e in erreurs:
                messages.error(request, e)
            return render(request, 'mfa/register.html', {
                'email': email, 'first_name': first_name, 'last_name': last_name,
            })
        
        try:
            user = User.objects.create_user(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
            )
            user.is_active = True
            user.save()
            
            messages.success(request, f'✅ Compte créé avec succès ! Connectez-vous avec {email}.')
            return redirect('login')
        except Exception as e:
            messages.error(request, f'Erreur lors de la création du compte : {e}')
    
    return render(request, 'mfa/register.html')


def logout_view(request):
    """Déconnexion de l'utilisateur."""
    logout(request)
    messages.success(request, 'Vous avez été déconnecté avec succès.')
    return redirect('login')