"""
Services métier pour la gestion des comptes utilisateurs.
"""
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.contrib.auth import get_user_model
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

User = get_user_model()
logger = logging.getLogger('audit')


class AuthService:
    """Service d'authentification et de gestion des sessions."""
    
    @staticmethod
    def send_mfa_code(user: User, request=None) -> bool:
        """
        Envoie le code MFA par email à l'utilisateur.
        
        Args:
            user: L'utilisateur à qui envoyer le code
            request: La requête HTTP (optionnel, pour stocker en session)
        
        Returns:
            bool: True si l'email a été envoyé avec succès
        """
        try:
            # Générer le token MFA
            token = user.get_mfa_token()
            
            # Stocker en session si request fourni
            if request:
                request.session['pre_mfa_user_id'] = user.id
                request.session['mfa_token'] = token
            
            # Préparer l'email
            html_message = render_to_string('emails/mfa_code.html', {
                'user': user,
                'code': token,
            })
            plain_message = strip_tags(html_message)
            
            # Envoyer l'email
            send_mail(
                subject='Votre code de vérification - Cimetière',
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
            )
            
            logger.info(f"MFA_CODE_SENT: user={user.email}")
            return True
            
        except Exception as e:
            logger.error(f"MFA_CODE_FAILED: user={user.email}, error={str(e)}")
            return False
    
    @staticmethod
    def verify_mfa_code(user: User, code: str, request=None) -> bool:
        """
        Vérifie le code MFA fourni par l'utilisateur.
        
        Args:
            user: L'utilisateur à vérifier
            code: Le code MFA fourni
            request: La requête HTTP (optionnel, pour nettoyer la session)
        
        Returns:
            bool: True si le code est valide
        """
        try:
            # Vérifier avec la clé secrète
            if user.verify_mfa_token(code):
                user.mfa_verified = True
                user.save(update_fields=['mfa_verified'])
                
                # Nettoyer la session
                if request:
                    keys_to_delete = ['pre_mfa_user_id', 'mfa_token']
                    for key in keys_to_delete:
                        if key in request.session:
                            del request.session[key]
                
                logger.info(f"MFA_VERIFIED: user={user.email}")
                return True
            
            # Vérifier avec le token stocké en session
            if request:
                expected_token = request.session.get('mfa_token')
                if expected_token and code == expected_token:
                    user.mfa_verified = True
                    user.save(update_fields=['mfa_verified'])
                    
                    # Nettoyer la session
                    keys_to_delete = ['pre_mfa_user_id', 'mfa_token']
                    for key in keys_to_delete:
                        if key in request.session:
                            del request.session[key]
                    
                    logger.info(f"MFA_VERIFIED_SESSION: user={user.email}")
                    return True
            
            logger.warning(f"MFA_FAILED: user={user.email}")
            return False
            
        except Exception as e:
            logger.error(f"MFA_VERIFY_ERROR: user={user.email}, error={str(e)}")
            return False
    
    @staticmethod
    def send_welcome_email(user: User) -> bool:
        """
        Envoie l'email de bienvenue à un nouvel utilisateur.
        
        Args:
            user: Le nouvel utilisateur
        
        Returns:
            bool: True si l'email a été envoyé avec succès
        """
        try:
            html_message = render_to_string('emails/welcome.html', {
                'user': user,
            })
            plain_message = strip_tags(html_message)
            
            send_mail(
                subject='Bienvenue sur la plateforme de gestion du cimetière',
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=True,
            )
            
            logger.info(f"WELCOME_EMAIL_SENT: user={user.email}")
            return True
            
        except Exception as e:
            logger.error(f"WELCOME_EMAIL_FAILED: user={user.email}, error={str(e)}")
            return False
    
    @staticmethod
    def log_user_action(user: User, action: str, details: Optional[Dict[str, Any]] = None, ip: Optional[str] = None):
        """
        Enregistre une action utilisateur dans l'audit log.
        
        Args:
            user: L'utilisateur qui a effectué l'action
            action: Le type d'action (LOGIN, LOGOUT, REGISTER, etc.)
            details: Détails supplémentaires (optionnel)
            ip: Adresse IP (optionnel)
        """
        log_data = {
            'action': action,
            'user_email': user.email,
            'user_id': user.id,
            'timestamp': datetime.now().isoformat(),
        }
        
        if ip:
            log_data['ip'] = ip
        
        if details:
            log_data['details'] = details
        
        logger.info(f"AUDIT: {log_data}")


