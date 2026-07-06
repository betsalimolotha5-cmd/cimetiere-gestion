# ============================================
# Procfile pour Heroku / déploiement cloud
# ============================================

# Application web principale (Gunicorn)
web: gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 3 --timeout 120 --access-logfile - --error-logfile -

# Tâches planifiées (optionnel - pour Heroku Scheduler)
# worker: python manage.py run_daily_tasks

# Release (migrations automatiques au déploiement)
release: python manage.py migrate --noinput