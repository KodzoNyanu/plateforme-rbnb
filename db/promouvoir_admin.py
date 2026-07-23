"""Promeut un utilisateur au rôle 'admin' (accès au tableau de bord des commissions).

Usage :
    python db/promouvoir_admin.py  ton.email@exemple.com
    python db/promouvoir_admin.py  +22890000000        (par téléphone)
"""
import os
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

if len(sys.argv) < 2:
    sys.exit("Donne l'email ou le téléphone du compte à promouvoir.")
identifiant = sys.argv[1]

with psycopg.connect(os.environ["DATABASE_URL"], autocommit=True) as conn:
    row = conn.execute(
        """UPDATE users SET role = 'admin'
           WHERE email = %s OR telephone = %s
           RETURNING nom_complet, COALESCE(email, telephone) AS contact""",
        (identifiant, identifiant),
    ).fetchone()

if row:
    print(f"OK - '{row[0]}' ({row[1]}) est maintenant administrateur.")
else:
    print(f"Aucun compte trouve pour : {identifiant}")
