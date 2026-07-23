"""Requêtes SQL du module Zones (guide / comparateur de quartiers)."""
from ...db import query


def liste_quartiers():
    return query(
        """
        SELECT q.id, q.nom, q.slug, c.nom AS commune, vl.nom AS ville
        FROM quartiers q
        JOIN communes c  ON c.id = q.commune_id
        JOIN villes  vl ON vl.id = c.ville_id
        ORDER BY vl.nom, c.nom, q.nom
        """
    )


def quartier_par_slug(slug):
    return query(
        """
        SELECT q.id, q.nom, q.slug, q.description,
               c.nom AS commune, vl.nom AS ville, r.nom AS region
        FROM quartiers q
        JOIN communes c  ON c.id = q.commune_id
        JOIN villes  vl ON vl.id = c.ville_id
        JOIN regions r  ON r.id = vl.region_id
        WHERE q.slug = %s
        """,
        (slug,),
        one=True,
    )


def scores_du_quartier(quartier_id):
    """Renvoie les critères notés pour un quartier."""
    return query(
        """
        SELECT cr.code, cr.libelle, cr.categorie, cr.type_valeur, cr.unite,
               zs.score, zs.valeur_num, zs.valeur_texte
        FROM criteres cr
        LEFT JOIN zone_scores zs
               ON zs.critere_id = cr.id AND zs.quartier_id = %s
        WHERE cr.code <> 'loyer_moyen'   -- affiché à part (calculé depuis les annonces)
        ORDER BY cr.categorie, cr.libelle
        """,
        (quartier_id,),
    )


def loyer_moyen_calcule(quartier_id):
    """Loyer mensuel moyen réel, calculé depuis les annonces publiées du quartier."""
    return query(
        """
        SELECT ROUND(AVG(t.montant)) AS loyer_moyen, COUNT(*) AS nb_biens
        FROM proprietes p
        JOIN tarifs t ON t.propriete_id = p.id AND t.unite = 'mois' AND t.actif
        WHERE p.quartier_id = %s AND p.statut = 'publiee'
        """,
        (quartier_id,),
        one=True,
    )
