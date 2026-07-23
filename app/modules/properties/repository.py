"""Requêtes SQL du module Annonces."""
from ...db import query

# SELECT commun : une annonce + son type, sa localisation et ses 2 tarifs
_BASE_SELECT = """
    SELECT p.id, p.proprietaire_id, p.titre, p.nb_chambres, p.nb_salons, p.surface_m2, p.meuble,
           p.mode_location, pt.libelle AS type_bien,
           q.nom AS quartier, q.slug AS quartier_slug, c.nom AS commune, vl.nom AS ville,
           tm.montant AS prix_mois, tm.caution_mois,
           tn.montant AS prix_nuit, tn.min_nuits, tn.frais_menage,
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


def liste(limit=30):
    return query(
        _BASE_SELECT + " WHERE p.statut = 'publiee' ORDER BY p.created_at DESC LIMIT %s",
        (limit,),
    )


def detail(propriete_id):
    return query(
        _BASE_SELECT + " WHERE p.id = %s",
        (propriete_id,),
        one=True,
    )


def photos(propriete_id):
    return query(
        """SELECT url FROM propriete_photos
           WHERE propriete_id = %s ORDER BY est_couverture DESC, ordre""",
        (propriete_id,),
    )
