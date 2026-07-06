"""
Tests unitaires pour l'application accounts (utilisateurs, authentification, MFA).
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from apps.accounts.models import User, MFACode
from apps.accounts.services import PermissionService, MFAService


class UserModelTest(TestCase):
    """Tests du modèle User."""
    
    def setUp(self):
        """Configuration initiale."""
        self.user_data = {
            'email': 'test@example.com',
            'password': 'TestPass123!',
            'first_name': 'Jean',
            'last_name': 'Dupont',
            'phone': '+243123456789',
            'role': User.Role.CLIENT,
        }
        self.user = User.objects.create_user(**self.user_data)
    
    def test_create_user(self):
        """Test de création d'un utilisateur."""
        self.assertEqual(self.user.email, 'test@example.com')
        self.assertEqual(self.user.first_name, 'Jean')
        self.assertEqual(self.user.role, User.Role.CLIENT)
        self.assertTrue(self.user.is_active)
        self.assertFalse(self.user.is_staff)
        self.assertFalse(self.user.is_superuser)
    
    def test_create_superuser(self):
        """Test de création d'un superutilisateur."""
        admin = User.objects.create_superuser(
            email='admin@example.com',
            password='AdminPass123!',
            first_name='Admin',
            last_name='User',
        )
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
        self.assertEqual(admin.role, User.Role.ADMIN)
    
    def test_user_str(self):
        """Test de la représentation string."""
        self.assertEqual(str(self.user), 'test@example.com')
    
    def test_user_full_name(self):
        """Test du nom complet."""
        self.assertEqual(self.user.get_full_name(), 'Jean Dupont')
    
    def test_user_short_name(self):
        """Test du nom court."""
        self.assertEqual(self.user.get_short_name(), 'Jean')
    
    def test_is_admin(self):
        """Test de la vérification du rôle admin."""
        self.assertFalse(self.user.is_admin())
        
        admin = User.objects.create_user(
            email='admin@example.com',
            password='AdminPass123!',
            role=User.Role.ADMIN,
        )
        self.assertTrue(admin.is_admin())
    
    def test_is_client(self):
        """Test de la vérification du rôle client."""
        self.assertTrue(self.user.is_client())
    
    def test_email_unique(self):
        """Test que l'email doit être unique."""
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            User.objects.create_user(
                email='test@example.com',  # Même email
                password='AnotherPass123!',
            )


class MFACodeModelTest(TestCase):
    """Tests du modèle MFACode."""
    
    def setUp(self):
        """Configuration initiale."""
        self.user = User.objects.create_user(
            email='test@example.com',
            password='TestPass123!',
        )
    
    def test_create_mfa_code(self):
        """Test de création d'un code MFA."""
        mfa_code = MFACode.objects.create(
            user=self.user,
            code='123456',
        )
        self.assertEqual(mfa_code.code, '123456')
        self.assertFalse(mfa_code.is_used)
        self.assertFalse(mfa_code.is_expired())
    
    def test_mfa_code_expiration(self):
        """Test de l'expiration du code MFA."""
        mfa_code = MFACode.objects.create(
            user=self.user,
            code='123456',
        )
        # Le code ne devrait pas être expiré immédiatement
        self.assertFalse(mfa_code.is_expired())
        
        # Simuler un code expiré (modifier la date de création)
        mfa_code.date_creation = timezone.now() - timedelta(minutes=10)
        mfa_code.save()
        self.assertTrue(mfa_code.is_expired())
    
    def test_mfa_code_mark_used(self):
        """Test de marquage d'un code comme utilisé."""
        mfa_code = MFACode.objects.create(
            user=self.user,
            code='123456',
        )
        mfa_code.mark_used()
        self.assertTrue(mfa_code.is_used)


class MFAServiceTest(TestCase):
    """Tests du service MFA."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='TestPass123!',
        )
    
    def test_generate_code(self):
        """Test de génération d'un code MFA."""
        code = MFAService.generate_code(self.user)
        self.assertEqual(len(code), 6)
        self.assertTrue(code.isdigit())
    
    def test_verify_valid_code(self):
        """Test de vérification d'un code valide."""
        code = MFAService.generate_code(self.user)
        result = MFAService.verify_code(self.user, code)
        self.assertTrue(result)
    
    def test_verify_invalid_code(self):
        """Test de vérification d'un code invalide."""
        result = MFAService.verify_code(self.user, '000000')
        self.assertFalse(result)
    
    def test_verify_expired_code(self):
        """Test de vérification d'un code expiré."""
        mfa_code = MFACode.objects.create(
            user=self.user,
            code='123456',
        )
        mfa_code.date_creation = timezone.now() - timedelta(minutes=10)
        mfa_code.save()
        
        result = MFAService.verify_code(self.user, '123456')
        self.assertFalse(result)


class PermissionServiceTest(TestCase):
    """Tests du service de permissions."""
    
    def setUp(self):
        """Configuration initiale."""
        self.admin = User.objects.create_user(
            email='admin@example.com',
            password='AdminPass123!',
            role=User.Role.ADMIN,
        )
        self.agent = User.objects.create_user(
            email='agent@example.com',
            password='AgentPass123!',
            role=User.Role.FIELD_AGENT,
        )
        self.secretary = User.objects.create_user(
            email='secretary@example.com',
            password='SecretaryPass123!',
            role=User.Role.SECRETARY,
        )
        self.client_user = User.objects.create_user(
            email='client@example.com',
            password='ClientPass123!',
            role=User.Role.CLIENT,
        )
    
    def test_admin_can_manage_caveaux(self):
        """Test que l'admin peut gérer les caveaux."""
        self.assertTrue(PermissionService.can_manage_caveaux(self.admin))
    
    def test_agent_can_manage_caveaux(self):
        """Test que l'agent peut gérer les caveaux."""
        self.assertTrue(PermissionService.can_manage_caveaux(self.agent))
    
    def test_client_cannot_manage_caveaux(self):
        """Test que le client ne peut pas gérer les caveaux."""
        self.assertFalse(PermissionService.can_manage_caveaux(self.client_user))
    
    def test_admin_can_view_financial_stats(self):
        """Test que l'admin peut voir les stats financières."""
        self.assertTrue(PermissionService.can_view_financial_stats(self.admin))
    
    def test_client_cannot_view_financial_stats(self):
        """Test que le client ne peut pas voir les stats financières globales."""
        self.assertFalse(PermissionService.can_view_financial_stats(self.client_user))
    
    def test_secretary_can_validate_reservations(self):
        """Test que le secrétariat peut valider les réservations."""
        self.assertTrue(PermissionService.can_validate_reservations(self.secretary))
    
    def test_admin_can_validate_reservations(self):
        """Test que l'admin peut valider les réservations."""
        self.assertTrue(PermissionService.can_validate_reservations(self.admin))
    
    def test_client_cannot_validate_reservations(self):
        """Test que le client ne peut pas valider les réservations."""
        self.assertFalse(PermissionService.can_validate_reservations(self.client_user))