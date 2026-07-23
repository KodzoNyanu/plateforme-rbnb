"""Module PAGE : Recherche multicritères."""
from flask import Blueprint, render_template, request

from . import repository as repo

bp = Blueprint("search", __name__, url_prefix="/recherche", template_folder="templates")


def _int(nom):
    """Lit un paramètre entier depuis l'URL, ou None si vide/invalide."""
    val = request.args.get(nom, "").strip()
    return int(val) if val.isdigit() else None


@bp.route("/")
def index():
    filtres = {
        "ville_id":    _int("ville_id"),
        "quartier_id": _int("quartier_id"),
        "type_id":     _int("type_id"),
        "nb_chambres": _int("nb_chambres"),
        "prix_max":    _int("prix_max"),
        "mode":        request.args.get("mode") or None,
        "meuble":      request.args.get("meuble") == "1",
    }
    # On ne lance la recherche que si au moins un filtre est actif
    a_cherche = any(v for v in filtres.values())
    resultats = repo.rechercher(filtres) if a_cherche else None

    return render_template(
        "search/index.html",
        resultats=resultats, filtres=filtres, a_cherche=a_cherche,
        villes=repo.villes(), quartiers=repo.quartiers(), types=repo.types(),
    )