class UserService:
    """Service de gestion des utilisateurs."""
    
    @staticmethod
    def create_client(
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        phone: str,
        national_id: str,
        address: str
    ) -> User:
        """
        Crée un nouveau client (citoyen).
        
        Args:
            email: Adresse email
            password: Mot de passe
            first_name: Prénom
            last_name: Nom
            phone: Téléphone
            national_id: Numéro d'identité nationale
            address: Adresse
        
        Returns:
            User: L'utilisateur créé
        
        Raises:
            ValueError: Si l'email ou le numéro d'identité existe déjà
        """
        # Vérifier les doublons
        if User.objects.filter(email=email).exists():
            raise ValueError("Cet email est déjà utilisé.")
        
        if User.objects.filter(national_id=national_id).exists():
            raise ValueError("Ce numéro d'identité est déjà utilisé.")
        
        # Créer l'utilisateur
        user = User.objects.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            national_id=national_id,
            address=address,
            role=User.Role.CLIENT,
            mfa_enabled=True,
        )
        
        # Envoyer l'email de bienvenue
        AuthService.send_welcome_email(user)
        
        logger.info(f"USER_CREATED: email={email}, role=CLIENT")
        
        return user
    
    @staticmethod
    def create_staff(
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        role: str,
        phone: str,
        employee_id: Optional[str] = None,
        assignment_zone: Optional[str] = None
    ) -> User:
        """
        Crée un nouveau membre du personnel (admin, agent, secrétaire).
        
        Args:
            email: Adresse email
            password: Mot de passe
            first_name: Prénom
            last_name: Nom
            role: Rôle (ADMIN, FIELD_AGENT, SECRETARY)
            phone: Téléphone
            employee_id: Matricule employé (optionnel)
            assignment_zone: Zone d'affectation (optionnel)
        
        Returns:
            User: L'utilisateur créé
        
        Raises:
            ValueError: Si l'email existe déjà
        """
        # Vérifier les doublons
        if User.objects.filter(email=email).exists():
            raise ValueError("Cet email est déjà utilisé.")
        
        # Créer l'utilisateur
        user = User.objects.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            role=role,
            employee_id=employee_id or '',
            assignment_zone=assignment_zone or '',
            mfa_enabled=True,
            is_staff=True,
        )
        
        logger.info(f"STAFF_CREATED: email={email}, role={role}")
        
        return user
    
    @staticmethod
    def update_user_profile(user: User, **kwargs) -> User:
        """
        Met à jour le profil d'un utilisateur.
        
        Args:
            user: L'utilisateur à mettre à jour
            **kwargs: Champs à mettre à jour
        
        Returns:
            User: L'utilisateur mis à jour
        """
        allowed_fields = ['first_name', 'last_name', 'phone', 'address']
        
        for field, value in kwargs.items():
            if field in allowed_fields and value is not None:
                setattr(user, field, value)
        
        user.save()
        
        logger.info(f"PROFILE_UPDATED: user={user.email}")
        
        return user
    
    @staticmethod
    def change_password(user: User, old_password: str, new_password: str) -> bool:
        """
        Change le mot de passe d'un utilisateur.
        
        Args:
            user: L'utilisateur
            old_password: Ancien mot de passe
            new_password: Nouveau mot de passe
        
        Returns:
            bool: True si le changement a réussi
        
        Raises:
            ValueError: Si l'ancien mot de passe est incorrect
        """
        if not user.check_password(old_password):
            raise ValueError("Ancien mot de passe incorrect.")
        
        if len(new_password) < 8:
            raise ValueError("Le nouveau mot de passe doit contenir au moins 8 caractères.")
        
        user.set_password(new_password)
        user.save()
        
        logger.info(f"PASSWORD_CHANGED: user={user.email}")
        
        return True
    
    @staticmethod
    def deactivate_user(user: User) -> User:
        """
        Désactive un utilisateur.
        
        Args:
            user: L'utilisateur à désactiver
        
        Returns:
            User: L'utilisateur désactivé
        """
        user.is_active = False
        user.save(update_fields=['is_active'])
        
        logger.info(f"USER_DEACTIVATED: user={user.email}")
        
        return user
    
    @staticmethod
    def activate_user(user: User) -> User:
        """
        Active un utilisateur.
        
        Args:
            user: L'utilisateur à activer
        
        Returns:
            User: L'utilisateur activé
        """
        user.is_active = True
        user.save(update_fields=['is_active'])
        
        logger.info(f"USER_ACTIVATED: user={user.email}")
        
        return user


class PermissionService:
    """Service de gestion des permissions RBAC."""
    
    @staticmethod
    def can_manage_caveaux(user: User) -> bool:
        """Vérifie si l'utilisateur peut gérer les caveaux."""
        return user.is_admin() or user.is_field_agent()
    
    @staticmethod
    def can_validate_reservations(user: User) -> bool:
        """Vérifie si l'utilisateur peut valider les réservations."""
        return user.is_admin() or user.is_secretary()
    
    @staticmethod
    def can_view_financial_stats(user: User) -> bool:
        """Vérifie si l'utilisateur peut voir les statistiques financières."""
        return user.is_admin()
    
    @staticmethod
    def can_manage_concessions(user: User) -> bool:
        """Vérifie si l'utilisateur peut gérer les concessions."""
        return user.is_admin() or user.is_secretary()
    
    @staticmethod
    def can_perform_exhumations(user: User) -> bool:
        """Vérifie si l'utilisateur peut gérer les exhumations."""
        return user.is_admin()
    
    @staticmethod
    def can_view_audit_logs(user: User) -> bool:
        """Vérifie si l'utilisateur peut voir les logs d'audit."""
        return user.is_admin()