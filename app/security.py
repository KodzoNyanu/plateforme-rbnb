"""Socle de sécurité partagé : session, utilisateur courant, protections d'accès.

- `current_user` est disponible dans TOUS les templates (via un context processor).
- `g.user` contient l'utilisateur connecté (ou None) pendant chaque requête.
- Décorateurs : @login_required et @proprietaire_required pour protéger des pages.
"""
import functools

from flask import g, session, redirect, url_for, flash, request

from .db import query


def charger_utilisateur():
    """Avant chaque requête : place l'utilisateur connecté dans g.user."""
    user_id = session.get("user_id")
    g.user = None
    if user_id:
        g.user = query(
            "SELECT id, nom_complet, email, telephone, role FROM users WHERE id = %s",
            (user_id,), one=True,
        )


def login_required(view):
    """Réserve une page aux utilisateurs connectés."""
    @functools.wraps(view)
    def wrapped(**kwargs):
        if g.user is None:
            flash("Connecte-toi pour accéder à cette page.", "info")
            return redirect(url_for("auth.login", next=request.path))
        return view(**kwargs)
    return wrapped


def proprietaire_required(view):
    """Réserve une page aux propriétaires (et agences/admin)."""
    @functools.wraps(view)
    def wrapped(**kwargs):
        if g.user is None:
            flash("Connecte-toi pour accéder à cette page.", "info")
            return redirect(url_for("auth.login", next=request.path))
        if g.user["role"] not in ("proprietaire", "agence", "admin"):
            flash("Cette page est réservée aux propriétaires.", "erreur")
            return redirect(url_for("home.index"))
        return view(**kwargs)
    return wrapped


def admin_required(view):
    """Réserve une page à l'administration de la plateforme."""
    @functools.wraps(view)
    def wrapped(**kwargs):
        if g.user is None:
            flash("Connecte-toi pour accéder à cette page.", "info")
            return redirect(url_for("auth.login", next=request.path))
        if g.user["role"] != "admin":
            flash("Accès réservé à l'administration.", "erreur")
            return redirect(url_for("home.index"))
        return view(**kwargs)
    return wrapped


def init_app(app):
    app.before_request(charger_utilisateur)

    @app.context_processor
    def injecter_utilisateur():
        return {"current_user": g.get("user")}
