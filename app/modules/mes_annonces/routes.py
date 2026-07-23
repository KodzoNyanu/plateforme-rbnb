"""Module PAGE : Espace propriétaire « Mes annonces »."""
from flask import Blueprint, render_template, request, redirect, url_for, flash, g, abort

from . import repository as repo
from ..deposer.repository import types_bien, quartiers
from ...security import proprietaire_required
from ...annonce_form import lire_et_valider
from ...uploads import enregistrer_photos, supprimer_fichiers

bp = Blueprint("mes_annonces", __name__, url_prefix="/mes-annonces", template_folder="templates")

STATUTS_AUTORISES = ("publiee", "archivee", "loue")


@bp.route("/")
@proprietaire_required
def index():
    annonces = repo.liste_pour_proprietaire(g.user["id"])
    return render_template("mes_annonces/index.html", annonces=annonces)


@bp.route("/<uuid:propriete_id>/modifier", methods=["GET", "POST"])
@proprietaire_required
def modifier(propriete_id):
    propriete_id = str(propriete_id)

    if request.method == "POST":
        d, erreurs = lire_et_valider(request.form)
        if erreurs:
            return render_template(
                "mes_annonces/edit.html",
                v=request.form, erreurs=erreurs, annonce_id=propriete_id,
                types=types_bien(), quartiers=quartiers(),
                photos=repo.photos_de(propriete_id, g.user["id"]),
            )
        photos_supprimer = request.form.getlist("supprimer_photo")
        # URLs des fichiers à effacer du disque (avant leur suppression en base)
        urls_a_effacer = [p["url"] for p in repo.photos_de(propriete_id, g.user["id"])
                          if str(p["id"]) in photos_supprimer]
        photos_ajout = enregistrer_photos(request.files.getlist("photos"))
        if not repo.mettre_a_jour(propriete_id, g.user["id"], d, photos_ajout, photos_supprimer):
            abort(404)
        supprimer_fichiers(urls_a_effacer)
        flash("Annonce mise à jour.", "succes")
        return redirect(url_for("mes_annonces.index"))

    # GET : pré-remplir avec les valeurs existantes
    annonce = repo.pour_edition(propriete_id, g.user["id"])
    if not annonce:
        abort(404)
    return render_template(
        "mes_annonces/edit.html",
        v=annonce, erreurs=[], annonce_id=propriete_id,
        types=types_bien(), quartiers=quartiers(),
        photos=repo.photos_de(propriete_id, g.user["id"]),
    )


@bp.route("/<uuid:propriete_id>/statut", methods=["POST"])
@proprietaire_required
def statut(propriete_id):
    cible = request.form.get("statut")
    if cible not in STATUTS_AUTORISES:
        abort(400)
    if not repo.changer_statut(str(propriete_id), g.user["id"], cible):
        abort(404)
    flash("Statut de l'annonce mis à jour.", "succes")
    return redirect(url_for("mes_annonces.index"))


@bp.route("/<uuid:propriete_id>/supprimer", methods=["POST"])
@proprietaire_required
def supprimer(propriete_id):
    pid = str(propriete_id)
    urls = [p["url"] for p in repo.photos_de(pid, g.user["id"])]
    if not repo.supprimer(pid, g.user["id"]):
        abort(404)
    supprimer_fichiers(urls)
    flash("Annonce supprimée.", "info")
    return redirect(url_for("mes_annonces.index"))
