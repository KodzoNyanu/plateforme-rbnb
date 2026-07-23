"""Module PAGE : Annonces (liste + détail)."""
from datetime import date

from flask import Blueprint, render_template, abort

from . import repository as repo

bp = Blueprint("properties", __name__, url_prefix="/annonces", template_folder="templates")


@bp.route("/")
def index():
    annonces = repo.liste()
    return render_template("properties/index.html", annonces=annonces)


@bp.route("/<uuid:propriete_id>")
def detail(propriete_id):
    annonce = repo.detail(str(propriete_id))
    if not annonce:
        abort(404)
    return render_template(
        "properties/detail.html",
        a=annonce,
        photos=repo.photos(str(propriete_id)),
        aujourd_hui=date.today().isoformat(),
    )
