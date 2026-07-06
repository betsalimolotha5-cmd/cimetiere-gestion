#!/bin/bash
# ============================================
# Script d'installation automatisée
# Application de Gestion de Cimetière
# ============================================
# Usage: chmod +x scripts/setup.sh && ./scripts/setup.sh

set -e  # Arrêter en cas d'erreur

# Couleurs pour l'affichage
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonctions utilitaires
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ============================================
# 1. VÉRIFICATION DES PRÉREQUIS
# ============================================
log_info "Vérification des prérequis..."

# Vérifier Python
if ! command -v python3 &> /dev/null; then
    log_error "Python 3 n'est pas installé. Veuillez l'installer d'abord."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
log_success "Python $PYTHON_VERSION détecté"

# Vérifier pip
if ! command -v pip3 &> /dev/null; then
    log_error "pip n'est pas installé."
    exit 1
fi
log_success "pip détecté"

# Vérifier PostgreSQL
if ! command -v psql &> /dev/null; then
    log_warning "PostgreSQL n'est pas détecté. Assurez-vous qu'il est installé."
else
    log_success "PostgreSQL détecté"
fi

# ============================================
# 2. NAVIGATION VERS LE RÉPERTOIRE DU PROJET
# ============================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"
log_info "Répertoire du projet : $PROJECT_DIR"

# ============================================
# 3. CRÉATION DE L'ENVIRONNEMENT VIRTUEL
# ============================================
if [ ! -d "venv" ]; then
    log_info "Création de l'environnement virtuel..."
    python3 -m venv venv
    log_success "Environnement virtuel créé"
else
    log_warning "L'environnement virtuel existe déjà"
fi

# Activation
log_info "Activation de l'environnement virtuel..."
source venv/bin/activate

# ============================================
# 4. INSTALLATION DES DÉPENDANCES
# ============================================
log_info "Mise à jour de pip..."
pip install --upgrade pip

log_info "Installation des dépendances Python..."
pip install -r requirements.txt
log_success "Dépendances installées"

# ============================================
# 5. CONFIGURATION DES VARIABLES D'ENVIRONNEMENT
# ============================================
if [ ! -f ".env" ]; then
    log_info "Création du fichier .env à partir du modèle..."
    cp .env.example .env
    
    # Générer une nouvelle clé secrète
    SECRET_KEY=$(python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
    
    # Remplacer la clé dans .env (compatible Linux/macOS)
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s|SECRET_KEY=.*|SECRET_KEY=$SECRET_KEY|" .env
    else
        sed -i "s|SECRET_KEY=.*|SECRET_KEY=$SECRET_KEY|" .env
    fi
    
    log_success "Fichier .env créé avec une nouvelle clé secrète"
    log_warning "⚠️  PENSEZ À MODIFIER .env AVEC VOS PROPRES VALEURS !"
else
    log_warning "Le fichier .env existe déjà"
fi

# ============================================
# 6. CRÉATION DES DOSSIERS NÉCESSAIRES
# ============================================
log_info "Création des dossiers nécessaires..."
mkdir -p logs media invoices documents static
log_success "Dossiers créés"

# ============================================
# 7. CONFIGURATION DE LA BASE DE DONNÉES
# ============================================
log_info "Vérification de la base de données..."

# Charger les variables depuis .env
set -a
source .env
set +a

# Tenter de créer la base de données si elle n'existe pas
if command -v psql &> /dev/null; then
    log_info "Tentative de création de la base de données..."
    PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -tc \
        "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME'" | grep -q 1 || \
    PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -c \
        "CREATE DATABASE $DB_NAME" || \
    log_warning "Impossible de créer la base. Vérifiez qu'elle existe déjà."
fi

# ============================================
# 8. MIGRATIONS DJANGO
# ============================================
log_info "Application des migrations Django..."
python manage.py makemigrations
python manage.py migrate
log_success "Migrations appliquées"

# ============================================
# 9. CRÉATION DU SUPERUTILISATEUR
# ============================================
log_info "Vérification du superutilisateur..."

python manage.py shell << EOF
from apps.accounts.models import User
if not User.objects.filter(is_superuser=True).exists():
    print("CREATE_SUPERUSER")
else:
    print("SUPERUSER_EXISTS")
EOF

# Créer le superutilisateur si nécessaire
if python manage.py shell -c "from apps.accounts.models import User; exit(0 if User.objects.filter(is_superuser=True).exists() else 1)" 2>/dev/null; then
    log_success "Un superutilisateur existe déjà"
else
    log_info "Création d'un superutilisateur..."
    python manage.py createsuperuser
fi

# ============================================
# 10. COLLECTE DES FICHIERS STATIQUES
# ============================================
log_info "Collecte des fichiers statiques..."
python manage.py collectstatic --noinput --clear
log_success "Fichiers statiques collectés"

# ============================================
# 11. CRÉATION DES DONNÉES DE TEST (OPTIONNEL)
# ============================================
read -p "Voulez-vous créer des données de test ? (o/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Oo]$ ]]; then
    log_info "Création des données de test..."
    python manage.py create_test_data || log_warning "Commande non disponible"
fi

# ============================================
# 12. TERMINÉ !
# ============================================
echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}✅ INSTALLATION TERMINÉE AVEC SUCCÈS !${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo -e "${BLUE}📋 Prochaines étapes :${NC}"
echo "  1. Vérifier le fichier .env"
echo "  2. Lancer le serveur : ./scripts/run_server.sh"
echo "  3. Accéder à l'admin : http://localhost:8000/admin/"
echo "  4. Accéder à l'API : http://localhost:8000/api/docs/"
echo ""
echo -e "${YELLOW}⚠️  N'oubliez pas de modifier .env avec vos vraies valeurs !${NC}"
echo ""