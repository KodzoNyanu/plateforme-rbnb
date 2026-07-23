"""Client CinetPay (paiement Mobile Money / carte).

Deux appels servent :
  - initier_paiement() : crée une transaction et renvoie l'URL de paiement hébergée.
  - verifier_paiement() : interroge l'API 'check' pour connaître le VRAI statut
    (on ne se fie jamais à la simple redirection navigateur).

Clés lues depuis la configuration (.env). Si absentes, is_configured() est False
et l'application retombe sur le paiement simulé.
"""
import requests
from flask import current_app


def _cfg():
    c = current_app.config
    return c["CINETPAY_API_KEY"], c["CINETPAY_SITE_ID"], c["CINETPAY_BASE_URL"]


def is_configured():
    apikey, site_id, _ = _cfg()
    return bool(apikey and site_id)


def initier_paiement(transaction_id, montant, description, client, notify_url, return_url):
    """Crée la transaction chez CinetPay et renvoie l'URL de paiement.

    `montant` doit être un entier multiple de 5 (contrainte XOF).
    Lève une exception si l'initialisation échoue.
    """
    apikey, site_id, base = _cfg()
    nom_complet = (client.get("nom_complet") or "Client").strip()
    morceaux = nom_complet.split(" ", 1)
    prenom = morceaux[0]
    nom = morceaux[1] if len(morceaux) > 1 else prenom

    payload = {
        "apikey": apikey,
        "site_id": site_id,
        "transaction_id": transaction_id,
        "amount": int(montant),
        "currency": "XOF",
        "description": description[:255],
        "notify_url": notify_url,
        "return_url": return_url,
        "channels": "ALL",           # Mobile Money + carte
        "lang": "fr",
        "customer_name": prenom,
        "customer_surname": nom,
    }
    if client.get("email"):
        payload["customer_email"] = client["email"]
    if client.get("telephone"):
        payload["customer_phone_number"] = client["telephone"]

    reponse = requests.post(f"{base}/payment", json=payload, timeout=20)
    data = reponse.json()
    if str(data.get("code")) != "201":
        raise RuntimeError(f"CinetPay init échouée : {data.get('message')} — {data.get('description')}")
    return data["data"]["payment_url"]


def verifier_paiement(transaction_id):
    """Renvoie le statut réel d'une transaction : 'ACCEPTED', 'REFUSED', 'PENDING'…"""
    apikey, site_id, base = _cfg()
    reponse = requests.post(
        f"{base}/payment/check",
        json={"apikey": apikey, "site_id": site_id, "transaction_id": transaction_id},
        timeout=20,
    )
    data = reponse.json()
    statut = (data.get("data") or {}).get("status")
    if str(data.get("code")) == "00" and statut:
        return statut          # succès : ACCEPTED attendu
    return statut or "REFUSED"
