"""
Script de vérification de conformité au CDC.
Teste tous les workflows critiques avec données isolées.
"""
import os
import sys
import django
from pathlib import Path
from datetime import timedelta

# Ajouter le répertoire racine au path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

# Configurer Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.core.models import Zone, Caveau, Defunt, Concession, Inhumation
from apps.billing.models import Facture, Paiement
from apps.portal.models import DemandeReservation
from apps.notifications.models import Notification, EmailLog
from decimal import Decimal
from django.utils import timezone

User = get_user_model()


class TestConformiteCDC:
    """Tests de conformité au CDC."""
    
    def __init__(self):
        self.admin = None
        self.client_user = None
        self.zone = None
        self.caveau = None
        self.created_objects = []
    
    def setUp(self):
        """Configuration initiale avec données isolées."""
        print("\n" + "="*60)
        print("CONFIGURATION DES DONNÉES DE TEST")
        print("="*60)
        
        # Créer un utilisateur admin unique
        admin_email = f'admin_test_{timezone.now().strftime("%Y%m%d%H%M%S")}@test.com'
        self.admin = User.objects.create_user(
            email=admin_email,
            password='testpass123',
            first_name='Admin',
            last_name='Test',
            role=User.Role.ADMIN
        )
        self.created_objects.append(('user', self.admin))
        print(f"   ✓ Admin créé : {admin_email}")
        
        # Créer un utilisateur client unique
        client_email = f'client_test_{timezone.now().strftime("%Y%m%d%H%M%S")}@test.com'
        self.client_user = User.objects.create_user(
            email=client_email,
            password='testpass123',
            first_name='Client',
            last_name='Test',
            role=User.Role.CLIENT
        )
        self.created_objects.append(('user', self.client_user))
        print(f"   ✓ Client créé : {client_email}")
        
        # Créer une zone unique
        zone_code = f'TEST-{timezone.now().strftime("%Y%m%d%H%M%S")}'
        self.zone = Zone.objects.create(
            code=zone_code,
            nom=f'Zone Test {zone_code}',
            type_zone=Zone.TypeZone.SECTION
        )
        self.created_objects.append(('zone', self.zone))
        print(f"   ✓ Zone créée : {zone_code}")
        
        # Créer un caveau unique
        caveau_code = f'TEST-{timezone.now().strftime("%Y%m%d%H%M%S")}'
        self.caveau = Caveau.objects.create(
            code=caveau_code,
            zone=self.zone,
            statut=Caveau.Statut.DISPONIBLE,
            prix_concession=Decimal('50000')
        )
        self.created_objects.append(('caveau', self.caveau))
        print(f"   ✓ Caveau créé : {caveau_code}")
        
        print("\n✓ Configuration terminée\n")
    
    def tearDown(self):
        """Nettoyage des données de test."""
        print("\n" + "="*60)
        print("NETTOYAGE DES DONNÉES DE TEST")
        print("="*60)
        
        deleted_count = 0
        for obj_type, obj in reversed(self.created_objects):
            try:
                obj.delete()
                deleted_count += 1
            except Exception as e:
                print(f"   ⚠ Impossible de supprimer {obj_type} {obj.id}: {e}")
        
        print(f"   ✓ {deleted_count} objet(s) supprimé(s)")
        print("\n✓ Nettoyage terminé\n")
    
    def test_workflow_reservation_complet(self):
        """Test du workflow complet : réservation → validation → facture → paiement."""
        print("\n" + "="*60)
        print("TEST 1 : Workflow de réservation complet")
        print("="*60)
        
        # 1. Créer une demande de réservation
        print("1. Création de la demande de réservation...")
        reservation = DemandeReservation.objects.create(
            client=self.client_user,
            caveau=self.caveau,
            defunt_nom='TestDefunt',
            defunt_prenom='TestPrenom',
            date_deces='2026-01-01',
            lien_parente='Fils',
            telephone_contact='0612345678',
            statut=DemandeReservation.Statut.EN_ATTENTE
        )
        self.created_objects.append(('reservation', reservation))
        print(f"   ✓ Demande créée : #{reservation.id}")
        
        # 2. Valider la demande
        print("2. Validation de la demande...")
        reservation.valider(self.admin)
        assert reservation.statut == DemandeReservation.Statut.VALIDEE, "Statut devrait être VALIDEE"
        print(f"   ✓ Demande validée")
        
        # 3. Vérifier que le caveau est réservé
        print("3. Vérification du statut du caveau...")
        self.caveau.refresh_from_db()
        assert self.caveau.statut == 'RESERVE', f"Caveau devrait être RESERVE, pas {self.caveau.statut}"
        print(f"   ✓ Caveau réservé")
        
        # 4. Créer une concession
        print("4. Création de la concession...")
        concession = Concession.objects.create(
            numero_contrat=f'CONC-TEST-{reservation.id:05d}',
            concessionnaire=self.client_user,
            caveau=self.caveau,
            type_concession=Concession.TypeConcession.TEMPORAIRE,
            duree_annees=30,
            date_debut=timezone.now().date(),
            montant_total=Decimal('50000'),
            statut=Concession.StatutConcession.ACTIVE
        )
        self.created_objects.append(('concession', concession))
        print(f"   ✓ Concession créée : {concession.numero_contrat}")
        
        # 5. Créer une facture
        print("5. Création de la facture...")
        facture = Facture.objects.create(
            numero_facture=f'FACT-TEST-{reservation.id:05d}',
            concession=concession,
            client=self.client_user,
            montant_ht=Decimal('50000'),
            taux_tva=Decimal('0'),
            date_emission=timezone.now().date(),
            date_echeance=timezone.now().date() + timedelta(days=30),
            statut=Facture.StatutFacture.EMISE
        )
        self.created_objects.append(('facture', facture))
        print(f"   ✓ Facture créée : {facture.numero_facture}")
        
        # 6. Créer un paiement
        print("6. Création du paiement...")
        paiement = Paiement.objects.create(
            facture=facture,
            client=self.client_user,
            montant=Decimal('50000'),
            mode_paiement=Paiement.ModePaiement.MOBILE_MONEY,
            statut=Paiement.StatutPaiement.EN_ATTENTE
        )
        self.created_objects.append(('paiement', paiement))
        print(f"   ✓ Paiement créé : {paiement.numero_transaction}")
        
        # 7. Valider le paiement
        print("7. Validation du paiement...")
        paiement.valider(self.admin)
        assert paiement.statut == Paiement.StatutPaiement.VALIDE, "Paiement devrait être VALIDE"
        print(f"   ✓ Paiement validé")
        
        # 8. Vérifier que la facture est payée
        print("8. Vérification du statut de la facture...")
        facture.refresh_from_db()
        assert facture.statut == Facture.StatutFacture.PAYEE, f"Facture devrait être PAYEE, pas {facture.statut}"
        print(f"   ✓ Facture payée")
        
        # 9. Vérifier que le caveau est occupé
        print("9. Vérification du statut du caveau...")
        self.caveau.refresh_from_db()
        assert self.caveau.statut == 'OCCUPE', f"Caveau devrait être OCCUPE, pas {self.caveau.statut}"
        print(f"   ✓ Caveau occupé")
        
        print("\n✓ TEST 1 RÉUSSI : Workflow complet fonctionnel")
        return True
    
    def test_mfa(self):
        """Test du système MFA."""
        print("\n" + "="*60)
        print("TEST 2 : Système MFA")
        print("="*60)
        
        # 1. Générer une clé MFA
        print("1. Génération de la clé MFA...")
        secret = self.admin.generate_mfa_secret()
        assert secret is not None, "La clé MFA ne devrait pas être None"
        print(f"   ✓ Clé MFA générée")
        
        # 2. Générer un token
        print("2. Génération d'un token...")
        token = self.admin.get_mfa_token()
        assert len(token) == 6, f"Le token devrait avoir 6 chiffres, pas {len(token)}"
        print(f"   ✓ Token généré : {token}")
        
        # 3. Vérifier le token
        print("3. Vérification du token...")
        is_valid = self.admin.verify_mfa_token(token)
        assert is_valid, "Le token devrait être valide"
        print(f"   ✓ Token vérifié")
        
        print("\n✓ TEST 2 RÉUSSI : MFA fonctionnel")
        return True
    
    def test_rbac(self):
        """Test du système RBAC."""
        print("\n" + "="*60)
        print("TEST 3 : Système RBAC")
        print("="*60)
        
        # 1. Vérifier les rôles
        print("1. Vérification des rôles...")
        assert self.admin.is_admin(), "Admin devrait être admin"
        assert self.client_user.is_client(), "Client devrait être client"
        print(f"   ✓ Rôles corrects")
        
        # 2. Vérifier les permissions
        print("2. Vérification des permissions...")
        assert self.admin.can_manage_caveaux(), "Admin devrait pouvoir gérer les caveaux"
        assert self.admin.can_validate_reservations(), "Admin devrait pouvoir valider les réservations"
        assert self.admin.can_view_financial_stats(), "Admin devrait pouvoir voir les stats financières"
        assert not self.client_user.can_manage_caveaux(), "Client ne devrait pas pouvoir gérer les caveaux"
        print(f"   ✓ Permissions correctes")
        
        print("\n✓ TEST 3 RÉUSSI : RBAC fonctionnel")
        return True
    
    def test_notifications(self):
        """Test du système de notifications."""
        print("\n" + "="*60)
        print("TEST 4 : Système de notifications")
        print("="*60)
        
        # 1. Créer une notification
        print("1. Création d'une notification...")
        notification = Notification.objects.create(
            utilisateur=self.client_user,
            titre='Test Notification',
            message='Ceci est un test de notification',
            type_notification=Notification.TypeNotification.INFO,
            priorite=Notification.Priorite.NORMALE
        )
        self.created_objects.append(('notification', notification))
        print(f"   ✓ Notification créée : #{notification.id}")
        
        # 2. Vérifier que la notification existe
        print("2. Vérification de la notification...")
        notif_count = Notification.objects.filter(utilisateur=self.client_user).count()
        assert notif_count > 0, "Il devrait y avoir au moins une notification"
        print(f"   ✓ Notification trouvée")
        
        print("\n✓ TEST 4 RÉUSSI : Notifications fonctionnelles")
        return True


