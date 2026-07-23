"""Requêtes SQL du module Dépôt d'annonce."""
from ...db import query, get_db


# ── Données pour alimenter le formulaire ──
def types_bien():
    return query("SELECT id, code, libelle FROM property_types ORDER BY libelle")


def quartiers():
    return query(
        """
        SELECT q.id, q.nom, c.nom AS commune, vl.nom AS ville
        FROM quartiers q
        JOIN communes c  ON c.id = q.commune_id
        JOIN villes  vl ON vl.id = c.ville_id
        ORDER BY vl.nom, c.nom, q.nom
        """
    )


def creer_annonce(d, proprietaire_id, photos_urls=None):
    """Insère l'annonce + ses tarifs + ses photos dans une seule transaction.

    `d` est un dict de valeurs déjà validées/converties par la couche route.
    `photos_urls` est une liste d'URLs (la première devient la photo de couverture).
    Retourne l'UUID de l'annonce créée.
    """
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO proprietes
                (proprietaire_id, property_type_id, titre, description, quartier_id,
                 adresse_precise, nb_chambres, nb_salons, nb_salles_bain, surface_m2,
                 etage, meuble, mode_location, capacite_voyageurs, statut)
            VALUES
                (%(prop)s, %(type)s, %(titre)s, %(desc)s, %(quartier)s,
                 %(adresse)s, %(ch)s, %(sal)s, %(sdb)s, %(surface)s,
                 %(etage)s, %(meuble)s, %(mode)s, %(cap)s, 'publiee')
            RETURNING id
            """,
            {
                "prop": proprietaire_id, "type": d["type_id"], "titre": d["titre"],
                "desc": d["description"], "quartier": d["quartier_id"], "adresse": d["adresse"],
                "ch": d["nb_chambres"], "sal": d["nb_salons"], "sdb": d["nb_salles_bain"],
                "surface": d["surface_m2"], "etage": d["etage"], "meuble": d["meuble"],
                "mode": d["mode_location"], "cap": d["capacite_voyageurs"],
            },
        )
        propriete_id = cur.fetchone()["id"]

        # Tarif mensuel (longue durée)
        if d["prix_mois"] is not None:
            cur.execute(
                """INSERT INTO tarifs (propriete_id, unite, montant, caution_mois)
                   VALUES (%s, 'mois', %s, %s)""",
                (propriete_id, d["prix_mois"], d["caution_mois"]),
            )
        # Tarif à la nuitée (courte durée)
        if d["prix_nuit"] is not None:
            cur.execute(
                """INSERT INTO tarifs (propriete_id, unite, montant, min_nuits)
                   VALUES (%s, 'nuit', %s, %s)""",
                (propriete_id, d["prix_nuit"], d["min_nuits"]),
            )
        # Photos (la première est la couverture)
        for i, url in enumerate(photos_urls or []):
            cur.execute(
                """INSERT INTO propriete_photos (propriete_id, url, est_couverture, ordre)
                   VALUES (%s, %s, %s, %s)""",
                (propriete_id, url, i == 0, i),
            )
    db.commit()
    return propriete_id
