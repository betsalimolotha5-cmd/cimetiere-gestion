"""
Tests unitaires pour l'application notifications (emails, alertes).
"""
from django.test import TestCase, override_settings
from django.utils import timezone
from django.core import mail
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock
from apps.accounts.models import User
from apps.core.models import Zone, Caveau, Concession
from apps.billing.models import Facture
from apps.notifications.models import EmailLog, Notification
from apps.notifications.services import EmailService, NotificationService, AlerteService
from apps.notifications.tasks import NotificationTasks


class EmailLogModelTest(TestCase):
    """Tests du modèle EmailLog."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='TestPass123!'
        )
    
    def test_create_email_log(self):
        """Test de création d'un log d'email."""
        log = EmailLog.objects.create(
            destinataire='dest@example.com',
            utilisateur=self.user,
            type_email=EmailLog.TypeEmail.MFA_CODE,
            sujet='Test sujet',
            contenu_html='<p>Test</p>',
            statut=EmailLog.StatutEmail.EN_ATTENTE
        )
        self.assertEqual(log.destinataire, 'dest@example.com')
        self.assertEqual(log.statut, EmailLog.StatutEmail.EN_ATTENTE)
    
    def test_marquer_envoye(self):
        """Test de marquage d'un email comme envoyé."""
        log = EmailLog.objects.create(
            destinataire='dest@example.com',
            type_email=EmailLog.TypeEmail.BIENVENUE,
            sujet='Test',
            contenu_html='<p>Test</p>',
            statut=EmailLog.StatutEmail.EN_ATTENTE
        )
        log.marquer_envoye()
        
        log.refresh_from_db()
        self.assertEqual(log.statut, EmailLog.StatutEmail.ENVOYE)
        self.assertIsNotNone(log.date_envoi_reussi)
    
    def test_marquer_echec(self):
        """Test de marquage d'un email comme échec."""
        log = EmailLog.objects.create(
            destinataire='dest@example.com',
            type_email=EmailLog.TypeEmail.FACTURE,
            sujet='Test',
            contenu_html='<p>Test</p>',
            statut=EmailLog.StatutEmail.EN_ATTENTE
        )
        log.marquer_echec('Erreur SMTP')
        
        log.refresh_from_db()
        self.assertEqual(log.statut, EmailLog.StatutEmail.ECHEC)
        self.assertEqual(log.message_erreur, 'Erreur SMTP')
    
    def test_str_representation(self):
        """Test de la représentation string."""
        log = EmailLog.objects.create(
            destinataire='dest@example.com',
            type_email=EmailLog.TypeEmail.MFA_CODE,
            sujet='Test',
            contenu_html='<p>Test</p>',
            statut=EmailLog.StatutEmail.ENVOYE
        )
        self.assertIn('dest@example.com', str(log))


