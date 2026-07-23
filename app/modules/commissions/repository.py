"""Requêtes SQL du tableau de bord des commissions (administration)."""
from ...db import query


def kpis():
    """Indicateurs globaux + revenus du mois en cours."""
    return query(
        """
        SELECT
            COALESCE(SUM(montant) FILTER (WHERE statut = 'percue'), 0)  AS total_percu,
            COALESCE(SUM(montant) FILTER (WHERE statut = 'due'),    0)  AS total_attente,
            COUNT(*) FILTER (WHERE statut = 'percue')                   AS nb_percues,
            COUNT(*)                                                    AS nb_total,
            COALESCE(SUM(montant) FILTER (
                WHERE statut = 'percue'
                  AND date_trunc('month', created_at) = date_trunc('month', now())
            ), 0) AS percu_ce_mois
        FROM commissions
        """,
        one=True,
    )


def par_mode():
    """Répartition des commissions perçues par type de location."""
    return query(
        """
        SELECT r.mode_location,
               COALESCE(SUM(c.montant) FILTER (WHERE c.statut = 'percue'), 0) AS total,
               COUNT(*) FILTER (WHERE c.statut = 'percue') AS nb
        FROM commissions c
        JOIN reservations r ON r.id = c.reservation_id
        GROUP BY r.mode_location
        ORDER BY total DESC
        """
    )


def evolution_mensuelle():
    """Commissions perçues sur les 6 derniers mois."""
    return query(
        """
        SELECT to_char(date_trunc('month', created_at), 'YYYY-MM') AS mois,
               COALESCE(SUM(montant) FILTER (WHERE statut = 'percue'), 0) AS total
        FROM commissions
        WHERE created_at >= date_trunc('month', now()) - interval '5 months'
        GROUP BY 1
        ORDER BY 1
        """
    )


def detail(limit=50):
    """Dernières commissions avec le contexte de la réservation."""
    return query(
        """
        SELECT c.montant, c.taux, c.statut, c.created_at,
               r.mode_location, r.montant_total, r.montant_en_ligne,
               p.titre, q.nom AS quartier, u.nom_complet AS locataire
        FROM commissions c
        JOIN reservations   r ON r.id = c.reservation_id
        JOIN proprietes     p ON p.id = r.propriete_id
        JOIN quartiers      q ON q.id = p.quartier_id
        JOIN users          u ON u.id = r.locataire_id
        ORDER BY c.created_at DESC
        LIMIT %s
        """,
        (limit,),
    )
