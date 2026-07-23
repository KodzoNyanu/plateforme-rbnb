"""Module PAGE : Tableau de bord des commissions (administration)."""
from flask import Blueprint, render_template

from . import repository as repo
from ...security import admin_required

bp = Blueprint("commissions", __name__, url_prefix="/admin/commissions", template_folder="templates")


@bp.route("/")
@admin_required
def index():
    return render_template(
        "commissions/index.html",
        k=repo.kpis(),
        par_mode=repo.par_mode(),
        evolution=repo.evolution_mensuelle(),
        detail=repo.detail(),
    )
