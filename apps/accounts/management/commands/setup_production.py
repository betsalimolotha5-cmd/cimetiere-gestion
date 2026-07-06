"""
Commande pour initialiser la base de données en production.
Applique les migrations et crée un superutilisateur par défaut.
"""
from django.core.management.base import BaseCommand
from django.core.management import call_command
from apps.accounts.models import User
import os


class Command(BaseCommand):
    help = 'Initialise la base de données en production'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🚀 Démarrage de la configuration production...'))
        
        # 1. Appliquer les migrations
        self.stdout.write('📦 Application des migrations...')
        call_command('migrate', verbosity=0)
        self.stdout.write(self.style.SUCCESS('✅ Migrations appliquées'))
        
        # 2. Collecter les fichiers statiques
        self.stdout.write('📁 Collecte des fichiers statiques...')
        call_command('collectstatic', verbosity=0, interactive=False)
        self.stdout.write(self.style.SUCCESS('✅ Fichiers statiques collectés'))
        
        # 3. Créer les rôles par défaut
        self.stdout.write('👥 Création des rôles...')
        from apps.accounts.models import Role
        roles = ['ADMIN', 'AGENT', 'SECRÉTARIAT', 'CLIENT']
        for role_name in roles:
            Role.objects.get_or_create(name=role_name)
        self.stdout.write(self.style.SUCCESS('✅ Rôles créés'))
        
        # 4. Créer le superutilisateur par défaut
        self.stdout.write('👤 Création du superutilisateur...')
        admin_email = os.environ.get('ADMIN_EMAIL', 'admin@cimetiere.com')
        admin_password = os.environ.get('ADMIN_PASSWORD', 'Admin@2026!')
        
        if not User.objects.filter(email=admin_email).exists():
            admin_role = Role.objects.get(name='ADMIN')
            user = User.objects.create_superuser(
                email=admin_email,
                password=admin_password,
                first_name='Admin',
                last_name='Système',
                role=admin_role
            )
            self.stdout.write(self.style.SUCCESS(f'✅ Superutilisateur créé: {admin_email}'))
        else:
            self.stdout.write(self.style.WARNING(f'⚠️  Superutilisateur existe déjà: {admin_email}'))
        
        # 5. Configurer le cimetière par défaut
        self.stdout.write('🏛️  Configuration du cimetière...')
        from apps.core.models import Cimetiere
        if not Cimetiere.objects.exists():
            Cimetiere.objects.create(
                nom='Cimetière Central',
                adresse='Adresse par défaut',
                ville='Ville',
                pays='Pays',
                superficie_totale=10000,
                description='Cimetière configuré automatiquement'
            )
            self.stdout.write(self.style.SUCCESS('✅ Cimetière créé'))
        else:
            self.stdout.write(self.style.WARNING('⚠️  Cimetière existe déjà'))
        
        self.stdout.write(self.style.SUCCESS('🎉 Configuration production terminée avec succès !'))
        self.stdout.write(self.style.SUCCESS(f'📧 Email admin: {admin_email}'))
        self.stdout.write(self.style.SUCCESS(f'🔑 Mot de passe: {admin_password}'))