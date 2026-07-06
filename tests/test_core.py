"""
Tests unitaires pour l'application core (zones, caveaux, concessions).
"""
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from apps.accounts.models import User
from apps.core.models import Zone, Caveau, Concession, Defunt, Inhumation
from apps.core.services import CaveauService, ConcessionService


class ZoneModelTest(TestCase):
    """Tests du modèle Zone."""
    
    def setUp(self):
        self.zone = Zone.objects.create(
            code='Z01',
            nom='Zone Nord',
            type_zone=Zone.TypeZone.SECTION,
            est_exploitable=True,
            superficie=Decimal('500.00')
        )
    
    def test_zone_creation(self):
        """Test de création d'une zone."""
        self.assertEqual(self.zone.code, 'Z01')
        self.assertEqual(self.zone.nom, 'Zone Nord')
        self.assertTrue(self.zone.est_exploitable)
    
    def test_zone_str(self):
        """Test de la représentation string."""
        self.assertEqual(str(self.zone), 'Zone Nord (Z01)')
    
    def test_calculer_capacite_theorique(self):
        """Test du calcul de la capacité théorique."""
        # Exemple basique : superficie / (longueur * largeur standard)
        # Supposons 2.5m x 1.2m = 3m² par caveau
        capacite = self.zone.calculer_capacite_theorique()
        self.assertGreater(capacite, 0)


class CaveauModelTest(TestCase):
    """Tests du modèle Caveau."""
    
    def setUp(self):
        self.zone = Zone.objects.create(
            code='Z01',
            nom='Zone Test',
            est_exploitable=True
        )
        self.caveau = Caveau.objects.create(
            code='C001',
            numero='1A',
            zone=self.zone,
            statut=Caveau.Statut.DISPONIBLE,
            prix_concession=Decimal('500.00')
        )
    
    def test_caveau_creation(self):
        """Test de création d'un caveau."""
        self.assertEqual(self.caveau.statut, Caveau.Statut.DISPONIBLE)
        self.assertTrue(self.caveau.est_reservable())
    
    def test_reserver_caveau(self):
        """Test de réservation d'un caveau."""
        self.caveau.reserver()
        self.assertEqual(self.caveau.statut, Caveau.Statut.RESERVE)
    
    def test_valider_reservation(self):
        """Test de validation d'une réservation."""
        self.caveau.reserver()
        self.caveau.valider_reservation()
        self.assertEqual(self.caveau.statut, Caveau.Statut.OCCUPE)
    
    def test_liberer_caveau(self):
        """Test de libération d'un caveau."""
        self.caveau.statut = Caveau.Statut.OCCUPE
        self.caveau.save()
        self.caveau.liberer()
        self.assertEqual(self.caveau.statut, Caveau.Statut.DISPONIBLE)
    
    def test_caveau_non_reservable_si_occupe(self):
        """Test qu'un caveau occupé n'est pas réservable."""
        self.caveau.statut = Caveau.Statut.OCCUPE
        self.caveau.save()
        self.assertFalse(self.caveau.est_reservable())
    
    def test_caveau_non_reservable_si_reserve(self):
        """Test qu'un caveau réservé n'est pas réservable."""
        self.caveau.statut = Caveau.Statut.RESERVE
        self.caveau.save()
        self.assertFalse(self.caveau.est_reservable())


class ConcessionModelTest(TestCase):
    """Tests du modèle Concession."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='client@test.com',
            password='pass123'
        )
        self.zone = Zone.objects.create(
            code='Z01',
            nom='Zone Test',
            est_exploitable=True
        )
        self.caveau = Caveau.objects.create(
            code='C001',
            numero='1A',
            zone=self.zone,
            statut=Caveau.Statut.DISPONIBLE
        )
        self.concession = Concession.objects.create(
            numero_contrat='CON-001',
            concessionnaire=self.user,
            caveau=self.caveau,
            type_concession=Concession.TypeConcession.TEMPORAIRE,
            duree_annees=10,
            date_debut=timezone.now().date(),
            date_signature=timezone.now().date(),
            statut=Concession.StatutConcession.ACTIVE,
            montant_total=Decimal('5000.00')
        )
    
    def test_concession_temporaire_calcule_date_fin(self):
        """Test que la date de fin est calculée pour une concession temporaire."""
        self.assertIsNotNone(self.concession.date_fin)
        attendu = self.concession.date_debut + timedelta(days=365 * 10)
        self.assertEqual(self.concession.date_fin, attendu)
    
    def test_jours_restants(self):
        """Test du calcul des jours restants."""
        days = self.concession.jours_restants()
        self.assertGreater(days, 0)
    
    def test_concession_perpetuelle(self):
        """Test d'une concession perpétuelle."""
        perp = Concession.objects.create(
            numero_contrat='CON-002',
            concessionnaire=self.user,
            caveau=Caveau.objects.create(
                code='C002',
                numero='2A',
                zone=self.zone,
                statut=Caveau.Statut.DISPONIBLE
            ),
            type_concession=Concession.TypeConcession.PERPETUELLE,
            date_debut=timezone.now().date(),
            date_signature=timezone.now().date(),
            statut=Concession.StatutConcession.ACTIVE
        )
        self.assertIsNone(perp.date_fin)
        self.assertTrue(perp.est_active())
    
    def test_est_active(self):
        """Test de vérification si la concession est active."""
        self.assertTrue(self.concession.est_active())
        
        # Concession expirée
        self.concession.date_fin = timezone.now().date() - timedelta(days=1)
        self.concession.save()
        self.assertFalse(self.concession.est_active())