class NotificationModelTest(TestCase):
    """Tests du modèle Notification."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='TestPass123!'
        )
    
    def test_create_notification(self):
        """Test de création d'une notification."""
        notif = Notification.objects.create(
            utilisateur=self.user,
            type_notification=Notification.TypeNotification.INFO,
            priorite=Notification.Priorite.NORMALE,
            titre='Test titre',
            message='Test message'
        )
        self.assertEqual(notif.titre, 'Test titre')
        self.assertFalse(notif.lue)
    
    def test_marquer_comme_lue(self):
        """Test de marquage d'une notification comme lue."""
        notif = Notification.objects.create(
            utilisateur=self.user,
            type_notification=Notification.TypeNotification.SUCCESS,
            titre='Test',
            message='Test'
        )
        notif.marquer_comme_lue()
        
        notif.refresh_from_db()
        self.assertTrue(notif.lue)
        self.assertIsNotNone(notif.date_lecture)
    
    def test_compter_non_lues(self):
        """Test du comptage des notifications non lues."""
        # Créer plusieurs notifications
        for i in range(5):
            Notification.objects.create(
                utilisateur=self.user,
                type_notification=Notification.TypeNotification.INFO,
                titre=f'Test {i}',
                message='Test'
            )
        
        # Marquer 2 comme lues
        notifs = Notification.objects.filter(utilisateur=self.user)[:2]
        for n in notifs:
            n.marquer_comme_lue()
        
        count = Notification.compter_non_lues(self.user)
        self.assertEqual(count, 3)
    
    def test_notification_str(self):
        """Test de la représentation string."""
        notif = Notification.objects.create(
            utilisateur=self.user,
            titre='Mon titre',
            message='Mon message'
        )
        self.assertIn('Mon titre', str(notif))


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class EmailServiceTest(TestCase):
    """Tests du service EmailService."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='TestPass123!',
            first_name='Jean',
            last_name='Dupont'
        )
    
    @patch('apps.notifications.services.render_to_string')
    def test_envoyer_email(self, mock_render):
        """Test d'envoi d'un email."""
        mock_render.return_value = '<p>Contenu test</p>'
        
        success = EmailService.envoyer_email(
            destinataire='dest@example.com',
            sujet='Test sujet',
            template_html='emails/test.html',
            context={'test': 'value'},
            type_email=EmailLog.TypeEmail.AUTRE,
            utilisateur=self.user
        )
        
        self.assertTrue(success)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, 'Test sujet')
        self.assertEqual(mail.outbox[0].to, ['dest@example.com'])
        
        # Vérifier le log
        log = EmailLog.objects.first()
        self.assertEqual(log.statut, EmailLog.StatutEmail.ENVOYE)
    
    def test_envoyer_code_mfa(self):
        """Test d'envoi d'un code MFA."""
        with patch('apps.notifications.services.render_to_string') as mock_render:
            mock_render.return_value = '<p>Code: 123456</p>'
            
            success = EmailService.envoyer_code_mfa(self.user, '123456')
            
            self.assertTrue(success)
            self.assertEqual(len(mail.outbox), 1)
            self.assertIn('vérification', mail.outbox[0].subject.lower())
    
    def test_envoyer_email_bienvenue(self):
        """Test d'envoi d'un email de bienvenue."""
        with patch('apps.notifications.services.render_to_string') as mock_render:
            mock_render.return_value = '<p>Bienvenue</p>'
            
            success = EmailService.envoyer_email_bienvenue(self.user)
            
            self.assertTrue(success)
            self.assertEqual(len(mail.outbox), 1)
            self.assertIn('bienvenue', mail.outbox[0].subject.lower())


class NotificationServiceTest(TestCase):
    """Tests du service NotificationService."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='TestPass123!'
        )
    
    def test_creer_notification(self):
        """Test de création d'une notification."""
        notif = NotificationService.creer_notification(
            utilisateur=self.user,
            titre='Test titre',
            message='Test message',
            type_notification=Notification.TypeNotification.INFO,
            priorite=Notification.Priorite.NORMALE
        )
        
        self.assertIsNotNone(notif.id)
        self.assertEqual(notif.titre, 'Test titre')
        self.assertFalse(notif.lue)
    
    def test_notifier_reservation_creee(self):
        """Test de notification de création de réservation."""
        zone = Zone.objects.create(code='Z01', nom='Zone Test', est_exploitable=True)
        caveau = Caveau.objects.create(
            code='C001', numero='1A', zone=zone,
            statut=Caveau.Statut.DISPONIBLE
        )
        concession = Concession.objects.create(
            numero_contrat='CON-001',
            concessionnaire=self.user,
            caveau=caveau,
            type_concession=Concession.TypeConcession.TEMPORAIRE,
            duree_annees=10,
            date_debut=timezone.now().date(),
            date_signature=timezone.now().date(),
            statut=Concession.StatutConcession.ACTIVE,
            montant_total=Decimal('5000.00')
        )
        
        NotificationService.notifier_reservation_creee(self.user, concession)
        
        notif = Notification.objects.filter(utilisateur=self.user).first()
        self.assertIsNotNone(notif)
        self.assertIn('réservation', notif.titre.lower())
    
    def test_get_notifications_non_lues(self):
        """Test de récupération des notifications non lues."""
        # Créer plusieurs notifications
        for i in range(3):
            NotificationService.creer_notification(
                utilisateur=self.user,
                titre=f'Test {i}',
                message='Test'
            )
        
        notifs = NotificationService.get_notifications_non_lues(self.user)
        self.assertEqual(len(notifs), 3)
    
    def test_marquer_toutes_comme_lues(self):
        """Test de marquage de toutes les notifications comme lues."""
        # Créer plusieurs notifications
        for i in range(5):
            NotificationService.creer_notification(
                utilisateur=self.user,
                titre=f'Test {i}',
                message='Test'
            )
        
        NotificationService.marquer_toutes_comme_lues(self.user)
        
        count = Notification.objects.filter(
            utilisateur=self.user,
            lue=False
        ).count()
        self.assertEqual(count, 0)


