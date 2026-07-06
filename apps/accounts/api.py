"""
API Django Ninja pour la gestion des comptes utilisateurs.
"""
from ninja import Router, Schema
from ninja.security import HttpBearer
from django.contrib.auth import authenticate, login, logout
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from typing import Optional, List
from datetime import datetime
import logging

from .models import User

router = Router(tags=["Authentification"])
logger = logging.getLogger('audit')


# === SCHÉMAS ===

class LoginSchema(Schema):
    email: str
    password: str


class MFAVerifySchema(Schema):
    user_id: int
    code: str


class RegisterSchema(Schema):
    email: str
    first_name: str
    last_name: str
    phone: str
    national_id: str
    address: str
    password: str


class UserResponseSchema(Schema):
    id: int
    email: str
    first_name: str
    last_name: str
    role: str
    phone: Optional[str] = None
    is_active: bool
    date_joined: datetime
    
    class Config:
        from_attributes = True


class ProfileUpdateSchema(Schema):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None


class PasswordChangeSchema(Schema):
    old_password: str
    new_password: str


class TokenSchema(Schema):
    access_token: str
    user_id: int
    user_email: str
    requires_mfa: bool = False


class MessageSchema(Schema):
    success: bool
    message: str
    data: Optional[dict] = None


# === AUTHENTIFICATION BEARER ===

class AuthBearer(HttpBearer):
    def authenticate(self, request, token):
        if token == "valid_token":  # Simplifié pour l'exemple
            return token
        return None


# === ENDPOINTS ===

@router.post("/login", response=TokenSchema)
def api_login(request, payload: LoginSchema):
    """Endpoint de connexion avec gestion MFA."""
    user = authenticate(request, email=payload.email, password=payload.password)
    
    if user is None:
        return 401, {"access_token": "", "user_id": 0, "user_email": "", "requires_mfa": False}
    
    if not user.is_active:
        return 403, {"access_token": "", "user_id": 0, "user_email": "", "requires_mfa": False}
    
    # Si MFA activé, on ne connecte pas encore
    if user.mfa_enabled:
        # Générer et envoyer le code MFA
        token = user.get_mfa_token()
        
        # Stocker en session
        request.session['pre_mfa_user_id'] = user.id
        request.session['mfa_token'] = token
        
        # Envoyer l'email
        _send_mfa_email(user, token)
        
        logger.info(f"API_LOGIN_MFA_REQUIRED: user={user.email}")
        
        return {
            "access_token": "",
            "user_id": user.id,
            "user_email": user.email,
            "requires_mfa": True
        }
    
    # Connexion directe sans MFA
    login(request, user)
    _log_login(request, user)
    
    return {
        "access_token": "session_authenticated",
        "user_id": user.id,
        "user_email": user.email,
        "requires_mfa": False
    }


@router.post("/mfa/verify", response=TokenSchema)
def api_mfa_verify(request, payload: MFAVerifySchema):
    """Vérification du code MFA."""
    user_id = request.session.get('pre_mfa_user_id')
    expected_token = request.session.get('mfa_token')
    
    if not user_id or user_id != payload.user_id:
        return 400, {"access_token": "", "user_id": 0, "user_email": "", "requires_mfa": False}
    
    try:
        user = User.objects.get(id=payload.user_id)
        
        # Vérifier le code
        if user.verify_mfa_token(payload.code) or payload.code == expected_token:
            # Connexion réussie
            login(request, user)
            
            # Nettoyer la session
            if 'pre_mfa_user_id' in request.session:
                del request.session['pre_mfa_user_id']
            if 'mfa_token' in request.session:
                del request.session['mfa_token']
            
            user.mfa_verified = True
            user.save(update_fields=['mfa_verified'])
            
            logger.info(f"API_MFA_SUCCESS: user={user.email}")
            
            return {
                "access_token": "session_authenticated",
                "user_id": user.id,
                "user_email": user.email,
                "requires_mfa": False
            }
        else:
            return 401, {"access_token": "", "user_id": 0, "user_email": "", "requires_mfa": False}
    
    except User.DoesNotExist:
        return 404, {"access_token": "", "user_id": 0, "user_email": "", "requires_mfa": False}


