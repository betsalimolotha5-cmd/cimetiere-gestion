"""
Commande Django pour envoyer les notifications automatiques.
Usage : python manage.py envoyer_notifications
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.notifications.services import NotificationService


class Command(BaseCommand):
    help = 'Envoie les notifications automatiques (rappels de paiement et alertes de concessions)'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            type=str,
            choices=['tous', 'paiement', 'concession'],
            default='tous',
            help='Type de notifications à envoyer (tous, paiement, concession)'
        )
    
    def handle(self, *args, **options):
        type_notification = options['type']
        aujourd = timezone.now().strftime('%d/%m/%Y à %H:%M')
        
        self.stdout.write(self.style.SUCCESS(f'\n🚀 Démarrage des notifications automatiques - {aujourd}'))
        self.stdout.write('=' * 70)
        
        total_envoyes = 0
        
        # Rappels de paiement
        if type_notification in ['tous', 'paiement']:
            self.stdout.write(self.style.NOTICE('\n📧 Envoi des rappels de paiement...'))
            try:
                rappels = NotificationService.envoyer_rappels_paiement()
                total_envoyes += rappels
                if rappels > 0:
                    self.stdout.write(self.style.SUCCESS(f'  ✓ {rappels} rappel(s) de paiement envoyé(s)'))
                else:
                    self.stdout.write(self.style.WARNING('  ℹ Aucun rappel de paiement à envoyer'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ✗ Erreur lors de l\'envoi des rappels : {str(e)}'))
        
        # Alertes de concessions
        if type_notification in ['tous', 'concession']:
            self.stdout.write(self.style.NOTICE('\n🔔 Envoi des alertes d\'échéance de concessions...'))
            try:
                alertes = NotificationService.envoyer_alertes_echeance_concession()
                total_envoyes += alertes
                if alertes > 0:
                    self.stdout.write(self.style.SUCCESS(f'  ✓ {alertes} alerte(s) de concession envoyée(s)'))
                else:
                    self.stdout.write(self.style.WARNING('  ℹ Aucune alerte de concession à envoyer'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ✗ Erreur lors de l\'envoi des alertes : {str(e)}'))
        
        # Résumé final
        self.stdout.write('\n' + '=' * 70)
        if total_envoyes > 0:
            self.stdout.write(self.style.SUCCESS(f'\n✅ Terminé ! {total_envoyes} notification(s) envoyée(s) au total.\n'))
        else:
            self.stdout.write(self.style.WARNING('\nℹ Terminé. Aucune notification à envoyer pour le moment.\n'))