"""Lecture + validation des champs d'une annonce.

Partagé par le dépôt (module `deposer`) et la modification (module `mes_annonces`).
Retourne un tuple (données_nettoyées, liste_d_erreurs).
"""


def _num(form, nom, entier=False):
    """Convertit un champ en nombre, ou None si vide/invalide."""
    val = (form.get(nom) or "").strip().replace(" ", "")
    if not val:
        return None
    try:
        return int(val) if entier else float(val)
    except ValueError:
        return None


def lire_et_valider(form):
    d = {
        "titre":          (form.get("titre") or "").strip(),
        "description":    (form.get("description") or "").strip() or None,
        "type_id":        _num(form, "type_id", entier=True),
        "quartier_id":    _num(form, "quartier_id", entier=True),
        "adresse":        (form.get("adresse") or "").strip() or None,
        "nb_chambres":    _num(form, "nb_chambres", entier=True) or 0,
        "nb_salons":      _num(form, "nb_salons", entier=True) or 1,
        "nb_salles_bain": _num(form, "nb_salles_bain", entier=True) or 1,
        "surface_m2":     _num(form, "surface_m2"),
        "etage":          _num(form, "etage", entier=True),
        "meuble":         form.get("meuble") == "on",
        "mode_location":  form.get("mode_location") or "",
        "capacite_voyageurs": _num(form, "capacite_voyageurs", entier=True),
        "prix_mois":      _num(form, "prix_mois", entier=True),
        "caution_mois":   _num(form, "caution_mois", entier=True),
        "prix_nuit":      _num(form, "prix_nuit", entier=True),
        "min_nuits":      _num(form, "min_nuits", entier=True),
    }

    erreurs = []
    if not d["titre"]:
        erreurs.append("Le titre est obligatoire.")
    if not d["type_id"]:
        erreurs.append("Choisis un type de bien.")
    if not d["quartier_id"]:
        erreurs.append("Choisis un quartier.")
    if d["mode_location"] not in ("longue_duree", "courte_duree", "les_deux"):
        erreurs.append("Choisis un mode de location.")
    else:
        besoin_mois = d["mode_location"] in ("longue_duree", "les_deux")
        besoin_nuit = d["mode_location"] in ("courte_duree", "les_deux")
        if besoin_mois and not d["prix_mois"]:
            erreurs.append("Indique le prix mensuel (location au mois).")
        if besoin_nuit and not d["prix_nuit"]:
            erreurs.append("Indique le prix par nuitée (location courte durée).")
        # On ignore le tarif non pertinent selon le mode choisi
        if not besoin_mois:
            d["prix_mois"] = d["caution_mois"] = None
        if not besoin_nuit:
            d["prix_nuit"] = d["min_nuits"] = None

    return d, erreurs
