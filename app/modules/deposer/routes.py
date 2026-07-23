"""Module PAGE : Dépôt d'annonce (réservé aux propriétaires connectés)."""
from flask import Blueprint, render_template, request, redirect, url_for, g

from . import repository as repo
from ...security import proprietaire_required
from ...annonce_form import lire_et_valider
from ...uploads import enregistrer_photos

bp = Blueprint("deposer", __name__, url_prefix="/deposer", template_folder="templates")


@bp.route("/", methods=["GET", "POST"])
@proprietaire_required
def index():
    contexte = {
        "types": repo.types_bien(),
        "quartiers": repo.quartiers(),
        "v": request.form,   # valeurs pour re-remplir en cas d'erreur
        "erreurs": [],
    }

    if request.method == "POST":
        d, erreurs = lire_et_valider(request.form)
        if erreurs:
            contexte["erreurs"] = erreurs
            return render_template("deposer/index.html", **contexte)

        photos = enregistrer_photos(request.files.getlist("photos"))
        propriete_id = repo.creer_annonce(d, g.user["id"], photos)
        return redirect(url_for("properties.detail", propriete_id=propriete_id))

    return render_template("deposer/index.html", **contexte)
