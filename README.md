# Locations Togo — Plateforme de centralisation des locations immobilières

Plateforme web de locations au Togo, hiérarchisée **Région > Ville > Commune > Quartier**,
avec **comparateur de quartiers** et **double tarification** (au mois / à la nuitée).

## Stack
- **Backend** : Python + Flask (rendu serveur Jinja2)
- **Base de données** : PostgreSQL (SQL écrit à la main via psycopg 3)
- **Architecture** : *modulaire par page* — chaque page est un module autonome
  dans `app/modules/` (ses routes, ses templates, ses requêtes SQL).

## Structure
```
app/
├── __init__.py            # usine à application (assemble les modules)
├── config.py              # configuration (lue depuis .env)
├── db.py                  # connexion PostgreSQL + helper query()
├── templates/base.html    # gabarit commun + _macros.html
├── static/css/style.css
└── modules/               # 🔑 UN DOSSIER = UNE PAGE
    ├── home/              # accueil
    ├── zones/             # guide + comparateur de quartiers
    ├── properties/        # annonces (liste + détail)
    └── search/            # recherche multicritères
db/
├── schema.sql             # schéma complet + données de base
├── seed_demo.sql          # données de démonstration
└── init_db.py             # crée la base et exécute les scripts
```

## Installation
```powershell
# 1. Dépendances
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# 2. Configurer la base : éditer .env et remplacer TON_MOT_DE_PASSE
#    par le mot de passe PostgreSQL choisi à l'installation.

# 3. Créer et remplir la base
.\.venv\Scripts\python.exe db\init_db.py

# 4. Lancer le serveur
.\.venv\Scripts\python.exe run.py
```
Puis ouvrir http://127.0.0.1:5000

## Ajouter une nouvelle page
1. Créer `app/modules/ma_page/` avec `routes.py` (+ `repository.py`, `templates/`).
2. Définir un `bp = Blueprint(...)`.
3. L'enregistrer dans `app/__init__.py`.
```
