"""
Script de démarrage pour la production avec Waitress.
Usage: python run_production.py
"""
import os
import sys

if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.production_settings')
    
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed?"
        ) from exc
    
    # Collecter les fichiers statiques
    print("📦 Collecte des fichiers statiques...")
    os.system('python manage.py collectstatic --noinput')
    
    # Démarrer le serveur Waitress
    print("\n🚀 Démarrage du serveur de production...")
    print("🌐 URL: http://127.0.0.1:8000")
    print("⚠️  Appuie sur Ctrl+C pour arrêter\n")
    
    from waitress import serve
    from config.wsgi import application
    
    serve(application, host='127.0.0.1', port=8000, threads=4)