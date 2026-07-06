# 🏛️ Application de Gestion de Cimetière

## 📋 Description

Application web complète pour la gestion numérique des cimetières, développée dans le cadre du projet GI2 2026.

## ✨ Fonctionnalités principales

### 🔐 Authentification et Sécurité
- Authentification par email/mot de passe
- Authentification à double facteur (MFA) par email
- Système RBAC avec 4 rôles : Administrateurs, Secrétariat, Agents de terrain, Clients

### 🗺️ Cartographie Interactive (SIG)
- Carte dynamique avec code couleur :
  - 🟢 Vert : Disponible
  - 🟠 Orange : Réservé / En attente
  - 🔴 Rouge : Occupé / Validé
  - ⚫ Gris : Non exploitable
- Sélection interactive des caveaux
- Workflow de réservation complet

### 💰 Gestion Financière
- Génération automatique de factures PDF
- Envoi par email sécurisé
- Paiements multi-canaux : Mobile Money, Airtel Money, espèces, virement
- Suivi des paiements partiels
- Journal d'audit financier

### 📋 Gestion des Concessions
- Attribution et renouvellement
- Gestion des concessions temporaires et perpétuelles
- Alertes automatiques d'échéance (30, 15, 7 jours)
- Documents légaux générés automatiquement

### ⚰️ Gestion des Exhumations
- Demandes d'exhumation avec validation administrative
- Génération automatique des autorisations et procès-verbaux PDF
- Traçabilité complète

### 🔔 Notifications
- Service de notifications centralisé
- Rappels de paiement automatiques (3, 7, 15 jours)
- Alertes d'échéance de concessions
- Tableau de bord admin des notifications

### 📊 Rapports et Statistiques
- Rapport financier (recettes, paiements, évolution)
- Rapport d'occupation (taux par zone)
- Rapport des concessions (actives, expirées, renouvelées)
- Rapport des notifications (taux de succès)
- Exports CSV et Excel de tous les registres

### 🌐 API RESTful
- API complète documentée via OpenAPI/Swagger
- Endpoints pour toutes les ressources
- Schéma YAML téléchargeable

## 🛠️ Technologies utilisées

### Backend
- **Django 5.0.1** - Framework Python
- **Django REST Framework** - API RESTful
- **PostgreSQL + PostGIS** - Base de données géographique
- **ReportLab** - Génération de PDF
- **drf-spectacular** - Documentation OpenAPI

### Frontend
- **HTML5/CSS3** - Interface responsive
- **JavaScript** - Interactivité carte
- **Leaflet.js** - Cartographie interactive

### Sécurité
- **TLS/SSL** - Chiffrement des échanges
- **MFA par email** - Double authentification
- **Audit Trail** - Journalisation complète

## 📦 Installation

### Prérequis
- Python 3.11+
- PostgreSQL 16+ avec PostGIS
- GDAL/GEOS pour PostGIS

### Étapes d'installation

1. **Installer les dépendances**
```bash
pip install -r requirements.txt