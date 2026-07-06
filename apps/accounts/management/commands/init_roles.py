"""
Commande Django pour initialiser les rôles et permissions RBAC.
Usage : python manage.py init_roles
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from apps.core.models import Zone, Caveau, Concession, Defunt, Inhumation, DemandeExhumation, ParametreCimetiere
from apps.billing.models import Facture, Paiement, TransactionFinanciere
from apps.notifications.models import EmailLog, Notification


class Command(BaseCommand):
    help = 'Initialise les groupes d\'utilisateurs et leurs permissions RBAC'
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n🔐 Initialisation des rôles RBAC...'))
        self.stdout.write('=' * 70)
        
        # Récupérer les ContentTypes
        ct_zone = ContentType.objects.get_for_model(Zone)
        ct_caveau = ContentType.objects.get_for_model(Caveau)
        ct_concession = ContentType.objects.get_for_model(Concession)
        ct_defunt = ContentType.objects.get_for_model(Defunt)
        ct_inhumation = ContentType.objects.get_for_model(Inhumation)
        ct_exhumation = ContentType.objects.get_for_model(DemandeExhumation)
        ct_parametre = ContentType.objects.get_for_model(ParametreCimetiere)
        ct_facture = ContentType.objects.get_for_model(Facture)
        ct_paiement = ContentType.objects.get_for_model(Paiement)
        ct_transaction = ContentType.objects.get_for_model(TransactionFinanciere)
        ct_email = ContentType.objects.get_for_model(EmailLog)
        ct_notification = ContentType.objects.get_for_model(Notification)
        
        # ============================================
        # GROUPE 1 : ADMINISTRATEURS
        # Accès complet à tout
        # ============================================
        self.stdout.write(self.style.NOTICE('\n👑 Création du groupe ADMINISTRATEURS...'))
        admin_group, created = Group.objects.get_or_create(name='Administrateurs')
        if created:
            self.stdout.write(self.style.SUCCESS('  ✓ Groupe créé'))
        else:
            self.stdout.write(self.style.WARNING('  ℹ Groupe déjà existant'))
        
        # Toutes les permissions
        all_permissions = Permission.objects.all()
        admin_group.permissions.set(all_permissions)
        self.stdout.write(self.style.SUCCESS(f'  ✓ {all_permissions.count()} permissions attribuées'))
        
        # ============================================
        # GROUPE 2 : SECRÉTARIAT
        # Accès : Concessions, Défunts, Inhumations, Exhumations, Factures (lecture)
        # Pas d'accès : Paramètres, Statistiques financières détaillées
        # ============================================
        self.stdout.write(self.style.NOTICE('\n📋 Création du groupe SECRÉTARIAT...'))
        secretariat_group, created = Group.objects.get_or_create(name='Secrétariat')
        if created:
            self.stdout.write(self.style.SUCCESS('  ✓ Groupe créé'))
        else:
            self.stdout.write(self.style.WARNING('  ℹ Groupe déjà existant'))
        
        secretariat_permissions = Permission.objects.filter(
            content_type__in=[ct_zone, ct_caveau, ct_concession, ct_defunt, ct_inhumation, ct_exhumation, ct_facture, ct_notification]
        ).exclude(
            codename__in=['add_parametrecimetiere', 'change_parametrecimetiere', 'delete_parametrecimetiere']
        )
        secretariat_group.permissions.set(secretariat_permissions)
        self.stdout.write(self.style.SUCCESS(f'  ✓ {secretariat_permissions.count()} permissions attribuées'))
        
        # ============================================
        # GROUPE 3 : AGENTS DE TERRAIN
        # Accès : Caveaux (modification statut), Zones (lecture), Inhumations
        # Pas d'accès : Factures, Paiements, Paramètres
        # ============================================
        self.stdout.write(self.style.NOTICE('\n🚜 Création du groupe AGENTS DE TERRAIN...'))
        agent_group, created = Group.objects.get_or_create(name='Agents de terrain')
        if created:
            self.stdout.write(self.style.SUCCESS('  ✓ Groupe créé'))
        else:
            self.stdout.write(self.style.WARNING('  ℹ Groupe déjà existant'))
        
        agent_permissions = Permission.objects.filter(
            content_type__in=[ct_zone, ct_caveau, ct_defunt, ct_inhumation]
        ).filter(
            codename__in=[
                'view_zone',
                'view_caveau', 'change_caveau',
                'view_defunt', 'add_defunt', 'change_defunt',
                'view_inhumation', 'add_inhumation', 'change_inhumation',
            ]
        )
        agent_group.permissions.set(agent_permissions)
        self.stdout.write(self.style.SUCCESS(f'  ✓ {agent_permissions.count()} permissions attribuées'))
        
        # ============================================
        # GROUPE 4 : CLIENTS (CITOYENS)
        # Accès : Propres concessions, propres factures, propres notifications
        # Pas d'accès admin
        # ============================================
        self.stdout.write(self.style.NOTICE('\n👤 Création du groupe CLIENTS...'))
        client_group, created = Group.objects.get_or_create(name='Clients')
        if created:
            self.stdout.write(self.style.SUCCESS('  ✓ Groupe créé'))
        else:
            self.stdout.write(self.style.WARNING('  ℹ Groupe déjà existant'))
        
        # Permissions minimales pour le portail client
        client_permissions = Permission.objects.filter(
            content_type__in=[ct_zone, ct_caveau, ct_concession, ct_facture, ct_notification]
        ).filter(
            codename__in=[
                'view_zone', 'view_caveau',
                'view_concession',
                'view_facture',
                'view_notification',
            ]
        )
        client_group.permissions.set(client_permissions)
        self.stdout.write(self.style.SUCCESS(f'  ✓ {client_permissions.count()} permissions attribuées'))
        
        # ============================================
        # RÉSUMÉ
        # ============================================
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.SUCCESS('\n✅ Initialisation RBAC terminée !\n'))
        self.stdout.write(self.style.NOTICE('📊 Résumé des groupes :'))
        self.stdout.write(f'  👑 Administrateurs    : {admin_group.permissions.count()} permissions (accès total)')
        self.stdout.write(f'  📋 Secrétariat        : {secretariat_group.permissions.count()} permissions')
        self.stdout.write(f'  🚜 Agents de terrain  : {agent_group.permissions.count()} permissions')
        self.stdout.write(f'  👤 Clients            : {client_group.permissions.count()} permissions\n')