"""
API Admin pour la gestion des utilisateurs (CRUD complet).
Accessible uniquement aux administrateurs.
"""
from ninja import Router, Schema
from ninja.security import HttpBearer
from typing import Optional, List
from datetime import datetime
from django.contrib.auth import get_user_model
from django.db.models import Q
import logging

from .models import User
from .services import PermissionService

router = Router(tags=["Admin - Utilisateurs"])
logger = logging.getLogger('audit')


class AuthBearer(HttpBearer):
    def authenticate(self, request, token):
        if token == "session_authenticated":
            return token
        return None


# === SCHÉMAS ===

class UserSchema(Schema):
    id: int
    email: str
    first_name: str
    last_name: str
    role: str
    phone: Optional[str] = None
    is_active: bool
    is_staff: bool
    mfa_enabled: bool
    date_joined: datetime
    last_login: Optional[datetime] = None
    employee_id: Optional[str] = None
    assignment_zone: Optional[str] = None
    national_id: Optional[str] = None
    address: Optional[str] = None
    
    class Config:
        from_attributes = True


class UserCreateSchema(Schema):
    email: str
    first_name: str
    last_name: str
    password: str
    role: str = User.Role.CLIENT
    phone: Optional[str] = None
    is_active: bool = True
    is_staff: bool = False
    mfa_enabled: bool = True
    employee_id: Optional[str] = None
    assignment_zone: Optional[str] = None
    national_id: Optional[str] = None
    address: Optional[str] = None


class UserUpdateSchema(Schema):
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None
    is_staff: Optional[bool] = None
    mfa_enabled: Optional[bool] = None
    employee_id: Optional[str] = None
    assignment_zone: Optional[str] = None
    national_id: Optional[str] = None
    address: Optional[str] = None


class MessageSchema(Schema):
    success: bool
    message: str
    data: Optional[dict] = None


# === VÉRIFICATION DES PERMISSIONS ===

def check_admin(request):
    """Vérifie que l'utilisateur est administrateur."""
    if not request.user.is_authenticated:
        return False
    return request.user.is_admin()


# === ENDPOINTS ===

@router.get("/users/", response=List[UserSchema], auth=AuthBearer())
def list_users(request):
    """Liste tous les utilisateurs (admin uniquement)."""
    if not check_admin(request):
        return 403, {"success": False, "message": "Accès refusé. Réservé aux administrateurs."}
    
    users = User.objects.all().order_by('-date_joined')
    return list(users)


@router.get("/users/{user_id}", response=UserSchema, auth=AuthBearer())
def get_user(request, user_id: int):
    """Récupère un utilisateur spécifique."""
    if not check_admin(request):
        return 403, {"success": False, "message": "Accès refusé."}
    
    try:
        user = User.objects.get(id=user_id)
        return user
    except User.DoesNotExist:
        return 404, {"success": False, "message": "Utilisateur introuvable."}


@router.post("/users/", response=MessageSchema, auth=AuthBearer())
def create_user(request, payload: UserCreateSchema):
    """Crée un nouvel utilisateur."""
    if not check_admin(request):
        return 403, {"success": False, "message": "Accès refusé."}
    
    # Vérifier si l'email existe déjà
    if User.objects.filter(email=payload.email).exists():
        return 400, {"success": False, "message": "Un utilisateur avec cet email existe déjà."}
    
    try:
        user = User.objects.create_user(
            email=payload.email,
            password=payload.password,
            first_name=payload.first_name,
            last_name=payload.last_name,
            role=payload.role,
            phone=payload.phone,
            is_active=payload.is_active,
            is_staff=payload.is_staff,
            mfa_enabled=payload.mfa_enabled,
            employee_id=payload.employee_id,
            assignment_zone=payload.assignment_zone,
            national_id=payload.national_id,
            address=payload.address,
        )
        
        logger.info(f"ADMIN_USER_CREATED: user={user.email}, role={user.role}, by={request.user.email}")
        
        return {
            "success": True,
            "message": f"Utilisateur {user.email} créé avec succès.",
            "data": {"user_id": user.id}
        }
    except Exception as e:
        logger.error(f"ADMIN_USER_CREATE_FAILED: error={str(e)}")
        return 500, {"success": False, "message": f"Erreur lors de la création: {str(e)}"}


@router.put("/users/{user_id}", response=MessageSchema, auth=AuthBearer())
def update_user(request, user_id: int, payload: UserUpdateSchema):
    """Met à jour un utilisateur."""
    if not check_admin(request):
        return 403, {"success": False, "message": "Accès refusé."}
    
    try:
        user = User.objects.get(id=user_id)
        
        # Mise à jour des champs
        if payload.email and payload.email != user.email:
            if User.objects.filter(email=payload.email).exclude(id=user_id).exists():
                return 400, {"success": False, "message": "Cet email est déjà utilisé par un autre utilisateur."}
            user.email = payload.email
        
        if payload.first_name is not None:
            user.first_name = payload.first_name
        if payload.last_name is not None:
            user.last_name = payload.last_name
        if payload.password is not None:
            user.set_password(payload.password)
        if payload.role is not None:
            user.role = payload.role
        if payload.phone is not None:
            user.phone = payload.phone
        if payload.is_active is not None:
            user.is_active = payload.is_active
        if payload.is_staff is not None:
            user.is_staff = payload.is_staff
        if payload.mfa_enabled is not None:
            user.mfa_enabled = payload.mfa_enabled
        if payload.employee_id is not None:
            user.employee_id = payload.employee_id
        if payload.assignment_zone is not None:
            user.assignment_zone = payload.assignment_zone
        if payload.national_id is not None:
            user.national_id = payload.national_id
        if payload.address is not None:
            user.address = payload.address
        
        user.save()
        
        logger.info(f"ADMIN_USER_UPDATED: user={user.email}, by={request.user.email}")
        
        return {
            "success": True,
            "message": f"Utilisateur {user.email} mis à jour avec succès.",
            "data": {"user_id": user.id}
        }
    except User.DoesNotExist:
        return 404, {"success": False, "message": "Utilisateur introuvable."}
    except Exception as e:
        logger.error(f"ADMIN_USER_UPDATE_FAILED: user_id={user_id}, error={str(e)}")
        return 500, {"success": False, "message": f"Erreur lors de la mise à jour: {str(e)}"}


