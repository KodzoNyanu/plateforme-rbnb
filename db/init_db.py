"""Initialise la base : crée la base 'rbnb_togo' si besoin, puis exécute schema.sql.

Lit la connexion depuis .env (variable DATABASE_URL) — aucun mot de passe en dur.
Usage :  python db/init_db.py
"""
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

import psycopg
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

url = os.getenv("DATABASE_URL", "")
if "TON_MOT_DE_PASSE" in url or not url:
    sys.exit("⛔ Renseigne d'abord ton mot de passe PostgreSQL dans le fichier .env")

parsed = urlparse(url)
dbname = parsed.path.lstrip("/")                       # ex: rbnb_togo
admin_url = url.replace(f"/{dbname}", "/postgres")     # connexion à la base 'postgres'

# 1) Créer la base si elle n'existe pas
with psycopg.connect(admin_url, autocommit=True) as conn:
    exists = conn.execute(
        "SELECT 1 FROM pg_database WHERE datname = %s", (dbname,)
    ).fetchone()
    if exists:
        print(f"ℹ️  La base '{dbname}' existe déjà.")
    else:
        conn.execute(f'CREATE DATABASE "{dbname}"')
        print(f"✅ Base '{dbname}' créée.")

# 2) Exécuter le schéma + les données de départ, puis le seed de démo
with psycopg.connect(url, autocommit=True) as conn:
    conn.execute((ROOT / "db" / "schema.sql").read_text(encoding="utf-8"))
    print("✅ schema.sql exécuté (tables + données de départ).")
    demo = ROOT / "db" / "seed_demo.sql"
    if demo.exists():
        conn.execute(demo.read_text(encoding="utf-8"))
        print("✅ seed_demo.sql exécuté (annonces + scores de démo).")

# 3) Petit récapitulatif
with psycopg.connect(url) as conn:
    for table in ("regions", "villes", "communes", "quartiers", "property_types",
                  "amenities", "criteres", "parametres_commission"):
        n = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"   • {table:<22} {n} ligne(s)")
print("🎉 Base prête.")
