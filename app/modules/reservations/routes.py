"""Module PAGE : Réservation en ligne.

Modèle : le locataire paie EN LIGNE des « frais de réservation » (= la commission
de la plateforme). Cela confirme la réservation et débloque les coordonnées du
propriétaire. Le reste (loyer/séjour) se règle sur place.

NB : le paiement est SIMULÉ pour l'instant (intégration Mobile Money / PayPal à venir).
"""
from datetime import date

from flask import Blueprint, render_template, request, redirect, url_for, flash, g, abort, current_app

from . import repository as repo
from ..properties.repository import detail as propriete_detail
from ...security import login_required
from ... import cinetpay

bp = Blueprint("reservations", __name__, url_prefix="/reservations", template_folder="templates")


def _calculer(mode_reservation, prop, date_debut, date_fin):
    """Calcule les montants + la commission. Retourne (m, erreurs)."""
    erreurs = []
    m = {"date_fin": None, "nb_unites": 1}

    if mode_reservation == "nuit":
        m["mode_location"] = "courte_duree"
        if not prop["prix_nuit"]:
            return None, ["Ce bien n'est pas disponible à la nuitée."]
        if not date_fin or date_fin <= date_debut:
            erreurs.append("La date de départ doit être après la date d'arrivée.")
        else:
            nb_nuits = (date_fin - date_debut).days
            mini = prop["min_nuits"] or 1
            if nb_nuits < mini:
                erreurs.append(f"Séjour minimum : {mini} nuit(s).")
            m["nb_unites"] = nb_nuits
            m["date_fin"] = date_fin
        if erreurs:
            return None, erreurs
        prix_nuit = int(prop["prix_nuit"])
        frais_menage = int(prop["frais_menage"] or 0)
        m["total"] = m["nb_unites"] * prix_nuit + frais_menage
    elif mode_reservation == "mois":
        m["mode_location"] = "longue_duree"
        if not prop["prix_mois"]:
            return None, ["Ce bien n'est pas disponible à la location au mois."]
        m["total"] = int(prop["prix_mois"])
    else:
        return None, ["Mode de réservation invalide."]

    m["date_debut"] = date_debut

    # Frais de réservation en ligne (= commission de la plateforme)
    param = repo.parametre_commission(m["mode_location"])
    if not param:
        return None, ["Barème de commission indisponible. Contactez le support."]
    if param["type_frais"] == "pourcentage":
        m["online"] = round(m["total"] * float(param["valeur"]) / 100)
        m["commission_taux"] = float(param["valeur"])
    else:  # fixe
        m["online"] = int(param["valeur"])
        m["commission_taux"] = 0

    # Longue durée : le loyer se règle au propriétaire, les frais sont EN PLUS.
    # Courte durée : l'acompte en ligne se déduit du total.
    if m["mode_location"] == "longue_duree":
        m["sur_place"] = m["total"]
    else:
        m["sur_place"] = m["total"] - m["online"]

    m["commission_base"] = m["total"]
    m["commission_montant"] = m["online"]
    return m, []


@bp.route("/creer", methods=["POST"])
@login_required
def creer():
    prop = propriete_detail(request.form.get("propriete_id", ""))
    if not prop:
        abort(404)
    if str(prop["proprietaire_id"]) == str(g.user["id"]):
        flash("Vous ne pouvez pas réserver votre propre annonce.", "erreur")
        return redirect(url_for("properties.detail", propriete_id=prop["id"]))

    retour = redirect(url_for("properties.detail", propriete_id=prop["id"]))
    mode_reservation = request.form.get("mode_reservation")

    try:
        date_debut = date.fromisoformat(request.form.get("date_debut", ""))
    except ValueError:
        flash("Renseigne une date valide.", "erreur")
        return retour
    date_fin = None
    if request.form.get("date_fin"):
        try:
            date_fin = date.fromisoformat(request.form["date_fin"])
        except ValueError:
            flash("Date de départ invalide.", "erreur")
            return retour
    if date_debut < date.today():
        flash("La date ne peut pas être dans le passé.", "erreur")
        return retour

    m, erreurs = _calculer(mode_reservation, prop, date_debut, date_fin)
    if erreurs:
        for e in erreurs:
            flash(e, "erreur")
        return retour

    reservation_id = repo.creer_reservation(g.user["id"], prop["id"], m)
    return redirect(url_for("reservations.recap", reservation_id=reservation_id))


