"""
Script de backup automatique de la base de données.
À exécuter quotidiennement via cron ou task scheduler.
"""
import os
import sys
import django
from pathlib import Path
from datetime import datetime
import subprocess

# Ajouter le répertoire racine au path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

# Configurer Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings


def create_backup():
    """Crée un backup de la base de données PostgreSQL."""
    # Créer le dossier backups s'il n'existe pas
    backup_dir = BASE_DIR / 'backups'
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    # Générer le nom du fichier
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = backup_dir / f'backup_{timestamp}.sql'
    
    # Récupérer les paramètres de la base
    db_settings = settings.DATABASES['default']
    
    # Construire la commande pg_dump
    env = os.environ.copy()
    env['PGPASSWORD'] = db_settings['PASSWORD']
    
    cmd = [
        'pg_dump',
        '-h', db_settings['HOST'],
        '-p', str(db_settings['PORT']),
        '-U', db_settings['USER'],
        '-d', db_settings['NAME'],
        '-F', 'c',  # Format custom (compressé)
        '-f', str(backup_file),
    ]
    
    try:
        print(f"Création du backup : {backup_file}")
        result = subprocess.run(cmd, env=env, check=True, capture_output=True, text=True)
        print(f"✓ Backup créé avec succès : {backup_file}")
        print(f"  Taille : {backup_file.stat().st_size / 1024:.2f} KB")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Erreur lors du backup : {e}")
        print(f"  stderr : {e.stderr}")
        return False
    except Exception as e:
        print(f"✗ Erreur inattendue : {e}")
        return False


def clean_old_backups(days_to_keep=30):
    """Supprime les backups de plus de X jours."""
    backup_dir = BASE_DIR / 'backups'
    if not backup_dir.exists():
        return
    
    cutoff_date = datetime.now().timestamp() - (days_to_keep * 24 * 60 * 60)
    deleted_count = 0
    
    for backup_file in backup_dir.glob('backup_*.sql'):
        if backup_file.stat().st_mtime < cutoff_date:
            print(f"Suppression : {backup_file.name}")
            backup_file.unlink()
            deleted_count += 1
    
    print(f"✓ {deleted_count} ancien(s) backup(s) supprimé(s)")


if __name__ == '__main__':
    print("=" * 60)
    print("BACKUP AUTOMATIQUE - Gestion Cimetière")
    print("=" * 60)
    
    # Créer le backup
    success = create_backup()
    
    # Nettoyer les anciens backups
    clean_old_backups(days_to_keep=30)
    
    print("=" * 60)
    if success:
        print("✓ Backup terminé avec succès")
    else:
        print("✗ Backup échoué")
    print("=" * 60)
    
    sys.exit(0 if success else 1)