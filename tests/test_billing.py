"""
Tests unitaires pour l'application billing (factures, paiements, transactions).
"""
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from apps.accounts.models import User
from apps.core.models import Zone, Caveau, Concession
from apps.billing.models import Facture, Paiement, TransactionFinanciere
from apps.billing.services import FactureService, PaiementService, StatistiquesFinancieresService


class FactureModelTest(TestCase):
    """Tests du modèle Facture."""
    
    def setUp(self):
        """Configuration initiale."""
        self.user = User.objects.create_user(
            email='client@test.com',
            password='TestPass123!',
            first_name='Jean',
            last_name='Dupont'
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
            statut=Caveau.Statut.DISPONIBLE,
            prix_concession=Decimal('500.00')
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
        self.facture = Facture.objects.create(
            numero_facture='FACT-20260101-0001',
            concession=self.concession,
            client=self.user,
            montant_ht=Decimal('5000.00'),
            taux_tva=Decimal('16.00'),
            date_emission=timezone.now().date(),
            date_echeance=timezone.now().date() + timedelta(days=30),
            statut=Facture.StatutFacture.EMISE,
            description='Test facture'
        )
    
    def test_facture_creation(self):
        """Test de création d'une facture."""
        self.assertEqual(self.facture.montant_ht, Decimal('5000.00'))
        self.assertEqual(self.facture.statut, Facture.StatutFacture.EMISE)
    
    def test_calcul_tva(self):
        """Test du calcul automatique de la TVA."""
        expected_tva = Decimal('5000.00') * Decimal('16.00') / Decimal('100')
        self.assertEqual(self.facture.montant_tva, expected_tva)
    
    def test_calcul_montant_total(self):
        """Test du calcul du montant total TTC."""
        expected_total = self.facture.montant_ht + self.facture.montant_tva
        self.assertEqual(self.facture.montant_total, expected_total)
    
    def test_est_payee(self):
        """Test de vérification si la facture est payée."""
        self.assertFalse(self.facture.est_payee())
        
        # Payer intégralement
        self.facture.montant_paye = self.facture.montant_total
        self.facture.save()
        self.assertTrue(self.facture.est_payee())
    
    def test_est_en_retard(self):
        """Test de vérification si la facture est en retard."""
        self.assertFalse(self.facture.est_en_retard())
        
        # Simuler une facture en retard
        self.facture.date_echeance = timezone.now().date() - timedelta(days=5)
        self.facture.save()
        self.assertTrue(self.facture.est_en_retard())
    
    def test_jours_retard(self):
        """Test du calcul des jours de retard."""
        self.assertEqual(self.facture.jours_retard(), 0)
        
        # Simuler une facture en retard
        self.facture.date_echeance = timezone.now().date() - timedelta(days=10)
        self.facture.save()
        self.assertEqual(self.facture.jours_retard(), 10)
    
    def test_annuler_facture_payee_echoue(self):
        """Test qu'on ne peut pas annuler une facture payée."""
        self.facture.montant_paye = self.facture.montant_total
        self.facture.statut = Facture.StatutFacture.PAYEE
        self.facture.save()
        
        with self.assertRaises(ValueError):
            self.facture.annuler('Test', self.user)


class PaiementModelTest(TestCase):
    """Tests du modèle Paiement."""
    
    def setUp(self):
        """Configuration initiale."""
        self.user = User.objects.create_user(
            email='client@test.com',
            password='TestPass123!'
        )
        self.zone = Zone.objects.create(code='Z01', nom='Zone Test', est_exploitable=True)
        self.caveau = Caveau.objects.create(
            code='C001', numero='1A', zone=self.zone,
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
        self.facture = Facture.objects.create(
            numero_facture='FACT-20260101-0001',
            concession=self.concession,
            client=self.user,
            montant_ht=Decimal('5000.00'),
            taux_tva=Decimal('16.00'),
            date_emission=timezone.now().date(),
            date_echeance=timezone.now().date() + timedelta(days=30),
            statut=Facture.StatutFacture.EMISE
        )
    
    def test_creer_paiement(self):
        """Test de création d'un paiement."""
        paiement = Paiement.objects.create(
            facture=self.facture,
            client=self.user,
            montant=Decimal('1000.00'),
            mode_paiement=Paiement.ModePaiement.MOBILE_MONEY,
            statut=Paiement.StatutPaiement.VALIDE
        )
        self.assertEqual(paiement.montant, Decimal('1000.00'))
        self.assertEqual(paiement.statut, Paiement.StatutPaiement.VALIDE)
    
    def test_valider_paiement(self):
        """Test de validation d'un paiement."""
        paiement = Paiement.objects.create(
            facture=self.facture,
            client=self.user,
            montant=Decimal('1000.00'),
            mode_paiement=Paiement.ModePaiement.ESPECES,
            statut=Paiement.StatutPaiement.EN_ATTENTE
        )
        
        admin = User.objects.create_user(
            email='admin@test.com',
            password='AdminPass123!',
            role=User.Role.ADMIN
        )
        
        paiement.valider(admin)
        self.assertEqual(paiement.statut, Paiement.StatutPaiement.VALIDE)
        self.assertIsNotNone(paiement.date_validation)
        self.assertEqual(paiement.valide_par, admin)
    
    def test_refuser_paiement(self):
        """Test de refus d'un paiement."""
        paiement = Paiement.objects.create(
            facture=self.facture,
            client=self.user,
            montant=Decimal('1000.00'),
            mode_paiement=Paiement.ModePaiement.ESPECES,
            statut=Paiement.StatutPaiement.EN_ATTENTE
        )
        
        admin = User.objects.create_user(
            email='admin@test.com',
            password='AdminPass123!',
            role=User.Role.ADMIN
        )
        
        paiement.refuser('Motif de refus', admin)
        self.assertEqual(paiement.statut, Paiement.StatutPaiement.REFUSE)


class FactureServiceTest(TestCase):
    """Tests du service FactureService."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='client@test.com',
            password='TestPass123!'
        )
        self.zone = Zone.objects.create(code='Z01', nom='Zone Test', est_exploitable=True)
        self.caveau = Caveau.objects.create(
            code='C001', numero='1A', zone=self.zone,
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
    
    def test_creer_facture(self):
        """Test de création d'une facture via le service."""
        facture = FactureService.creer_facture(
            concession=self.concession,
            client=self.user,
            montant_ht=Decimal('5000.00'),
            taux_tva=Decimal('16.00')
        )
        
        self.assertIsNotNone(facture.id)
        self.assertEqual(facture.montant_ht, Decimal('5000.00'))
        self.assertEqual(facture.statut, Facture.StatutFacture.BROUILLON)
        self.assertTrue(facture.numero_facture.startswith('FACT-'))
    
    def test_generer_numero_facture_unique(self):
        """Test que les numéros de facture sont uniques."""
        f1 = FactureService.creer_facture(
            concession=self.concession,
            client=self.user,
            montant_ht=Decimal('1000.00')
        )
        f2 = FactureService.creer_facture(
            concession=self.concession,
            client=self.user,
            montant_ht=Decimal('2000.00')
        )
        
        self.assertNotEqual(f1.numero_facture, f2.numero_facture)
    
    def test_emettre_facture(self):
        """Test d'émission d'une facture."""
        facture = FactureService.creer_facture(
            concession=self.concession,
            client=self.user,
            montant_ht=Decimal('5000.00')
        )
        
        admin = User.objects.create_user(
            email='admin@test.com',
            password='AdminPass123!',
            role=User.Role.ADMIN
        )
        
        FactureService.emettre_facture(facture, admin)
        
        facture.refresh_from_db()
        self.assertEqual(facture.statut, Facture.StatutFacture.EMISE)
    
    def test_emettre_facture_non_brouillon_echoue(self):
        """Test qu'on ne peut émettre qu'une facture en brouillon."""
        facture = FactureService.creer_facture(
            concession=self.concession,
            client=self.user,
            montant_ht=Decimal('5000.00')
        )
        facture.statut = Facture.StatutFacture.EMISE
        facture.save()
        
        admin = User.objects.create_user(
            email='admin@test.com',
            password='AdminPass123!',
            role=User.Role.ADMIN
        )
        
        with self.assertRaises(ValueError):
            FactureService.emettre_facture(facture, admin)
    
    def test_get_factures_en_retard(self):
        """Test de récupération des factures en retard."""
        facture = FactureService.creer_facture(
            concession=self.concession,
            client=self.user,
            montant_ht=Decimal('5000.00')
        )
        facture.statut = Facture.StatutFacture.EMISE
        facture.date_echeance = timezone.now().date() - timedelta(days=5)
        facture.save()
        
        factures_retard = FactureService.get_factures_en_retard()
        self.assertIn(facture, factures_retard)


class PaiementServiceTest(TestCase):
    """Tests du service PaiementService."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='client@test.com',
            password='TestPass123!'
        )
        self.admin = User.objects.create_user(
            email='admin@test.com',
            password='AdminPass123!',
            role=User.Role.ADMIN
        )
        self.zone = Zone.objects.create(code='Z01', nom='Zone Test', est_exploitable=True)
        self.caveau = Caveau.objects.create(
            code='C001', numero='1A', zone=self.zone,
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
        self.facture = Facture.objects.create(
            numero_facture='FACT-20260101-0001',
            concession=self.concession,
            client=self.user,
            montant_ht=Decimal('5000.00'),
            taux_tva=Decimal('16.00'),
            date_emission=timezone.now().date(),
            date_echeance=timezone.now().date() + timedelta(days=30),
            statut=Facture.StatutFacture.EMISE
        )
    
    def test_enregistrer_paiement(self):
        """Test d'enregistrement d'un paiement."""
        paiement = PaiementService.enregistrer_paiement(
            facture=self.facture,
            montant=Decimal('1000.00'),
            mode_paiement=Paiement.ModePaiement.MOBILE_MONEY
        )
        
        self.assertIsNotNone(paiement.id)
        self.assertEqual(paiement.montant, Decimal('1000.00'))
        self.assertEqual(paiement.statut, Paiement.StatutPaiement.EN_ATTENTE)
    
    def test_enregistrer_paiement_auto_valide(self):
        """Test d'enregistrement avec auto-validation."""
        paiement = PaiementService.enregistrer_paiement(
            facture=self.facture,
            montant=Decimal('1000.00'),
            mode_paiement=Paiement.ModePaiement.MOBILE_MONEY,
            auto_valider=True,
            valide_par=self.admin
        )
        
        self.assertEqual(paiement.statut, Paiement.StatutPaiement.VALIDE)
        
        # Vérifier que la facture a été mise à jour
        self.facture.refresh_from_db()
        self.assertEqual(self.facture.montant_paye, Decimal('1000.00'))
    
    def test_enregistrer_paiement_trop_eleve_echoue(self):
        """Test qu'un paiement ne peut pas dépasser le montant restant."""
        with self.assertRaises(ValueError):
            PaiementService.enregistrer_paiement(
                facture=self.facture,
                montant=Decimal('99999.00'),  # Trop élevé
                mode_paiement=Paiement.ModePaiement.ESPECES
            )
    
    def test_enregistrer_paiement_facture_annulee_echoue(self):
        """Test qu'on ne peut pas payer une facture annulée."""
        self.facture.statut = Facture.StatutFacture.ANNULEE
        self.facture.save()
        
        with self.assertRaises(ValueError):
            PaiementService.enregistrer_paiement(
                facture=self.facture,
                montant=Decimal('1000.00'),
                mode_paiement=Paiement.ModePaiement.ESPECES
            )
    
    def test_valider_paiement(self):
        """Test de validation d'un paiement."""
        paiement = Paiement.objects.create(
            facture=self.facture,
            client=self.user,
            montant=Decimal('1000.00'),
            mode_paiement=Paiement.ModePaiement.ESPECES,
            statut=Paiement.StatutPaiement.EN_ATTENTE
        )
        
        PaiementService.valider_paiement(paiement, self.admin)
        
        paiement.refresh_from_db()
        self.assertEqual(paiement.statut, Paiement.StatutPaiement.VALIDE)
        
        self.facture.refresh_from_db()
        self.assertEqual(self.facture.montant_paye, Decimal('1000.00'))
    
    def test_transaction_financiere_creee(self):
        """Test qu'une transaction financière est créée lors du paiement."""
        paiement = PaiementService.enregistrer_paiement(
            facture=self.facture,
            montant=Decimal('1000.00'),
            mode_paiement=Paiement.ModePaiement.MOBILE_MONEY,
            auto_valider=True,
            valide_par=self.admin
        )
        
        transactions = TransactionFinanciere.objects.filter(paiement=paiement)
        self.assertEqual(transactions.count(), 1)
        self.assertEqual(transactions.first().type_transaction, TransactionFinanciere.TypeTransaction.PAIEMENT_RECUE)


class StatistiquesFinancieresServiceTest(TestCase):
    """Tests du service de statistiques financières."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='client@test.com',
            password='TestPass123!'
        )
        self.zone = Zone.objects.create(code='Z01', nom='Zone Test', est_exploitable=True)
        self.caveau = Caveau.objects.create(
            code='C001', numero='1A', zone=self.zone,
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
    
    def test_get_statistiques_globales(self):
        """Test du calcul des statistiques globales."""
        # Créer quelques factures
        FactureService.creer_facture(
            concession=self.concession,
            client=self.user,
            montant_ht=Decimal('5000.00')
        )
        
        stats = StatistiquesFinancieresService.get_statistiques_globales()
        
        self.assertIn('total_factures', stats)
        self.assertIn('factures_payees', stats)
        self.assertIn('revenus_mois', stats)
        self.assertIn('paiements_par_mode', stats)
    
    def test_get_statistiques_client(self):
        """Test du calcul des statistiques d'un client."""
        FactureService.creer_facture(
            concession=self.concession,
            client=self.user,
            montant_ht=Decimal('5000.00')
        )
        
        stats = StatistiquesFinancieresService.get_statistiques_client(self.user)
        
        self.assertIn('total_factures', stats)
        self.assertEqual(stats['total_factures'], 1)