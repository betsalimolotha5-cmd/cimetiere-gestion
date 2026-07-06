# ============================================
# Dockerfile pour l'application de gestion de cimetière
# ============================================

# Image de base officielle Python 3.11 (stable & légère)
FROM python:3.11-slim

# Variables d'environnement pour optimiser Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Répertoire de travail
WORKDIR /app

# Installation des dépendances système nécessaires
# - build-essential: compilation des paquets Python
# - libpq-dev: client PostgreSQL (pour psycopg2)
# - gdal-bin & libgdal-dev: support PostGIS (géolocalisation)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    gdal-bin \
    libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

# Copie et installation des dépendances Python
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

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