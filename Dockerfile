# ============================================
# Dockerfile pour l'application de gestion de cimetière
# ============================================

# 🚨 CHANGEMENT CRUCIAL : Version spécifique pour forcer l'invalidation du cache Docker
FROM python:3.11.9-slim-bookworm

# Variables d'environnement pour optimiser Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Répertoire de travail
WORKDIR /app

# Installation des dépendances système nécessaires
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

# Installation de GDAL
RUN pip install --no-cache-dir GDAL==$(gdal-config --version)

# 🚨 FORCE CACHE BUST : Changement de texte statique pour obliger la réinstallation
RUN echo "CACHE_BUST_VERSION_3" && \
    grep -v '^GDAL' requirements.txt > requirements_no_gdal.txt && \
    pip install --no-cache-dir -r requirements_no_gdal.txt

# Copie du code source du projet
COPY . .

# Collecte des fichiers statiques pour la production
RUN python manage.py collectstatic --noinput --clear

# Exposition du port par défaut (Gunicorn)
EXPOSE 8000

# Commande de démarrage avec Gunicorn
CMD ["gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "3", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]