@router.delete("/users/{user_id}", response=MessageSchema, auth=AuthBearer())
def delete_user(request, user_id: int):
    """Supprime un utilisateur."""
    if not check_admin(request):
        return 403, {"success": False, "message": "Accès refusé."}
    
    try:
        user = User.objects.get(id=user_id)
        
        # Ne pas supprimer le superuser actuel
        if user.is_superuser:
            return 400, {"success": False, "message": "Impossible de supprimer un superutilisateur."}
        
        # Ne pas supprimer l'utilisateur connecté
        if user.id == request.user.id:
            return 400, {"success": False, "message": "Impossible de supprimer votre propre compte."}
        
        user.delete()
        
        logger.info(f"ADMIN_USER_DELETED: user={user.email}, by={request.user.email}")
        
        return {
            "success": True,
            "message": f"Utilisateur {user.email} supprimé avec succès.",
            "data": None
        }
    except User.DoesNotExist:
        return 404, {"success": False, "message": "Utilisateur introuvable."}
    except Exception as e:
        logger.error(f"ADMIN_USER_DELETE_FAILED: user_id={user_id}, error={str(e)}")
        return 500, {"success": False, "message": f"Erreur lors de la suppression: {str(e)}"}


@router.post("/users/{user_id}/activate", response=MessageSchema, auth=AuthBearer())
def activate_user(request, user_id: int):
    """Active un utilisateur."""
    if not check_admin(request):
        return 403, {"success": False, "message": "Accès refusé."}
    
    try:
        user = User.objects.get(id=user_id)
        user.is_active = True
        user.save()
        
        logger.info(f"ADMIN_USER_ACTIVATED: user={user.email}, by={request.user.email}")
        
        return {
            "success": True,
            "message": f"Utilisateur {user.email} activé avec succès.",
            "data": None
        }
    except User.DoesNotExist:
        return 404, {"success": False, "message": "Utilisateur introuvable."}


@router.post("/users/{user_id}/deactivate", response=MessageSchema, auth=AuthBearer())
def deactivate_user(request, user_id: int):
    """Désactive un utilisateur."""
    if not check_admin(request):
        return 403, {"success": False, "message": "Accès refusé."}
    
    try:
        user = User.objects.get(id=user_id)
        user.is_active = False
        user.save()
        
        logger.info(f"ADMIN_USER_DEACTIVATED: user={user.email}, by={request.user.email}")
        
        return {
            "success": True,
            "message": f"Utilisateur {user.email} désactivé avec succès.",
            "data": None
        }
    except User.DoesNotExist:
        return 404, {"success": False, "message": "Utilisateur introuvable."}


@router.post("/users/bulk-activate", response=MessageSchema, auth=AuthBearer())
def bulk_activate_users(request, user_ids: List[int]):
    """Active plusieurs utilisateurs en masse."""
    if not check_admin(request):
        return 403, {"success": False, "message": "Accès refusé."}
    
    try:
        count = User.objects.filter(id__in=user_ids).update(is_active=True)
        
        logger.info(f"ADMIN_BULK_ACTIVATE: count={count}, by={request.user.email}")
        
        return {
            "success": True,
            "message": f"{count} utilisateur(s) activé(s) avec succès.",
            "data": {"count": count}
        }
    except Exception as e:
        logger.error(f"ADMIN_BULK_ACTIVATE_FAILED: error={str(e)}")
        return 500, {"success": False, "message": f"Erreur: {str(e)}"}


@router.post("/users/bulk-deactivate", response=MessageSchema, auth=AuthBearer())
def bulk_deactivate_users(request, user_ids: List[int]):
    """Désactive plusieurs utilisateurs en masse."""
    if not check_admin(request):
        return 403, {"success": False, "message": "Accès refusé."}
    
    try:
        count = User.objects.filter(id__in=user_ids).update(is_active=False)
        
        logger.info(f"ADMIN_BULK_DEACTIVATE: count={count}, by={request.user.email}")
        
        return {
            "success": True,
            "message": f"{count} utilisateur(s) désactivé(s) avec succès.",
            "data": {"count": count}
        }
    except Exception as e:
        logger.error(f"ADMIN_BULK_DEACTIVATE_FAILED: error={str(e)}")
        return 500, {"success": False, "message": f"Erreur: {str(e)}"}
