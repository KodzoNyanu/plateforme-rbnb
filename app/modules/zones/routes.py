"""Module PAGE : Guide des quartiers & comparateur de zones."""
from flask import Blueprint, render_template, request, abort

from . import repository as repo

bp = Blueprint("zones", __name__, url_prefix="/zones", template_folder="templates")


@bp.route("/")
def index():
    """Liste des quartiers + sélection pour comparaison."""
    quartiers = repo.liste_quartiers()
    return render_template("zones/index.html", quartiers=quartiers)


@bp.route("/<slug>")
def detail(slug):
    """Fiche détaillée d'un quartier : scores par critère + loyer moyen réel."""
    quartier = repo.quartier_par_slug(slug)
    if not quartier:
        abort(404)
    scores = repo.scores_du_quartier(quartier["id"])
    loyer = repo.loyer_moyen_calcule(quartier["id"])
    return render_template("zones/detail.html", quartier=quartier, scores=scores, loyer=loyer)


@bp.route("/comparer")
def comparer():
    """Comparaison côte à côte de 2 quartiers (via ?a=slug&b=slug)."""
    quartiers = repo.liste_quartiers()
    slug_a, slug_b = request.args.get("a"), request.args.get("b")
    colonnes = []
    for slug in (slug_a, slug_b):
        if slug:
            q = repo.quartier_par_slug(slug)
            if q:
                colonnes.append({
                    "quartier": q,
                    "scores": {s["code"]: s for s in repo.scores_du_quartier(q["id"])},
                    "loyer": repo.loyer_moyen_calcule(q["id"]),
                })
    # Union des critères présents pour aligner les lignes du tableau
    criteres = []
    if colonnes:
        vus = set()
        for col in colonnes:
            for code, s in col["scores"].items():
                if code not in vus:
                    vus.add(code)
                    criteres.append(s)
    return render_template(
        "zones/comparer.html",
        quartiers=quartiers, colonnes=colonnes, criteres=criteres,
        slug_a=slug_a, slug_b=slug_b,
    )
