# ============================================
# Dockerfile pour l'application de gestion de cimetière
# ============================================

# Image de base officielle Python 3.11 (stable & légère, basée sur Debian)
FROM python:3.11-slim

# Variables d'environnement pour optimiser Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# Force rebuild for weasyprint fix

# Répertoire de travail
WORKDIR /app

# Installation des dépendances système nécessaires
# - build-essential: compilation des paquets Python
# - libpq-dev: client PostgreSQL (pour psycopg)
# - gdal-bin & libgdal-dev: support PostGIS (géolocalisation)
# - libcairo2, libpango, libgdk-pixbuf-xlib, libglib2.0, libffi-dev: WeasyPrint (génération PDF)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    gdal-bin \
    libgdal-dev \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-xlib-2.0-0 \
    libffi-dev \
    libglib2.0-0 \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Copie du fichier requirements.txt
COPY requirements.txt .

# Mise à jour de pip
RUN pip install --upgrade pip

# 🌟 ASTUCE CRUCIALE : Installer la version de GDAL Python qui correspond EXACTEMENT 
# à la version système installée par apt (évite tout conflit de compilation)
RUN pip install --no-cache-dir GDAL==$(gdal-config --version)

# Installation du reste des dépendances Python
# (On filtre pour ignorer toute ligne GDAL qui aurait pu rester dans le fichier)
RUN grep -v '^GDAL' requirements.txt > requirements_no_gdal.txt && \
    pip install --no-cache-dir -r requirements_no_gdal.txt

# Copie du code source du projet
COPY . .

# Collecte des fichiers statiques pour la production
RUN python manage.py collectstatic --noinput --clear

# Exposition du port par défaut (Gunicorn)
EXPOSE 8000

# Commande de démarrage avec Gunicorn
# 3 workers recommandés pour (2 x CPU + 1)
CMD ["gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "3", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]