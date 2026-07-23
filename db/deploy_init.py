"""Initialise le schéma sur une base DÉJÀ EXISTANTE (déploiement, ex: Render).

Contrairement à db/init_db.py (usage local), ce script ne tente PAS de créer la
base de données : sur un hébergeur managé, elle est provisionnée automatiquement
et l'utilisateur applicatif n'a généralement pas le droit de se connecter à la
base admin 'postgres' pour en créer une nouvelle.

Usage (depuis ta machine, avec l'URL EXTERNE de la base Render dans DATABASE_URL) :
    python db/deploy_init.py            -> schéma + données de référence
    python db/deploy_init.py --demo     -> + annonces de démonstration
"""
import os
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

url = os.getenv("DATABASE_URL", "")
if not url:
    sys.exit("⛔ DATABASE_URL n'est pas définie (mets l'URL externe de la base Render dans .env).")

with psycopg.connect(url, autocommit=True) as conn:
    conn.execute((ROOT / "db" / "schema.sql").read_text(encoding="utf-8"))
    print("✅ schema.sql exécuté (tables + données de départ).")
    if "--demo" in sys.argv:
        demo = ROOT / "db" / "seed_demo.sql"
        if demo.exists():
            conn.execute(demo.read_text(encoding="utf-8"))
            print("✅ seed_demo.sql exécuté (annonces + scores de démo).")

with psycopg.connect(url) as conn:
    for table in ("regions", "villes", "communes", "quartiers", "property_types",
                  "amenities", "criteres", "parametres_commission"):
        n = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"   • {table:<22} {n} ligne(s)")
print("🎉 Base distante prête.")
