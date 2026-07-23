"""Accès à PostgreSQL.

Une connexion est ouverte par requête HTTP puis fermée automatiquement.
Le helper `query()` te permet d'écrire du SQL directement dans chaque module —
c'est volontaire : tu maîtrises SQL, autant l'exploiter.
"""
import psycopg
from psycopg.rows import dict_row
from flask import g, current_app


def get_db():
    """Retourne la connexion de la requête courante (la crée si besoin)."""
    if "db" not in g:
        g.db = psycopg.connect(
            current_app.config["DATABASE_URL"],
            row_factory=dict_row,  # chaque ligne = dict {colonne: valeur}
        )
    return g.db


def close_db(exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def query(sql, params=None, *, one=False, commit=False):
    """Exécute une requête SQL.

    - SELECT  -> renvoie une liste de dicts (ou un seul dict si one=True).
    - INSERT/UPDATE/DELETE -> passer commit=True ; renvoie la ligne RETURNING si présente.
    """
    db = get_db()
    with db.cursor() as cur:
        cur.execute(sql, params or ())
        rows = cur.fetchall() if cur.description else None
        if commit:
            db.commit()
    if rows is None:
        return None
    if one:
        return rows[0] if rows else None
    return rows


def init_app(app):
    """Branche la fermeture automatique de la connexion en fin de requête."""
    app.teardown_appcontext(close_db)
