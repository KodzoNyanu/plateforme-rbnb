"""Requêtes SQL de la page d'accueil."""
from ...db import query


def quartiers_a_decouvrir(limit=6):
    return query(
        """
        SELECT q.nom, q.slug, q.description, c.nom AS commune, vl.nom AS ville
        FROM quartiers q
        JOIN communes c  ON c.id = q.commune_id
        JOIN villes  vl ON vl.id = c.ville_id
        ORDER BY q.nom
        LIMIT %s
        """,
        (limit,),
    )


def logements_a_la_une(limit=6):
    """Logements publiés AVEC photo, classés par nombre de réservations confirmées
    (les plus loués d'abord), puis par nouveauté."""
    return query(
        """
        SELECT p.id, p.titre, pt.libelle AS type_bien,
               q.nom AS quartier, c.nom AS commune,
               tm.montant AS prix_mois, tn.montant AS prix_nuit,
               ph.url AS photo,
               COUNT(r.id) FILTER (WHERE r.statut = 'confirmee') AS nb_resa
        FROM proprietes p
        JOIN property_types pt ON pt.id = p.property_type_id
        JOIN quartiers q  ON q.id = p.quartier_id
        JOIN communes  c  ON c.id = q.commune_id
        JOIN propriete_photos ph
             ON ph.propriete_id = p.id AND ph.est_couverture
        LEFT JOIN tarifs tm ON tm.propriete_id = p.id AND tm.unite = 'mois' AND tm.actif
        LEFT JOIN tarifs tn ON tn.propriete_id = p.id AND tn.unite = 'nuit' AND tn.actif
        LEFT JOIN reservations r ON r.propriete_id = p.id
        WHERE p.statut = 'publiee'
        GROUP BY p.id, pt.libelle, q.nom, c.nom, tm.montant, tn.montant, ph.url
        ORDER BY nb_resa DESC, p.created_at DESC
        LIMIT %s
        """,
        (limit,),
    )
