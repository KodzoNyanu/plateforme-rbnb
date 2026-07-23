"""Requêtes SQL du module Recherche multicritères.

On construit la clause WHERE dynamiquement selon les filtres fournis,
avec des requêtes paramétrées (pas de concaténation de valeurs = pas d'injection SQL).
"""
from ...db import query

_SELECT = """
    SELECT p.id, p.titre, p.nb_chambres, p.nb_salons, p.surface_m2, p.meuble,
           p.mode_location, pt.libelle AS type_bien,
           q.nom AS quartier, q.slug AS quartier_slug, c.nom AS commune, vl.nom AS ville,
           tm.montant AS prix_mois, tn.montant AS prix_nuit,
           (SELECT url FROM propriete_photos ph
             WHERE ph.propriete_id = p.id ORDER BY est_couverture DESC, ordre LIMIT 1) AS photo
    FROM proprietes p
    JOIN property_types pt ON pt.id = p.property_type_id
    JOIN quartiers q  ON q.id = p.quartier_id
    JOIN communes  c  ON c.id = q.commune_id
    JOIN villes    vl ON vl.id = c.ville_id
    LEFT JOIN tarifs tm ON tm.propriete_id = p.id AND tm.unite = 'mois' AND tm.actif
    LEFT JOIN tarifs tn ON tn.propriete_id = p.id AND tn.unite = 'nuit' AND tn.actif
"""


def rechercher(filtres):
    where = ["p.statut = 'publiee'"]
    params = []

    if filtres.get("ville_id"):
        where.append("vl.id = %s"); params.append(filtres["ville_id"])
    if filtres.get("quartier_id"):
        where.append("q.id = %s"); params.append(filtres["quartier_id"])
    if filtres.get("type_id"):
        where.append("pt.id = %s"); params.append(filtres["type_id"])
    if filtres.get("nb_chambres"):
        where.append("p.nb_chambres >= %s"); params.append(filtres["nb_chambres"])
    if filtres.get("meuble"):
        where.append("p.meuble = true")

    # Mode de location : filtre sur le tarif correspondant
    mode = filtres.get("mode")
    if mode == "mois":
        where.append("tm.montant IS NOT NULL")
        if filtres.get("prix_max"):
            where.append("tm.montant <= %s"); params.append(filtres["prix_max"])
    elif mode == "nuit":
        where.append("tn.montant IS NOT NULL")
        if filtres.get("prix_max"):
            where.append("tn.montant <= %s"); params.append(filtres["prix_max"])

    sql = _SELECT + " WHERE " + " AND ".join(where) + " ORDER BY p.created_at DESC LIMIT 60"
    return query(sql, params)


# ── Données pour alimenter les menus déroulants du formulaire ──
def villes():
    return query("SELECT id, nom FROM villes ORDER BY nom")

def quartiers():
    return query("""
        SELECT q.id, q.nom, c.nom AS commune FROM quartiers q
        JOIN communes c ON c.id = q.commune_id ORDER BY q.nom
    """)

def types():
    return query("SELECT id, libelle FROM property_types ORDER BY libelle")
