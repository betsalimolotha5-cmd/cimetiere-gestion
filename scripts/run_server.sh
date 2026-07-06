#!/bin/bash
# ============================================
# Script de lancement du serveur de développement
# Application de Gestion de Cimetière
# ============================================
# Usage: chmod +x scripts/run_server.sh && ./scripts/run_server.sh

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
log_info "Activation de l'environnement virtuel..."
source venv/bin/activate

# Vérifier le fichier .env
if [ ! -f ".env" ]; then
    log_error "Fichier .env non trouvé. Lancez d'abord : ./scripts/setup.sh"
    exit 1
fi

# Charger les variables d'environnement
set -a
source .env
set +a

# Port par défaut
PORT=${PORT:-8000}

# ============================================
# MENU DE DÉMARRAGE
# ============================================
echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}🏛️  GESTION CIMETIÈRE - SERVEUR${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo "Choisissez le mode de démarrage :"
echo "  1) Serveur Django (développement)"
echo "  2) Gunicorn (production locale)"
echo "  3) Docker Compose (tous les services)"
echo "  4) Frontend Flet uniquement"
echo "  5) Quitter"
echo ""
read -p "Votre choix (1-5) : " choice

case $choice in
    1)
        log_info "Lancement du serveur Django en mode développement..."
        echo -e "${YELLOW}🌐 Accès : http://localhost:${PORT}/${NC}"
        echo -e "${YELLOW}📚 API Docs : http://localhost:${PORT}/api/docs/${NC}"
        echo -e "${YELLOW}🔧 Admin : http://localhost:${PORT}/admin/${NC}"
        echo ""
        python manage.py runserver 0.0.0.0:$PORT
        ;;
    
    2)
        log_info "Lancement avec Gunicorn..."
        echo -e "${YELLOW}🌐 Accès : http://localhost:${PORT}/${NC}"
        echo ""
        gunicorn config.wsgi:application \
            --bind 0.0.0.0:$PORT \
            --workers 3 \
            --timeout 120 \
            --reload
        ;;
    
    3)
        log_info "Lancement de Docker Compose..."
        echo -e "${YELLOW}🐳 Démarrage de tous les services...${NC}"
        echo ""
        docker-compose up --build
        ;;
    
    4)
        log_info "Lancement du frontend Flet..."
        echo -e "${YELLOW}🎨 Frontend : http://localhost:8550/${NC}"
        echo ""
        cd frontend
        python main.py
        ;;
    
    5)
        log_info "Au revoir !"
        exit 0
        ;;
    
    *)
        log_error "Choix invalide"
        exit 1
        ;;
esac