"""Module PAGE : Authentification (inscription, connexion, déconnexion)."""
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, g
from werkzeug.security import check_password_hash

from . import repository as repo

bp = Blueprint("auth", __name__, url_prefix="/auth", template_folder="templates")


def _url_suivante():
    """Redirection après connexion : vers ?next= si présent et interne, sinon accueil."""
    nxt = request.args.get("next") or request.form.get("next")
    if nxt and nxt.startswith("/"):
        return nxt
    return url_for("home.index")


@bp.route("/inscription", methods=["GET", "POST"])
def register():
    if g.user:
        return redirect(url_for("home.index"))

    form = request.form
    erreurs = []
    if request.method == "POST":
        nom       = (form.get("nom") or "").strip()
        email     = (form.get("email") or "").strip().lower() or None
        telephone = (form.get("telephone") or "").strip() or None
        mdp       = form.get("mot_de_passe") or ""
        mdp2      = form.get("mot_de_passe2") or ""
        role      = form.get("role") or ""

        if not nom:
            erreurs.append("Indique ton nom complet.")
        if not email and not telephone:
            erreurs.append("Renseigne au moins un email ou un numéro de téléphone.")
        if role not in ("locataire", "proprietaire"):
            erreurs.append("Choisis un type de compte.")
        if len(mdp) < 8:
            erreurs.append("Le mot de passe doit faire au moins 8 caractères.")
        if mdp != mdp2:
            erreurs.append("Les deux mots de passe ne correspondent pas.")
        if repo.email_existe(email):
            erreurs.append("Cet email est déjà utilisé.")
        if repo.telephone_existe(telephone):
            erreurs.append("Ce numéro de téléphone est déjà utilisé.")

        if not erreurs:
            user_id = repo.creer_utilisateur(nom, email, telephone, mdp, role)
            session.clear()
            session["user_id"] = str(user_id)
            flash("Bienvenue ! Ton compte a été créé.", "succes")
            return redirect(_url_suivante())

    return render_template("auth/register.html", erreurs=erreurs, form=form)


@bp.route("/connexion", methods=["GET", "POST"])
def login():
    if g.user:
        return redirect(url_for("home.index"))

    form = request.form
    erreurs = []
    if request.method == "POST":
        identifiant = (form.get("identifiant") or "").strip().lower()
        mdp = form.get("mot_de_passe") or ""

        user = repo.utilisateur_par_identifiant(identifiant) if identifiant else None
        if not user or not user["password_hash"] or not check_password_hash(user["password_hash"], mdp):
            erreurs.append("Identifiant ou mot de passe incorrect.")
        else:
            session.clear()
            session["user_id"] = str(user["id"])
            flash(f"Content de te revoir, {user['nom_complet'].split(' ')[0]} !", "succes")
            return redirect(_url_suivante())

    return render_template("auth/login.html", erreurs=erreurs, form=form)


@bp.route("/deconnexion")
def logout():
    session.clear()
    flash("Tu es déconnecté.", "info")
    return redirect(url_for("home.index"))
