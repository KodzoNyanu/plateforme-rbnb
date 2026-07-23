"""Requêtes SQL du module Réservations."""
import uuid

from ...db import query, get_db


def parametre_commission(mode_location):
    """Barème de commission actif pour un mode ('longue_duree' / 'courte_duree')."""
    return query(
        """SELECT type_frais, valeur FROM parametres_commission
           WHERE mode_location = %s AND actif ORDER BY id LIMIT 1""",
        (mode_location,), one=True,
    )


def creer_reservation(locataire_id, propriete_id, m):
    """Crée la réservation (en attente de paiement) + sa commission (due)."""
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            """INSERT INTO reservations
                   (propriete_id, locataire_id, mode_location, date_debut, date_fin,
                    nb_unites, montant_total, montant_en_ligne, montant_sur_place, statut)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'en_attente_paiement')
               RETURNING id""",
            (propriete_id, locataire_id, m["mode_location"], m["date_debut"], m["date_fin"],
             m["nb_unites"], m["total"], m["online"], m["sur_place"]),
        )
        reservation_id = cur.fetchone()["id"]
        cur.execute(
            """INSERT INTO commissions (reservation_id, base_calcul, taux, montant, statut)
               VALUES (%s, %s, %s, %s, 'due')""",
            (reservation_id, m["commission_base"], m["commission_taux"], m["commission_montant"]),
        )
    db.commit()
    return reservation_id


def pour_locataire(reservation_id, locataire_id):
    """Détail d'une réservation (seulement pour le locataire qui l'a faite)."""
    return query(
        """
        SELECT r.*, p.titre, p.adresse_precise, pt.libelle AS type_bien,
               q.nom AS quartier, c.nom AS commune, vl.nom AS ville,
               u.nom_complet AS proprietaire_nom, u.telephone AS proprietaire_tel,
               u.email AS proprietaire_email,
               pay.methode AS paie_methode
        FROM reservations r
        JOIN proprietes p     ON p.id = r.propriete_id
        JOIN property_types pt ON pt.id = p.property_type_id
        JOIN quartiers q      ON q.id = p.quartier_id
        JOIN communes  c      ON c.id = q.commune_id
        JOIN villes    vl     ON vl.id = c.ville_id
        JOIN users     u      ON u.id = p.proprietaire_id
        LEFT JOIN paiements pay ON pay.reservation_id = r.id AND pay.statut = 'paye'
        WHERE r.id = %s AND r.locataire_id = %s
        """,
        (reservation_id, locataire_id), one=True,
    )


def marquer_payee(reservation_id, locataire_id, methode):
    """Simule le paiement en ligne du frais de réservation : enregistre le paiement,
    confirme la réservation et marque la commission comme perçue.
    Retourne False si la réservation n'est pas payable (déjà payée / pas la bonne personne).
    """
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            """SELECT montant_en_ligne FROM reservations
               WHERE id = %s AND locataire_id = %s AND statut = 'en_attente_paiement'""",
            (reservation_id, locataire_id),
        )
        row = cur.fetchone()
        if not row:
            db.rollback()
            return False
        cur.execute(
            """INSERT INTO paiements (reservation_id, type, methode, montant, statut, paye_le)
               VALUES (%s, 'frais_reservation', %s, %s, 'paye', now()) RETURNING id""",
            (reservation_id, methode, row["montant_en_ligne"]),
        )
        paiement_id = cur.fetchone()["id"]
        cur.execute("UPDATE reservations SET statut = 'confirmee' WHERE id = %s", (reservation_id,))
        cur.execute(
            "UPDATE commissions SET statut = 'percue', paiement_id = %s WHERE reservation_id = %s",
            (paiement_id, reservation_id),
        )
    db.commit()
    return True


def creer_tentative_paiement(reservation_id, locataire_id):
    """Crée un paiement 'initié' (méthode CinetPay) pour une réservation payable.
    Retourne le transaction_id à envoyer à CinetPay, ou None si non payable.
    """
    transaction_id = "RESA" + uuid.uuid4().hex[:20]
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            """INSERT INTO paiements (reservation_id, type, methode, montant, statut, reference_externe)
               SELECT id, 'frais_reservation', 'cinetpay', montant_en_ligne, 'initie', %s
               FROM reservations
               WHERE id = %s AND locataire_id = %s AND statut = 'en_attente_paiement'
               RETURNING id""",
            (transaction_id, reservation_id, locataire_id),
        )
        if cur.fetchone() is None:
            db.rollback()
            return None
    db.commit()
    return transaction_id


def confirmer_paiement(transaction_id):
    """Confirme un paiement vérifié auprès de CinetPay (idempotent).
    Retourne l'id de la réservation, ou None si transaction inconnue.
    """
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            """SELECT p.id AS paiement_id, r.id AS reservation_id, r.statut
               FROM paiements p JOIN reservations r ON r.id = p.reservation_id
               WHERE p.reference_externe = %s""",
            (transaction_id,),
        )
        row = cur.fetchone()
        if row is None:
            db.rollback()
            return None
        if row["statut"] == "confirmee":
            db.rollback()
            return row["reservation_id"]          # déjà confirmé : rien à refaire
        cur.execute("UPDATE paiements SET statut = 'paye', paye_le = now() WHERE id = %s", (row["paiement_id"],))
        cur.execute("UPDATE reservations SET statut = 'confirmee' WHERE id = %s", (row["reservation_id"],))
        cur.execute(
            "UPDATE commissions SET statut = 'percue', paiement_id = %s WHERE reservation_id = %s",
            (row["paiement_id"], row["reservation_id"]),
        )
    db.commit()
    return row["reservation_id"]


def liste_pour_locataire(locataire_id):
    return query(
        """
        SELECT r.id, r.statut, r.date_debut, r.date_fin, r.mode_location,
               r.montant_en_ligne, r.montant_sur_place,
               p.titre, q.nom AS quartier
        FROM reservations r
        JOIN proprietes p ON p.id = r.propriete_id
        JOIN quartiers  q ON q.id = p.quartier_id
        WHERE r.locataire_id = %s
        ORDER BY r.created_at DESC
        """,
        (locataire_id,),
    )
