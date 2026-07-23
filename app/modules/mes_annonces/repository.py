"""Requêtes SQL du module « Mes annonces ».

Toutes les opérations filtrent sur `proprietaire_id` : un propriétaire ne peut
voir/modifier/supprimer QUE ses propres annonces.
"""
from ...db import query, get_db


def liste_pour_proprietaire(proprietaire_id):
    return query(
        """
        SELECT p.id, p.titre, p.statut, p.nb_chambres, p.meuble, p.created_at,
               pt.libelle AS type_bien,
               q.nom AS quartier, c.nom AS commune,
               tm.montant AS prix_mois, tn.montant AS prix_nuit,
               (SELECT url FROM propriete_photos ph
                 WHERE ph.propriete_id = p.id ORDER BY est_couverture DESC, ordre LIMIT 1) AS photo
        FROM proprietes p
        JOIN property_types pt ON pt.id = p.property_type_id
        JOIN quartiers q  ON q.id = p.quartier_id
        JOIN communes  c  ON c.id = q.commune_id
        LEFT JOIN tarifs tm ON tm.propriete_id = p.id AND tm.unite = 'mois' AND tm.actif
        LEFT JOIN tarifs tn ON tn.propriete_id = p.id AND tn.unite = 'nuit' AND tn.actif
        WHERE p.proprietaire_id = %s
        ORDER BY p.created_at DESC
        """,
        (proprietaire_id,),
    )


def pour_edition(propriete_id, proprietaire_id):
    """Charge une annonce (si elle appartient au propriétaire) au format du formulaire."""
    return query(
        """
        SELECT p.id, p.titre, p.description,
               p.property_type_id AS type_id, p.quartier_id,
               p.adresse_precise AS adresse,
               p.nb_chambres, p.nb_salons, p.nb_salles_bain, p.surface_m2, p.etage,
               p.meuble, p.mode_location, p.capacite_voyageurs,
               tm.montant AS prix_mois, tm.caution_mois,
               tn.montant AS prix_nuit, tn.min_nuits,
               (SELECT url FROM propriete_photos ph
                 WHERE ph.propriete_id = p.id ORDER BY est_couverture DESC, ordre LIMIT 1) AS photo_url
        FROM proprietes p
        LEFT JOIN tarifs tm ON tm.propriete_id = p.id AND tm.unite = 'mois'
        LEFT JOIN tarifs tn ON tn.propriete_id = p.id AND tn.unite = 'nuit'
        WHERE p.id = %s AND p.proprietaire_id = %s
        """,
        (propriete_id, proprietaire_id), one=True,
    )


def photos_de(propriete_id, proprietaire_id):
    """Photos d'une annonce (si elle appartient au propriétaire)."""
    return query(
        """SELECT ph.id, ph.url
           FROM propriete_photos ph
           JOIN proprietes p ON p.id = ph.propriete_id
           WHERE ph.propriete_id = %s AND p.proprietaire_id = %s
           ORDER BY ph.est_couverture DESC, ph.ordre""",
        (propriete_id, proprietaire_id),
    )


def mettre_a_jour(propriete_id, proprietaire_id, d, photos_ajout=None, photos_supprimer=None):
    """Met à jour l'annonce + ses tarifs + ses photos. Retourne False si pas le propriétaire."""
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            """
            UPDATE proprietes SET
                property_type_id = %(type)s, titre = %(titre)s, description = %(desc)s,
                quartier_id = %(quartier)s, adresse_precise = %(adresse)s,
                nb_chambres = %(ch)s, nb_salons = %(sal)s, nb_salles_bain = %(sdb)s,
                surface_m2 = %(surface)s, etage = %(etage)s, meuble = %(meuble)s,
                mode_location = %(mode)s, capacite_voyageurs = %(cap)s, updated_at = now()
            WHERE id = %(id)s AND proprietaire_id = %(prop)s
            """,
            {
                "type": d["type_id"], "titre": d["titre"], "desc": d["description"],
                "quartier": d["quartier_id"], "adresse": d["adresse"],
                "ch": d["nb_chambres"], "sal": d["nb_salons"], "sdb": d["nb_salles_bain"],
                "surface": d["surface_m2"], "etage": d["etage"], "meuble": d["meuble"],
                "mode": d["mode_location"], "cap": d["capacite_voyageurs"],
                "id": propriete_id, "prop": proprietaire_id,
            },
        )
        if cur.rowcount == 0:
            db.rollback()
            return False

        # Remplacement des tarifs (simple et fiable en cas de changement de mode)
        cur.execute("DELETE FROM tarifs WHERE propriete_id = %s", (propriete_id,))
        if d["prix_mois"] is not None:
            cur.execute(
                """INSERT INTO tarifs (propriete_id, unite, montant, caution_mois)
                   VALUES (%s, 'mois', %s, %s)""",
                (propriete_id, d["prix_mois"], d["caution_mois"]),
            )
        if d["prix_nuit"] is not None:
            cur.execute(
                """INSERT INTO tarifs (propriete_id, unite, montant, min_nuits)
                   VALUES (%s, 'nuit', %s, %s)""",
                (propriete_id, d["prix_nuit"], d["min_nuits"]),
            )
        # Suppression des photos cochées (uniquement celles de ce bien)
        if photos_supprimer:
            cur.execute(
                "DELETE FROM propriete_photos WHERE propriete_id = %s AND id::text = ANY(%s)",
                (propriete_id, list(photos_supprimer)),
            )
        # Ajout des nouvelles photos (à la suite)
        cur.execute(
            "SELECT COALESCE(MAX(ordre), -1) AS m FROM propriete_photos WHERE propriete_id = %s",
            (propriete_id,),
        )
        ordre = cur.fetchone()["m"] + 1
        for url in (photos_ajout or []):
            cur.execute(
                "INSERT INTO propriete_photos (propriete_id, url, ordre) VALUES (%s, %s, %s)",
                (propriete_id, url, ordre),
            )
            ordre += 1
        # Une seule photo de couverture (la première dans l'ordre)
        cur.execute("UPDATE propriete_photos SET est_couverture = false WHERE propriete_id = %s", (propriete_id,))
        cur.execute(
            """UPDATE propriete_photos SET est_couverture = true
               WHERE id = (SELECT id FROM propriete_photos WHERE propriete_id = %s
                           ORDER BY ordre, id LIMIT 1)""",
            (propriete_id,),
        )
    db.commit()
    return True


def changer_statut(propriete_id, proprietaire_id, statut):
    row = query(
        """UPDATE proprietes SET statut = %s, updated_at = now()
           WHERE id = %s AND proprietaire_id = %s RETURNING id""",
        (statut, propriete_id, proprietaire_id), one=True, commit=True,
    )
    return row is not None


def supprimer(propriete_id, proprietaire_id):
    row = query(
        "DELETE FROM proprietes WHERE id = %s AND proprietaire_id = %s RETURNING id",
        (propriete_id, proprietaire_id), one=True, commit=True,
    )
    return row is not None