@router.post("/register", response=MessageSchema)
def api_register(request, payload: RegisterSchema):
    """Inscription d'un nouveau client."""
    # Vérifier si l'email existe déjà
    if User.objects.filter(email=payload.email).exists():
        return 400, {"success": False, "message": "Cet email est déjà utilisé.", "data": None}
    
    # Vérifier si le numéro d'identité existe déjà
    if User.objects.filter(national_id=payload.national_id).exists():
        return 400, {"success": False, "message": "Ce numéro d'identité est déjà utilisé.", "data": None}
    
    # Créer l'utilisateur
    user = User.objects.create_user(
        email=payload.email,
        password=payload.password,
        first_name=payload.first_name,
        last_name=payload.last_name,
        phone=payload.phone,
        national_id=payload.national_id,
        address=payload.address,
        role=User.Role.CLIENT,
        mfa_enabled=True,
    )
    
    # Envoyer l'email de bienvenue
    _send_welcome_email(user)
    
    logger.info(f"API_USER_REGISTERED: user={user.email}, role=CLIENT")
    
    return {
        "success": True,
        "message": "Inscription réussie ! Vous pouvez maintenant vous connecter.",
        "data": {"user_id": user.id}
    }


@router.get("/me", response=UserResponseSchema, auth=AuthBearer())
def api_get_profile(request):
    """Récupérer le profil de l'utilisateur connecté."""
    user = request.user
    return user


@router.put("/me", response=UserResponseSchema, auth=AuthBearer())
def api_update_profile(request, payload: ProfileUpdateSchema):
    """Mettre à jour le profil de l'utilisateur."""
    user = request.user
    
    if payload.first_name is not None:
        user.first_name = payload.first_name
    if payload.last_name is not None:
        user.last_name = payload.last_name
    if payload.phone is not None:
        user.phone = payload.phone
    if payload.address is not None:
        user.address = payload.address
    
    user.save()
    
    logger.info(f"API_PROFILE_UPDATED: user={user.email}")
    
    return user


@router.post("/change-password", response=MessageSchema, auth=AuthBearer())
def api_change_password(request, payload: PasswordChangeSchema):
    """Changer le mot de passe."""
    user = request.user
    
    if not user.check_password(payload.old_password):
        return 400, {"success": False, "message": "Ancien mot de passe incorrect.", "data": None}
    
    if len(payload.new_password) < 8:
        return 400, {"success": False, "message": "Le nouveau mot de passe doit contenir au moins 8 caractères.", "data": None}
    
    user.set_password(payload.new_password)
    user.save()
    
    logger.info(f"API_PASSWORD_CHANGED: user={user.email}")
    
    return {
        "success": True,
        "message": "Mot de passe modifié avec succès.",
        "data": None
    }


@router.post("/logout", response=MessageSchema)
def api_logout(request):
    """Déconnexion de l'utilisateur."""
    if request.user.is_authenticated:
        logger.info(f"API_LOGOUT: user={request.user.email}")
        logout(request)
    
    return {
        "success": True,
        "message": "Déconnexion réussie.",
        "data": None
    }


@router.post("/mfa/resend", response=MessageSchema)
def api_resend_mfa(request):
    """Renvoyer le code MFA."""
    user_id = request.session.get('pre_mfa_user_id')
    
    if not user_id:
        return 400, {"success": False, "message": "Aucune authentification en cours.", "data": None}
    
    try:
        user = User.objects.get(id=user_id)
        token = user.get_mfa_token()
        request.session['mfa_token'] = token
        
        _send_mfa_email(user, token)
        
        return {
            "success": True,
            "message": "Code MFA renvoyé avec succès.",
            "data": None
        }
    except User.DoesNotExist:
        return 404, {"success": False, "message": "Utilisateur introuvable.", "data": None}


# === FONCTIONS UTILITAIRES ===

def _send_mfa_email(user: User, token: str):
    """Envoie le code MFA par email."""
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
    except Exception as e:
        logger.error(f"EMAIL_MFA_FAILED: user={user.email}, error={str(e)}")


def _send_welcome_email(user: User):
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
    except Exception as e:
        logger.error(f"EMAIL_WELCOME_FAILED: user={user.email}, error={str(e)}")


def _log_login(request, user: User):
    """Enregistre la connexion dans l'audit log."""
    ip = request.META.get('REMOTE_ADDR', 'unknown')
    user.last_login_ip = ip
    user.save(update_fields=['last_login_ip'])
    logger.info(f"API_LOGIN_SUCCESS: user={user.email}, ip={ip}")