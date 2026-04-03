Voici un `README.md` complet et professionnel pour votre backend API :

```markdown
# 🍽️ Gastiva API - Anti-Gaspillage Alimentaire

API RESTful pour l'application Gastiva, une plateforme de lutte contre le gaspillage alimentaire connectant les partenaires (restaurants, boulangeries, traiteurs) et les clients.

## 📋 Table des matières

- [Technologies](#-technologies)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Structure du projet](#-structure-du-projet)
- [Endpoints API](#-endpoints-api)
- [Authentification](#-authentification)
- [Base de données](#-base-de-données)
- [Tests](#-tests)
- [Déploiement](#-déploiement)
- [Documentation](#-documentation)
- [Contributeurs](#-contributeurs)

---

## 🚀 Technologies

| Technologie | Version | Utilisation |
|-------------|---------|-------------|
| Django | 5.2.5 | Framework backend |
| Django REST Framework | 3.15.2 | API REST |
| PostgreSQL | 15+ | Base de données |
| Simple JWT | 5.3.1 | Authentification JWT |
| drf-spectacular | 0.27.2 | Documentation Swagger |
| django-cors-headers | 4.3.1 | Gestion CORS |
| Gunicorn | 22.0.0 | Serveur WSGI |

---

## 📦 Installation

### Prérequis

- Python 3.12+
- PostgreSQL 15+
- pip (gestionnaire de paquets Python)

### Étapes d'installation

1. **Cloner le dépôt**

```bash
git clone https://github.com/votre-username/gastiva-api.git
cd gastiva-api
```

2. **Créer et activer un environnement virtuel**

```bash
# Linux/Mac
python -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

3. **Installer les dépendances**

```bash
pip install -r requirements.txt
```

4. **Configurer la base de données**

```bash
# Créer la base de données PostgreSQL
sudo -u postgres psql
CREATE DATABASE gastiva_db;
CREATE USER gastiva_user WITH PASSWORD 'your_password';
ALTER ROLE gastiva_user SET client_encoding TO 'utf8';
ALTER ROLE gastiva_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE gastiva_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE gastiva_db TO gastiva_user;
\q
```

5. **Configurer les variables d'environnement**

Créez un fichier `.env` à la racine :

```env
# Database
DB_NAME=gastiva_db
DB_USER=gastiva_user
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432

# Django
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# JWT
JWT_ACCESS_TOKEN_LIFETIME=1
JWT_REFRESH_TOKEN_LIFETIME=7
```

6. **Appliquer les migrations**

```bash
python manage.py makemigrations
python manage.py migrate
```

7. **Créer un superutilisateur**

```bash
python manage.py createsuperuser
```

8. **Lancer le serveur de développement**

```bash
python manage.py runserver
```

L'API est accessible à l'adresse : `http://localhost:8000/api/`

---

## ⚙️ Configuration

### Fichier `settings.py` principal

```python
# Configuration base de données
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST'),
        'PORT': config('DB_PORT'),
    }
}

# Configuration JWT
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'phone_number',
}

# Configuration CORS
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8000",
    "http://10.0.2.2:8000",  # Pour émulateur Android
]
```

---

## 📁 Structure du projet

```
gastiva-api/
├── manage.py
├── requirements.txt
├── .env
├── foodWasteAPI/
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── apps/
│   ├── accounts/          # Authentification & utilisateurs
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   └── permissions.py
│   ├── partners/          # Gestion des partenaires
│   ├── offers/            # Gestion des offres
│   ├── orders/            # Gestion des commandes
│   ├── payments/          # Gestion des paiements
│   ├── reviews/           # Gestion des avis
│   ├── notifications/     # Système de notifications
│   └── dashboard/         # Tableau de bord
└── static/                # Fichiers statiques
```

---

## 🔌 Endpoints API

### 🔐 Authentification (`/api/accounts/`)

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/register/` | Inscription utilisateur |
| POST | `/login/` | Connexion (email/téléphone) |
| POST | `/token/refresh/` | Rafraîchir token JWT |
| GET | `/profile/` | Profil utilisateur |
| PUT/PATCH | `/profile/update/` | Mettre à jour profil |

### 🏪 Partenaires (`/api/partners/`)

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/categories/` | Liste catégories |
| GET | `/` | Liste partenaires |
| GET | `/geo/` | Données géolocalisation |
| GET | `/my-partners/` | Mes partenaires |
| POST | `/create/` | Créer partenaire |
| GET | `/{id}/` | Détails partenaire |
| PUT/PATCH | `/{id}/update/` | Modifier partenaire |
| DELETE | `/{id}/delete/` | Supprimer partenaire |
| GET | `/{id}/offers/` | Offres du partenaire |
| GET | `/{id}/stats/` | Statistiques partenaire |

### 🍽️ Offres (`/api/offers/`)

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/categories/` | Liste catégories alimentaires |
| GET | `/home/` | Offres page d'accueil (avec filtres) |
| GET | `/featured/` | Offres en vedette |
| GET | `/expiring-soon/` | Offres expirant bientôt |
| GET | `/my-partner-offers/` | Mes offres (partenaire) |
| POST | `/create/` | Créer offre |
| GET | `/{id}/` | Détails offre |
| PUT/PATCH | `/{id}/update/` | Modifier offre |
| DELETE | `/{id}/delete/` | Supprimer offre |
| POST | `/{id}/reserve/` | Réserver offre |
| POST | `/{id}/release/` | Libérer réservation |
| PATCH | `/{id}/update-status/` | Modifier statut |

### 📦 Commandes (`/api/orders/`)

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/` | Liste commandes |
| GET | `/active/` | Commandes en cours |
| GET | `/history/` | Historique commandes |
| POST | `/create/` | Créer commande |
| GET | `/{id}/` | Détails commande |
| POST | `/{id}/cancel/` | Annuler commande |
| POST | `/{id}/confirm/` | Confirmer commande (partenaire) |
| POST | `/{id}/ready/` | Marquer prête (partenaire) |
| POST | `/{id}/pickup/` | Marquer retirée |

