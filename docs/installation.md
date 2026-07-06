# 🚀 Guide d'Installation

> Guide complet pour installer et configurer l'application de gestion de cimetière.

## 📋 Table des matières

- [Prérequis](#-prérequis)
- [Installation rapide (Docker)](#-installation-rapide-docker)
- [Installation manuelle](#-installation-manuelle)
- [Configuration](#-configuration)
- [Premier démarrage](#-premier-démarrage)
- [Dépannage](#-dépannage)

---

## 🎯 Prérequis

### Système d'exploitation supporté
- ✅ Linux (Ubuntu 20.04+, Debian 11+)
- ✅ macOS (11+)
- ✅ Windows 10/11 (avec WSL2 recommandé)

### Logiciels requis

| Logiciel | Version minimale | Vérification |
|----------|------------------|--------------|
| Python | 3.10+ | `python3 --version` |
| PostgreSQL | 14+ | `psql --version` |
| PostGIS | 3.0+ | `SELECT PostGIS_Version();` |
| Git | 2.20+ | `git --version` |
| pip | 22.0+ | `pip --version` |

### Installation des prérequis

#### Ubuntu/Debian
```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git
sudo apt install -y postgresql postgresql-contrib postgis postgresql-14-postgis-3