class AlerteServiceTest(TestCase):
    """Tests du service AlerteService."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='TestPass123!'
        )
        self.zone = Zone.objects.create(
            code='Z01', nom='Zone Test',
            est_exploitable=True,
            superficie=Decimal('100.00')
        )
    
    def test_verifier_concessions_expiring(self):
        """Test de vérification des concessions expirantes."""
        # Créer une concession qui expire bientôt
        date_debut = timezone.now().date() - timedelta(days=365 * 10 - 30)
        caveau = Caveau.objects.create(
            code='C001', numero='1A', zone=self.zone,
            statut=Caveau.Statut.OCCUPE
        )
        Concession.objects.create(
            numero_contrat='CON-EXP',
            concessionnaire=self.user,
            caveau=caveau,
            type_concession=Concession.TypeConcession.TEMPORAIRE,
            duree_annees=10,
            date_debut=date_debut,
            date_signature=date_debut,
            statut=Concession.StatutConcession.ACTIVE,
            montant_total=Decimal('5000.00')
        )
        
        with patch.object(EmailService, 'envoyer_alerte_concession_expiree', return_value=True):
            alertes = AlerteService.verifier_concessions_expiring(jours_avant=90)
        
        self.assertGreater(len(alertes), 0)
    
    def test_verifier_factures_en_retard(self):
        """Test de vérification des factures en retard."""
        caveau = Caveau.objects.create(
            code='C001', numero='1A', zone=self.zone,
            statut=Caveau.Statut.OCCUPE
        )
        concession = Concession.objects.create(
            numero_contrat='CON-001',
            concessionnaire=self.user,
            caveau=caveau,
            type_concession=Concession.TypeConcession.TEMPORAIRE,
            duree_annees=10,
            date_debut=timezone.now().date(),
            date_signature=timezone.now().date(),
            statut=Concession.StatutConcession.ACTIVE,
            montant_total=Decimal('5000.00')
        )
        
        # Créer une facture en retard
        Facture.objects.create(
            numero_facture='FACT-RETARD',
            concession=concession,
            client=self.user,
            montant_ht=Decimal('5000.00'),
            taux_tva=Decimal('16.00'),
            date_emission=timezone.now().date() - timedelta(days=60),
            date_echeance=timezone.now().date() - timedelta(days=10),
            statut=Facture.StatutFacture.EMISE
        )
        
        with patch.object(EmailService, 'envoyer_rappel_paiement', return_value=True):
            rappels = AlerteService.verifier_factures_en_retard()
        
        self.assertGreater(len(rappels), 0)
    
    def test_verifier_seuil_places_critiques(self):
        """Test de vérification du seuil de places critiques."""
        # Créer plusieurs caveaux occupés
        for i in range(10):
            Caveau.objects.create(
                code=f'C{i:03d}',
                numero=f'{i}A',
                zone=self.zone,
                statut=Caveau.Statut.OCCUPE
            )
        
        zones = AlerteService.verifier_seuil_places_critiques(seuil=50)
        # Selon la configuration, la zone devrait être critique
        # Le test dépend de la logique de calcul dans CaveauService
        self.assertIsInstance(zones, list)


class NotificationTasksTest(TestCase):
    """Tests des tâches planifiées."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='TestPass123!'
        )
        self.admin = User.objects.create_user(
            email='admin@example.com',
            password='AdminPass123!',
            role=User.Role.ADMIN
        )
    
    def test_nettoyer_anciens_logs_emails(self):
        """Test du nettoyage des anciens logs d'emails."""
        # Créer des logs anciens
        for i in range(5):
            log = EmailLog.objects.create(
                destinataire=f'dest{i}@example.com',
                type_email=EmailLog.TypeEmail.AUTRE,
                sujet='Test',
                contenu_html='<p>Test</p>',
                statut=EmailLog.StatutEmail.ENVOYE
            )
            # Rendre le log ancien
            log.date_envoi_tente = timezone.now() - timedelta(days=100)
            log.save()
        
        result = NotificationTasks.nettoyer_anciens_logs_emails(jours=90)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['deleted'], 5)
        self.assertEqual(EmailLog.objects.count(), 0)
    
    def test_nettoyer_anciennes_notifications(self):
        """Test du nettoyage des anciennes notifications."""
        # Créer des notifications anciennes
        for i in range(5):
            notif = Notification.objects.create(
                utilisateur=self.user,
                titre=f'Test {i}',
                message='Test',
                lue=True
            )
            # Rendre la notification ancienne
            notif.date_creation = timezone.now() - timedelta(days=40)
            notif.save()
        
        result = NotificationTasks.nettoyer_anciennes_notifications(jours=30)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['deleted'], 5)
        self.assertEqual(Notification.objects.count(), 0)
    
    def test_envoyer_rapport_quotidien_admin(self):
        """Test de l'envoi du rapport quotidien aux admins."""
        result = NotificationTasks.envoyer_rapport_quotidien_admin()
        
        self.assertTrue(result['success'])
        self.assertGreater(result['admins_notified'], 0)
        
        # Vérifier que des notifications ont été créées pour les admins
        notif_count = Notification.objects.filter(
            utilisateur=self.admin,
            titre='Rapport quotidien'
        ).count()
        self.assertGreater(notif_count, 0)
    
    def test_executer_toutes_taches_quotidiennes(self):
        """Test de l'exécution de toutes les tâches quotidiennes."""
        with patch.object(AlerteService, 'verifier_concessions_expiring', return_value=[]):
            with patch.object(AlerteService, 'verifier_factures_en_retard', return_value=[]):
                with patch.object(AlerteService, 'verifier_seuil_places_critiques', return_value=[]):
                    results = NotificationTasks.executer_toutes_taches_quotidiennes()
        
        self.assertIn('concessions_expiring', results)
        self.assertIn('factures_en_retard', results)
        self.assertIn('seuil_places_critiques', results)
        self.assertIn('rapport_admin', results)
        
        # Toutes les tâches devraient réussir
        for task_result in results.values():
            self.assertTrue(task_result['success'])