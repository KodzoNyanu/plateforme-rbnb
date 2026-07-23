"""Requêtes SQL du module Authentification."""
from werkzeug.security import generate_password_hash

from ...db import query, get_db


def email_existe(email):
    return bool(email) and query("SELECT 1 FROM users WHERE email = %s", (email,), one=True) is not None


def telephone_existe(telephone):
    return bool(telephone) and query("SELECT 1 FROM users WHERE telephone = %s", (telephone,), one=True) is not None


def utilisateur_par_identifiant(identifiant):
    """Retrouve un utilisateur par son email OU son téléphone."""
    return query(
        "SELECT * FROM users WHERE email = %s OR telephone = %s",
        (identifiant, identifiant), one=True,
    )


def creer_utilisateur(nom, email, telephone, mot_de_passe, role):
    """Crée l'utilisateur (mot de passe haché) et, si propriétaire, sa fiche."""
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            """INSERT INTO users (nom_complet, email, telephone, password_hash, role)
               VALUES (%s, %s, %s, %s, %s) RETURNING id""",
            (nom, email, telephone, generate_password_hash(mot_de_passe), role),
        )
        user_id = cur.fetchone()["id"]
        if role == "proprietaire":
            cur.execute("INSERT INTO proprietaires (user_id) VALUES (%s)", (user_id,))
    db.commit()
    return user_id
