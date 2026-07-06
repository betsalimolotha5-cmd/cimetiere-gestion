#!/bin/bash
# ============================================
# Script de lancement des tests automatisés
# Application de Gestion de Cimetière
# ============================================
# Usage: chmod +x scripts/run_tests.sh && ./scripts/run_tests.sh

set -e

# Couleurs
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Répertoire du projet
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# Vérifier l'environnement virtuel
if [ ! -d "venv" ]; then
    log_error "Environnement virtuel non trouvé. Lancez d'abord : ./scripts/setup.sh"
    exit 1
fi

# Activer l'environnement virtuel
source venv/bin/activate

# Charger les variables d'environnement
if [ -f ".env" ]; then
    set -a
    source .env
    set +a
fi

# ============================================
# MENU DES TESTS
# ============================================
echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}🧪 GESTION CIMETIÈRE - TESTS${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo "Choisissez le type de test :"
echo "  1) Tous les tests (avec couverture)"
echo "  2) Tests d'une application spécifique"
echo "  3) Tests rapides (sans couverture)"
echo "  4) Tests d'intégration uniquement"
echo "  5) Tests unitaires uniquement"
echo "  6) Quitter"
echo ""
read -p "Votre choix (1-6) : " choice

case $choice in
    1)
        log_info "Lancement de tous les tests avec couverture..."
        pytest --cov=apps --cov=frontend --cov-report=term-missing --cov-report=html
        log_success "Rapport de couverture disponible dans : htmlcov/"
        ;;
    
    2)
        read -p "Nom de l'application (accounts/core/billing/notifications) : " app_name
        if [ -z "$app_name" ]; then
            log_error "Nom d'application requis"
            exit 1
        fi
        log_info "Lancement des tests pour l'application : $app_name"
        pytest tests/test_$app_name.py -v
        ;;
    
    3)
        log_info "Lancement des tests rapides..."
        pytest -x --no-cov
        ;;
    
    4)
        log_info "Lancement des tests d'intégration..."
        pytest tests/ -m "integration" -v
        ;;
    
    5)
        log_info "Lancement des tests unitaires..."
        pytest tests/ -m "not integration" -v
        ;;
    
    6)
        log_info "Au revoir !"
        exit 0
        ;;
    
    *)
        log_error "Choix invalide"
        exit 1
        ;;
esac