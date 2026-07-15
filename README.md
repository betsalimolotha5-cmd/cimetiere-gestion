# 🏛️ Application de Gestion de Cimetière

**Projet GI2 - 2026**  
**Développé par : MVIBUNDULU Gaëtan**  
📧 mvibundulugaetan1@gmail.com  
📱 06 910 3715 / 05 322 1067

---

## 📋 Table des matières

1. [Présentation du projet](#-présentation-du-projet)
2. [Fonctionnalités](#-fonctionnalités)
3. [Stack technique](#-stack-technique)
4. [Architecture du projet](#-architecture-du-projet)
5. [Installation locale](#-installation-locale)
6. [Configuration](#-configuration)
7. [Déploiement en production](#-déploiement-en-production)
8. [Utilisation](#-utilisation)
9. [API REST](#-api-rest)
10. [Structure du projet](#-structure-du-projet)
11. [Conformité au CDC](#-conformité-au-cdc)
12. [Licence](#-licence)

---

## 🎯 Présentation du projet

Cette application web permet la **numérisation complète de la gestion d'un cimetière** : cartographie interactive des emplacements, réservation en ligne par les citoyens, gestion des concessions, exhumations, facturation automatique et reporting.

Elle répond aux besoins de traçabilité, de sécurité et d'accessibilité 24h/24.

### 🌐 Site en ligne

🔗 **URL publique** : [https://cimetiere-gestion.onrender.com](https://cimetiere-gestion.onrender.com)

---

## ✨ Fonctionnalités

###  Gestion des utilisateurs et rôles (RBAC)
- **4 rôles** : Administrateur, Agent de terrain, Secrétariat, Client (citoyen)
- **Authentification sécurisée** : Email + Mot de passe
- **MFA (Double authentification)** : Code TOTP par email obligatoire
- **Permissions granulaires** : Accès différencié selon le rôle

### ️ Cartographie Interactive (SIG)
- **Carte dynamique Leaflet** avec géolocalisation des caveaux
- **Code couleur en temps réel** :
  - 🟢 Vert : Disponible
  - 🟠 Orange : Réservé / En attente de validation
  - 🔴 Rouge : Occupé / Validé
  - ⚫ Gris : Zone non exploitable
- **PostGIS** pour le stockage des coordonnées géographiques

### 📝 Processus de réservation et validation
- **Workflow client** : Sélection sur carte → Formulaire → Soumission
- **Validation Admin** : Passage du statut Orange → Rouge
- **Facturation automatique** : Génération PDF + envoi par email sécurisé

### ⚰️ Gestion des concessions et exhumations
- **Concessions** : Attribution, renouvellement, résiliation
- **Suivi des durées** : Temporaires, perpétuelles, alertes d'échéance
- **Exhumations** : Demandes, validation administrative, traçabilité
- **Documents légaux** : Autorisations d'exhumation, procès-verbaux

### 💰 Gestion financière
- **Paiements multi-canaux** : Mobile Money, Airtel Money, espèces, virement
- **Suivi des soldes** : Paiements partiels, historique par client

### 📊 Reporting et statistiques
- **Tableaux de bord** : Taux d'occupation, jauge de saturation, revenus
- **Exports** : CSV et Excel (caveaux, concessions, défunts, inhumations, exhumations)

### 🔌 API REST documentée
- **Django REST Framework** avec OpenAPI/Swagger
- **Documentation interactive** : `/api/docs/` (Swagger UI) et `/api/redoc/` (ReDoc)

---

## 🛠️ Stack technique

| Composant | Technologie |
|-----------|-------------|
| **Backend** | Django 5.2.15 (Python 3.11+) |
| **Frontend** | HTML/CSS/JS + Leaflet (carte) + Flet (desktop) |
| **Base de données** | PostgreSQL 15 + PostGIS 3.4 |
| **API REST** | Django REST Framework + drf-spectacular |
| **Authentification** | Django Auth + pyotp (MFA TOTP) |
| **PDF** | WeasyPrint + ReportLab |
| **Excel** | Openpyxl |
| **Hébergement** | Render (Web) + Neon (PostgreSQL) |
| **Serveur web** | Gunicorn + WhiteNoise (fichiers statiques) |
| **Versionning** | Git + GitHub |

---

## ️ Architecture du projet

cimetiere-gestion/
├── config/ # Configuration Django
│ ├── settings.py # Paramètres (dev + prod)
│ ├── urls.py # Routes principales
│ └── wsgi.py # Point d'entrée WSGI
├── apps/ # Applications métier
│ ├── accounts/ # Utilisateurs, rôles, MFA
│ ├── core/ # Cimetière, zones, caveaux, concessions
│ ├── billing/ # Facturation, paiements
│ ├── notifications/ # Emails, alertes
│ ├── reports/ # Rapports, exports
│ ├── mfa/ # Authentification double facteur
│ └── portal/ # Portail client public
├── static/ # Fichiers statiques (CSS, JS, images)
├── templates/ # Templates HTML
├── requirements.txt # Dépendances Python
├── Procfile # Configuration Render
├── manage.py # CLI Django
└── README.md # Ce fichier



##  Installation locale

### Prérequis
- Python 3.11 ou supérieur
- PostgreSQL 15 + PostGIS 3.4
- Git

### Étapes d'installation

1. **Cloner le dépôt**
   ```bash
   git clone https://github.com/betsalimolotha5-cmd/cimetiere-gestion.git
   cd cimetiere-gestion



cimetiere-gestion/
├── apps/
│   ├── accounts/
│   │   ├── models.py          # Modèle User personnalisé + Rôles
│   │   ├── views.py           # Vues d'authentification
│   │   └── admin.py           # Administration Django
│   ├── core/
│   │   ├── models.py          # Zone, Caveau, Concession, Defunt, Inhumation
│   │   ├── views.py           # Vues métier + exports CSV/Excel
│   │   ├── api_views.py       # API REST
│   │   └── services.py        # Logique métier (calculs, validations)
│   ├── billing/
│   │   ├── models.py          # Facture, Paiement
│   │   └── views.py           # Gestion financière
│   ├── notifications/
│   │   ── tasks.py           # Envoi d'emails, alertes
│   ├── reports/
│   │   └── views.py           # Rapports, statistiques
│   ├── mfa/
│   │   └── views.py           # Authentification double facteur
│   └── portal/
│       └── views.py           # Portail client public
├── config/
│   ├── settings.py            # Configuration Django
│   ── urls.py                # Routes principales
├── static/                    # CSS, JS, images
├── templates/                 # Templates HTML
├── requirements.txt           # Dépendances
├── Procfile                   # Configuration Render
└── manage.py                  # CLI Django