@bp.route("/<uuid:reservation_id>")
@login_required
def recap(reservation_id):
    r = repo.pour_locataire(str(reservation_id), g.user["id"])
    if not r:
        abort(404)
    return render_template("reservations/recap.html", r=r, cinetpay_actif=cinetpay.is_configured())


@bp.route("/<uuid:reservation_id>/payer", methods=["POST"])
@login_required
def payer(reservation_id):
    rid = str(reservation_id)
    r = repo.pour_locataire(rid, g.user["id"])
    if not r or r["statut"] != "en_attente_paiement":
        flash("Cette réservation ne peut plus être payée.", "erreur")
        return redirect(url_for("reservations.recap", reservation_id=rid))

    # ── Paiement réel via CinetPay ──
    if cinetpay.is_configured():
        transaction_id = repo.creer_tentative_paiement(rid, g.user["id"])
        if not transaction_id:
            flash("Cette réservation ne peut plus être payée.", "erreur")
            return redirect(url_for("reservations.recap", reservation_id=rid))
        try:
            url = cinetpay.initier_paiement(
                transaction_id=transaction_id,
                montant=int(r["montant_en_ligne"]),
                description=f"Frais de reservation - {r['titre']}",
                client=g.user,
                notify_url=url_for("reservations.cinetpay_notification", _external=True),
                return_url=url_for("reservations.cinetpay_retour", _external=True),
            )
        except Exception as exc:                     # noqa: BLE001
            current_app.logger.warning("CinetPay init: %s", exc)
            flash("Le service de paiement est momentanément indisponible. Réessaie plus tard.", "erreur")
            return redirect(url_for("reservations.recap", reservation_id=rid))
        return redirect(url)

    # ── Repli : paiement simulé (CinetPay non configuré) ──
    methode = request.form.get("methode")
    if methode not in ("paypal", "mobile_money"):
        methode = "mobile_money"
    repo.marquer_payee(rid, g.user["id"], methode)
    flash("Paiement confirmé (simulation). Les coordonnées du propriétaire sont débloquées.", "succes")
    return redirect(url_for("reservations.recap", reservation_id=rid))


@bp.route("/cinetpay/retour", methods=["GET", "POST"])
def cinetpay_retour():
    """Retour navigateur après paiement : on revérifie le statut réel avant de confirmer."""
    txn = (request.values.get("transaction_id") or request.values.get("cpm_trans_id"))
    if txn and cinetpay.verifier_paiement(txn) == "ACCEPTED":
        rid = repo.confirmer_paiement(txn)
        if rid:
            flash("Paiement confirmé ! Les coordonnées du propriétaire sont débloquées.", "succes")
            return redirect(url_for("reservations.recap", reservation_id=rid))
    flash("Le paiement n'a pas abouti ou a été annulé.", "erreur")
    return redirect(url_for("reservations.index"))


@bp.route("/cinetpay/notification", methods=["POST"])
def cinetpay_notification():
    """Webhook serveur-à-serveur de CinetPay (source de vérité)."""
    txn = request.form.get("cpm_trans_id") or request.form.get("transaction_id")
    if txn and cinetpay.verifier_paiement(txn) == "ACCEPTED":
        repo.confirmer_paiement(txn)
    return ("", 200)


@bp.route("/")
@login_required
def index():
    return render_template(
        "reservations/index.html",
        reservations=repo.liste_pour_locataire(g.user["id"]),
    )
