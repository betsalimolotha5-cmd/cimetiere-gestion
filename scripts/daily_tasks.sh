#!/bin/bash
# ============================================
# Script des tâches quotidiennes planifiées
# Application de Gestion de Cimetière
# ============================================
# Usage: chmod +x scripts/daily_tasks.sh && ./scripts/daily_tasks.sh
#
# Configuration Cron (tous les jours à 6h du matin) :
#   crontab -e
#   0 6 * * * /chemin/vers/scripts/daily_tasks.sh >> logs/daily_tasks.log 2>&1

set -e

# Couleurs
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "$(date '+%Y-%m-%d %H:%M:%S') ${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "$(date '+%Y-%m-%d %H:%M:%S') ${GREEN}[OK]${NC} $1"; }
log_error() { echo -e "$(date '+%Y-%m-%d %H:%M:%S') ${RED}[ERROR]${NC} $1"; }

# Répertoire du projet
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# Vérifier l'environnement virtuel
if [ ! -d "venv" ]; then
    log_error "Environnement virtuel non trouvé"
    exit 1
fi

source venv/bin/activate

# Charger les variables d'environnement
if [ -f ".env" ]; then
    set -a
    source .env
    set +a
fi

echo ""
log_info "========================================"
log_info "🔄 DÉMARRAGE DES TÂCHES QUOTIDIENNES"
log_info "========================================"
echo ""

# ============================================
# TÂCHE 1 : Vérifier les concessions expirantes
# ============================================
log_info "📜 Tâche 1/6 : Vérification des concessions expirantes..."
if python manage.py check_expiring_concessions; then
    log_success "Concessions expirantes vérifiées et alertes envoyées"
else
    log_error "Erreur lors de la vérification des concessions"
fi
echo ""

# ============================================
# TÂCHE 2 : Rappels de paiement en retard
# ============================================
log_info "💰 Tâche 2/6 : Envoi des rappels de paiement..."
if python manage.py send_payment_reminders; then
    log_success "Rappels de paiement envoyés"
else
    log_error "Erreur lors de l'envoi des rappels"
fi
echo ""

# ============================================
# TÂCHE 3 : Vérification du seuil de places
# ============================================
log_info "📊 Tâche 3/6 : Vérification du seuil de places critiques..."
if python manage.py check_capacity_alerts; then
    log_success "Seuil de places vérifié"
else
    log_error "Erreur lors de la vérification du seuil"
fi
echo ""

# ============================================
# TÂCHE 4 : Nettoyage des anciens logs d'emails
# ============================================
log_info "🧹 Tâche 4/6 : Nettoyage des anciens logs d'emails..."
if python manage.py cleanup_email_logs --days=90; then
    log_success "Anciens logs d'emails nettoyés"
else
    log_error "Erreur lors du nettoyage des logs"
fi
echo ""

# ============================================
# TÂCHE 5 : Nettoyage des anciennes notifications
# ============================================
log_info "🔔 Tâche 5/6 : Nettoyage des anciennes notifications..."
if python manage.py cleanup_notifications --days=30; then
    log_success "Anciennes notifications nettoyées"
else
    log_error "Erreur lors du nettoyage des notifications"
fi
echo ""

# ============================================
# TÂCHE 6 : Rapport quotidien aux administrateurs
# ============================================
log_info "📈 Tâche 6/6 : Envoi du rapport quotidien..."
if python manage.py send_daily_report; then
    log_success "Rapport quotidien envoyé aux administrateurs"
else
    log_error "Erreur lors de l'envoi du rapport"
fi
echo ""

# ============================================
# RÉSUMÉ
# ============================================
log_info "========================================"
log_success "✅ TÂCHES QUOTIDIENNES TERMINÉES"
log_info "========================================"
echo ""