def run_tests():
    """Exécute tous les tests de conformité."""
    print("\n" + "="*60)
    print("VÉRIFICATION DE CONFORMITÉ AU CDC")
    print("="*60)
    
    test = TestConformiteCDC()
    
    try:
        test.setUp()
    except Exception as e:
        print(f"\n✗ ERREUR DE CONFIGURATION : {e}")
        return 1
    
    results = []
    
    try:
        results.append(("Workflow complet", test.test_workflow_reservation_complet()))
    except Exception as e:
        print(f"\n✗ TEST 1 ÉCHOUÉ : {e}")
        import traceback
        traceback.print_exc()
        results.append(("Workflow complet", False))
    
    try:
        results.append(("MFA", test.test_mfa()))
    except Exception as e:
        print(f"\n✗ TEST 2 ÉCHOUÉ : {e}")
        import traceback
        traceback.print_exc()
        results.append(("MFA", False))
    
    try:
        results.append(("RBAC", test.test_rbac()))
    except Exception as e:
        print(f"\n✗ TEST 3 ÉCHOUÉ : {e}")
        import traceback
        traceback.print_exc()
        results.append(("RBAC", False))
    
    try:
        results.append(("Notifications", test.test_notifications()))
    except Exception as e:
        print(f"\n✗ TEST 4 ÉCHOUÉ : {e}")
        import traceback
        traceback.print_exc()
        results.append(("Notifications", False))
    
    # Nettoyage
    try:
        test.tearDown()
    except Exception as e:
        print(f"\n⚠ ERREUR DE NETTOYAGE : {e}")
    
    # Résumé
    print("\n" + "="*60)
    print("RÉSUMÉ DES TESTS")
    print("="*60)
    
    for name, success in results:
        status = "✓ RÉUSSI" if success else "✗ ÉCHOUÉ"
        print(f"{status} : {name}")
    
    total = len(results)
    passed = sum(1 for _, success in results if success)
    
    print("\n" + "="*60)
    print(f"RÉSULTAT FINAL : {passed}/{total} tests réussis")
    print("="*60)
    
    if passed == total:
        print("\n🎉 APPLICATION 100% CONFORME AU CDC ! 🎉\n")
        return 0
    else:
        print(f"\n⚠️ {total - passed} test(s) échoué(s). Veuillez corriger les problèmes.\n")
        return 1


if __name__ == '__main__':
    sys.exit(run_tests())