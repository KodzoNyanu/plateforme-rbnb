"""Module PAGE : Accueil."""
from flask import Blueprint, render_template

from . import repository as repo

bp = Blueprint("home", __name__, template_folder="templates")


@bp.route("/")
def index():
    return render_template(
        "home/index.html",
        quartiers=repo.quartiers_a_decouvrir(),
        carrousel=repo.logements_a_la_une(),
    )