class CaveauServiceTest(TestCase):
    """Tests du service CaveauService."""
    
    def setUp(self):
        self.zone = Zone.objects.create(
            code='Z01',
            nom='Zone Service',
            est_exploitable=True
        )
        self.user = User.objects.create_user(
            email='agent@test.com',
            password='pass123',
            role=User.Role.FIELD_AGENT
        )
    
    def test_creer_caveau(self):
        """Test de création d'un caveau via le service."""
        caveau = CaveauService.creer_caveau(
            code='CS001',
            numero='S1',
            zone=self.zone,
            cree_par=self.user
        )
        self.assertEqual(caveau.statut, Caveau.Statut.DISPONIBLE)
        self.assertEqual(caveau.zone, self.zone)
    
    def test_duplicate_code_raises_error(self):
        """Test qu'un code dupliqué lève une erreur."""
        CaveauService.creer_caveau(code='DUP01', numero='D1', zone=self.zone)
        with self.assertRaises(ValueError):
            CaveauService.creer_caveau(code='DUP01', numero='D2', zone=self.zone)
    
    def test_reserver_caveau_non_disponible(self):
        """Test qu'on ne peut réserver qu'un caveau disponible."""
        caveau = CaveauService.creer_caveau(code='ND001', numero='ND1', zone=self.zone)
        caveau.statut = Caveau.Statut.OCCUPE
        caveau.save()
        with self.assertRaises(ValueError):
            CaveauService.reserver_caveau(caveau, self.user)


class ConcessionServiceTest(TestCase):
    """Tests du service ConcessionService."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='client2@test.com',
            password='pass123'
        )
        self.zone = Zone.objects.create(
            code='Z02',
            nom='Zone Service',
            est_exploitable=True
        )
        self.caveau = Caveau.objects.create(
            code='CS002',
            numero='S2',
            zone=self.zone,
            statut=Caveau.Statut.DISPONIBLE
        )
    
    def test_creer_concession(self):
        """Test de création d'une concession via le service."""
        concession = ConcessionService.creer_concession(
            concessionnaire=self.user,
            caveau=self.caveau,
            type_concession=Concession.TypeConcession.TEMPORAIRE,
            duree_annees=5,
            montant_total=Decimal('2500.00'),
            cree_par=self.user
        )
        self.assertEqual(concession.statut, Concession.StatutConcession.ACTIVE)
        self.assertEqual(self.caveau.statut, Caveau.Statut.RESERVE)
    
    def test_get_concessions_expiring_soon(self):
        """Test de récupération des concessions expirant bientôt."""
        # Créer une concession qui expire dans 30 jours
        date_debut = timezone.now().date() - timedelta(days=365 * 10 - 30)
        concession_expiring = Concession.objects.create(
            numero_contrat='CON-EXP',
            concessionnaire=self.user,
            caveau=Caveau.objects.create(
                code='EXP01',
                numero='E1',
                zone=self.zone,
                statut=Caveau.Statut.DISPONIBLE
            ),
            type_concession=Concession.TypeConcession.TEMPORAIRE,
            duree_annees=10,
            date_debut=date_debut,
            date_signature=date_debut,
            statut=Concession.StatutConcession.ACTIVE,
            montant_total=Decimal('5000.00')
        )
        
        expiring = ConcessionService.get_concessions_expiring_soon(jours=90)
        self.assertIn(concession_expiring, expiring)