### 💳 Paiements (`/api/payments/`)

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/` | Liste paiements |
| POST | `/create/` | Créer paiement |
| GET | `/{id}/` | Détails paiement |
| POST | `/{id}/process/` | Traiter paiement |
| POST | `/{id}/refund/` | Rembourser |
| GET | `/stats/` | Statistiques paiements |
| GET | `/check-balance/` | Vérifier solde (simulation) |

### ⭐ Avis (`/api/reviews/`)

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/` | Liste avis publics |
| GET | `/partner/{id}/` | Avis d'un partenaire |
| GET | `/my-reviews/` | Mes avis |
| POST | `/create/` | Créer avis |
| GET | `/{id}/` | Détails avis |
| PUT/PATCH | `/{id}/update/` | Modifier avis |
| DELETE | `/{id}/delete/` | Supprimer avis |
| PATCH | `/{id}/moderate/` | Modérer (admin) |
| GET | `/stats/` | Statistiques avis |

### 📊 Dashboard Partenaire (`/api/dashboard/`)

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/partner/overview/` | Aperçu global |
| GET | `/partner/offers-stats/` | Statistiques offres |
| GET | `/partner/revenue/` | Revenus par période |

---

## 🔐 Authentification

### Schéma d'authentification

L'API utilise **JWT (JSON Web Tokens)** pour l'authentification.

**Flux d'authentification :**

```
1. Client → POST /api/accounts/login/
   Body: { "username": "90123456", "password": "..." }
   
2. Server → Réponse
   {
     "access": "eyJhbGciOiJIUzI1NiIs...",
     "refresh": "eyJhbGciOiJIUzI1NiIs...",
     "user": { ... }
   }
   
3. Requêtes suivantes → Header
   Authorization: Bearer <access_token>
```

### Rôles utilisateurs

| Rôle | Description | Permissions |
|------|-------------|-------------|
| `CLIENT` | Client final | Consulter offres, passer commandes, laisser avis |
| `PARTNER` | Partenaire (restaurateur) | Gérer offres, commandes, voir stats |
| `ADMIN` | Administrateur | Gestion complète, modération |

---

## 🗄️ Base de données

### Modèle conceptuel

```sql
-- Principales tables
- accounts_user        (Utilisateurs)
- partners_partner     (Établissements partenaires)
- partners_categorypartner (Catégories de partenaires)
- offers_foodoffer     (Offres alimentaires)
- offers_foodcategory  (Catégories d'offres)
- orders_order         (Commandes)
- orders_orderitem     (Articles de commande)
- payments_payment     (Paiements)
- reviews_review       (Avis)
- notifications_notification (Notifications)
```

### Diagramme des relations

```
User (1) ----< Order (n) ----< OrderItem (n) ---- (1) FoodOffer
  |                           |
  |                           +---- (1) Partner
  +---- (1) Partner
  |
  +---- (n) Review
```

---

## 🧪 Tests

### Lancer les tests

```bash
# Tous les tests
python manage.py test

# Tests d'une application spécifique
python manage.py test apps.accounts
python manage.py test apps.offers

# Tests avec couverture
coverage run manage.py test
coverage report
```

### Exemple de test unitaire

```python
from django.test import TestCase
from rest_framework.test import APIClient
from apps.accounts.models import User

class AuthTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        
    def test_login_success(self):
        user = User.objects.create_user(
            phone_number="90123456",
            first_name="Test",
            last_name="User",
            password="test123"
        )
        
        response = self.client.post('/api/accounts/login/', {
            'username': '90123456',
            'password': 'test123'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.json())
```

---

## 🚢 Déploiement

### Déploiement avec Gunicorn + Nginx

1. **Installer Gunicorn**

```bash
pip install gunicorn
```

2. **Configurer Gunicorn**

```bash
gunicorn --bind 0.0.0.0:8000 foodWasteAPI.wsgi:application
```

3. **Configurer Nginx**

```nginx
server {
    listen 80;
    server_name api.gastiva.com;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location /static/ {
        alias /path/to/static/;
    }
    
    location /media/ {
        alias /path/to/media/;
    }
}
```

4. **Variables d'environnement (production)**

```env
DEBUG=False
ALLOWED_HOSTS=api.gastiva.com,www.api.gastiva.com
DB_PASSWORD=secure_password
SECRET_KEY=very_secure_key
```

---

## 📚 Documentation

### Swagger UI

La documentation interactive est disponible à l'adresse :

```
http://localhost:8000/api/docs/
```

### ReDoc

Documentation alternative :

```
http://localhost:8000/api/redoc/
```

### Schéma OpenAPI

```
http://localhost:8000/api/schema/
```

---

## 🤝 Contributeurs

| Nom | Rôle | Contributions |
|-----|------|---------------|
| [Votre Nom] | Développeur Backend | Architecture, API, Modèles |
| [Nom Équipe] | Développeur Frontend | Intégration Flutter |
| [Nom Équipe] | Designer UI/UX | Maquettes, Design système |

---

## 📄 Licence

Ce projet est développé dans le cadre d'un projet académique.

---

## 📞 Support

Pour toute question ou problème :

- **Email** : support@gastiva.com
- **GitHub Issues** : [github.com/votre-repo/issues](https://github.com/votre-repo/issues)

---

## 🎯 Version

**Version actuelle :** 1.0.0

---

*Dernière mise à jour : Avril 2026*
```

Ce README.md est complet, professionnel et prêt à être utilisé pour votre projet !
