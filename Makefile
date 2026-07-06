# ============================================
# Makefile - Raccourcis de commandes
# Application de Gestion de Cimetière
# ============================================
# Usage: make <commande>
# Exemple: make install, make run, make test

# Variables
PYTHON := python3
PIP := pip
MANAGE := $(PYTHON) manage.py
DOCKER := docker
DOCKER_COMPOSE := docker-compose
PROJECT_NAME := cimetiere-gestion
VERSION := 1.0.0

# Couleurs pour l'affichage
GREEN := \033[0;32m
YELLOW := \033[1;33m
BLUE := \033[0;34m
NC := \033[0m

# ============================================
# AIDE
# ============================================
.PHONY: help
help:  ## Afficher cette aide
	@echo ""
	@echo "$(BLUE)============================================$(NC)"
	@echo "$(GREEN)🏛️  GESTION CIMETIÈRE - COMMANDES$(NC)"
	@echo "$(BLUE)============================================$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "$(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""

# ============================================
# INSTALLATION
# ============================================
.PHONY: install
install:  ## Installation complète du projet
	@echo "$(BLUE)[INFO]$(NC) Installation du projet..."
	@chmod +x scripts/setup.sh
	@./scripts/setup.sh

.PHONY: install-deps
install-deps:  ## Installation des dépendances Python
	@echo "$(BLUE)[INFO]$(NC) Installation des dépendances..."
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

.PHONY: install-dev
install-dev:  ## Installation des dépendances de développement
	@echo "$(BLUE)[INFO]$(NC) Installation des dépendances de développement..."
	$(PIP) install -e ".[dev]"
	$(PIP) install pre-commit
	pre-commit install

# ============================================
# CONFIGURATION
# ============================================
.PHONY: env
env:  ## Créer le fichier .env à partir du modèle
	@echo "$(BLUE)[INFO]$(NC) Création du fichier .env..."
	@test -f .env || cp .env.example .env
	@echo "$(GREEN)[OK]$(NC) Fichier .env créé"

.PHONY: secret-key
secret-key:  ## Générer une nouvelle clé secrète Django
	@$(PYTHON) -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

.PHONY: migrate
migrate:  ## Appliquer les migrations Django
	@echo "$(BLUE)[INFO]$(NC) Application des migrations..."
	$(MANAGE) makemigrations
	$(MANAGE) migrate
	@echo "$(GREEN)[OK]$(NC) Migrations appliquées"

.PHONY: createsuperuser
createsuperuser:  ## Créer un superutilisateur
	$(MANAGE) createsuperuser

.PHONY: collectstatic
collectstatic:  ## Collecter les fichiers statiques
	@echo "$(BLUE)[INFO]$(NC) Collecte des fichiers statiques..."
	$(MANAGE) collectstatic --noinput --clear
	@echo "$(GREEN)[OK]$(NC) Fichiers collectés"

# ============================================
# SERVEUR
# ============================================
.PHONY: run
run:  ## Lancer le serveur Django (développement)
	@echo "$(BLUE)[INFO]$(NC) Démarrage du serveur Django..."
	$(MANAGE) runserver 0.0.0.0:8000

.PHONY: run-prod
run-prod:  ## Lancer Gunicorn (production)
	@echo "$(BLUE)[INFO]$(NC) Démarrage de Gunicorn..."
	gunicorn config.wsgi:application \
		--bind 0.0.0.0:8000 \
		--workers 3 \
		--timeout 120 \
		--access-logfile - \
		--error-logfile -

.PHONY: run-flet
run-flet:  ## Lancer le frontend Flet
	@echo "$(BLUE)[INFO]$(NC) Démarrage du frontend Flet..."
	cd frontend && $(PYTHON) main.py

.PHONY: run-all
run-all:  ## Lancer tous les services (Docker)
	@echo "$(BLUE)[INFO]$(NC) Démarrage de tous les services..."
	$(DOCKER_COMPOSE) up --build

# ============================================
# TESTS
# ============================================
.PHONY: test
test:  ## Lancer tous les tests
	@echo "$(BLUE)[INFO]$(NC) Lancement des tests..."
	pytest --cov=apps --cov=frontend --cov-report=term-missing

.PHONY: test-fast
test-fast:  ## Tests rapides sans couverture
	@echo "$(BLUE)[INFO]$(NC) Tests rapides..."
	pytest -x --no-cov

.PHONY: test-accounts
test-accounts:  ## Tests de l'application accounts
	pytest tests/test_accounts.py -v

.PHONY: test-core
test-core:  ## Tests de l'application core
	pytest tests/test_core.py -v

.PHONY: test-billing
test-billing:  ## Tests de l'application billing
	pytest tests/test_billing.py -v

.PHONY: test-notifications
test-notifications:  ## Tests de l'application notifications
	pytest tests/test_notifications.py -v

.PHONY: coverage
coverage:  ## Rapport de couverture HTML
	@echo "$(BLUE)[INFO]$(NC) Génération du rapport de couverture..."
	pytest --cov=apps --cov=frontend --cov-report=html
	@echo "$(GREEN)[OK]$(NC) Rapport disponible dans htmlcov/"
	@echo "$(BLUE)[INFO]$(NC) Ouvrir : open htmlcov/index.html"

# ============================================
# QUALITÉ DU CODE
# ============================================
.PHONY: lint
lint:  ## Vérifier la qualité du code (Ruff)
	@echo "$(BLUE)[INFO]$(NC) Vérification du code..."
	ruff check apps/ frontend/ tests/

.PHONY: lint-fix
lint-fix:  ## Corriger automatiquement les erreurs
	@echo "$(BLUE)[INFO]$(NC) Correction automatique..."
	ruff check --fix apps/ frontend/ tests/

.PHONY: format
format:  ## Formater le code (Black + isort)
	@echo "$(BLUE)[INFO]$(NC) Formatage du code..."
	black apps/ frontend/ tests/
	isort apps/ frontend/ tests/

.PHONY: check
check: lint format test  ## Vérification complète (lint + format + tests)

# ============================================
# DOCKER
# ============================================
.PHONY: docker-build
docker-build:  ## Construire les images Docker
	@echo "$(BLUE)[INFO]$(NC) Construction des images..."
	$(DOCKER_COMPOSE) build

.PHONY: docker-up
docker-up:  ## Démarrer les conteneurs
	$(DOCKER_COMPOSE) up -d

.PHONY: docker-down
docker-down:  ## Arrêter les conteneurs
	$(DOCKER_COMPOSE) down

.PHONY: docker-logs
docker-logs:  ## Voir les logs des conteneurs
	$(DOCKER_COMPOSE) logs -f

.PHONY: docker-shell
docker-shell:  ## Entrer dans le conteneur web
	$(DOCKER_COMPOSE) exec web bash

.PHONY: docker-db
docker-db:  ## Entrer dans la base de données
	$(DOCKER_COMPOSE) exec db psql -U postgres -d cimetiere_db

.PHONY: docker-restart
docker-restart: docker-down docker-up  ## Redémarrer tous les services

# ============================================
# BASE DE DONNÉES
# ============================================
.PHONY: db-shell
db-shell:  ## Shell PostgreSQL
	$(MANAGE) dbshell

.PHONY: db-reset
db-reset:  ## Réinitialiser la base de données (⚠️ DANGER)
	@echo "$(YELLOW)[WARN]$(NC) Cette action va supprimer toutes les données !"
	@read -p "Continuer ? (oui/non) : " confirm; \
	if [ "$$confirm" = "oui" ]; then \
		$(MANAGE) reset_db --noinput; \
		$(MAKE) migrate; \
		echo "$(GREEN)[OK]$(NC) Base réinitialisée"; \
	else \
		echo "$(BLUE)[INFO]$(NC) Opération annulée"; \
	fi

.PHONY: db-dump
db-dump:  ## Exporter la base de données
	@echo "$(BLUE)[INFO]$(NC) Export de la base de données..."
	@mkdir -p backups
	pg_dump -U postgres -h localhost cimetiere_db > backups/db_$$(date +%Y%m%d_%H%M%S).sql
	@echo "$(GREEN)[OK]$(NC) Dump créé dans backups/"

.PHONY: db-backup
db-backup: db-dump  ## Alias pour db-dump

# ============================================
# TÂCHES QUOTIDIENNES
# ============================================
.PHONY: daily-tasks
daily-tasks:  ## Exécuter les tâches quotidiennes
	@echo "$(BLUE)[INFO]$(NC) Exécution des tâches quotidiennes..."
	@chmod +x scripts/daily_tasks.sh
	@./scripts/daily_tasks.sh

.PHONY: check-expiring
check-expiring:  ## Vérifier les concessions expirantes
	$(MANAGE) check_expiring_concessions

.PHONY: send-reminders
send-reminders:  ## Envoyer les rappels de paiement
	$(MANAGE) send_payment_reminders

.PHONY: send-report
send-report:  ## Envoyer le rapport quotidien aux admins
	$(MANAGE) send_daily_report

# ============================================
# DONNÉES DE TEST
# ============================================
.PHONY: fixtures
fixtures:  ## Charger les données de test
	@echo "$(BLUE)[INFO]$(NC) Chargement des données de test..."
	$(MANAGE) create_test_data || echo "$(YELLOW)[WARN]$(NC) Commande non disponible"

.PHONY: flush
flush:  ## Supprimer toutes les données (⚠️ DANGER)
	@echo "$(YELLOW)[WARN]$(NC) Suppression de toutes les données..."
	$(MANAGE) flush --noinput

# ============================================
# DÉPLOIEMENT
# ============================================
.PHONY: deploy-check
deploy-check:  ## Vérifier la configuration pour le déploiement
	@echo "$(BLUE)[INFO]$(NC) Vérification de la configuration..."
	$(MANAGE) check --deploy

.PHONY: build
build:  ## Construire le projet pour la production
	@echo "$(BLUE)[INFO]$(NC) Construction pour la production..."
	$(MAKE) collectstatic
	$(MAKE) test
	@echo "$(GREEN)[OK]$(NC) Build terminé"

# ============================================
# NETTOYAGE
# ============================================
.PHONY: clean
clean:  ## Nettoyer les fichiers temporaires
	@echo "$(BLUE)[INFO]$(NC) Nettoyage..."
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache .coverage htmlcov .mypy_cache .ruff_cache
	rm -rf build dist
	@echo "$(GREEN)[OK]$(NC) Nettoyage terminé"

.PHONY: clean-all
clean-all: clean  ## Nettoyage complet (incluant venv et Docker)
	@echo "$(YELLOW)[WARN]$(NC) Nettoyage complet..."
	rm -rf venv
	$(DOCKER_COMPOSE) down -v --rmi all || true
	@echo "$(GREEN)[OK]$(NC) Nettoyage complet terminé"

# ============================================
# INFOS
# ============================================
.PHONY: version
version:  ## Afficher la version du projet
	@echo "$(GREEN)$(PROJECT_NAME)$(NC) v$(VERSION)"

.PHONY: info
info:  ## Afficher les informations du projet
	@echo ""
	@echo "$(BLUE)============================================$(NC)"
	@echo "$(GREEN)🏛️  $(PROJECT_NAME)$(NC) v$(VERSION)"
	@echo "$(BLUE)============================================$(NC)"
	@echo ""
	@echo "Python : $$(python3 --version)"
	@echo "Django : $$(python3 -c 'import django; print(django.get_version())')"
	@echo "Auteur : MVIBUNDULU Gaëtan"
	@echo "Licence : MIT"
	@echo ""

# ============================================
# CIBLE PAR DÉFAUT
# ============================================
.DEFAULT_GOAL := help