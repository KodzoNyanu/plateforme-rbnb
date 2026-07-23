"""Enregistrement des photos uploadées.

Si les clés Cloudinary sont configurées (.env), les photos partent vers
Cloudinary : stockage persistant, qui survit aux redéploiements — indispensable
en production (le disque d'un hébergeur comme Render est éphémère).

Sinon, repli automatique sur le disque local app/static/uploads/ — pratique en
développement, mais À ÉVITER en production pour cette raison.
"""
import uuid
from pathlib import Path

import cloudinary
import cloudinary.uploader
from flask import current_app

UPLOAD_DIR = Path(__file__).resolve().parent / "static" / "uploads"
EXTENSIONS_OK = {"jpg", "jpeg", "png", "webp", "gif"}
DOSSIER_CLOUDINARY = "rbnb_togo"


def _extension(nom_fichier):
    if "." not in nom_fichier:
        return None
    ext = nom_fichier.rsplit(".", 1)[1].lower()
    return ext if ext in EXTENSIONS_OK else None


def _cloud_pret():
    """Configure le SDK Cloudinary si les clés sont présentes. Renvoie True/False."""
    c = current_app.config
    if not (c["CLOUDINARY_CLOUD_NAME"] and c["CLOUDINARY_API_KEY"] and c["CLOUDINARY_API_SECRET"]):
        return False
    cloudinary.config(
        cloud_name=c["CLOUDINARY_CLOUD_NAME"],
        api_key=c["CLOUDINARY_API_KEY"],
        api_secret=c["CLOUDINARY_API_SECRET"],
        secure=True,
    )
    return True


def _public_id_depuis_url(url):
    """Retrouve le public_id Cloudinary (dossier/nom, sans extension) depuis une secure_url."""
    marqueur = "/upload/"
    if marqueur not in url:
        return None
    segments = url.split(marqueur, 1)[1].split("/")
    if segments and segments[0].startswith("v") and segments[0][1:].isdigit():
        segments = segments[1:]              # retire le segment de version 'v169.../'
    chemin = "/".join(segments)
    return chemin.rsplit(".", 1)[0] if "." in chemin else chemin


def enregistrer_photos(fichiers, max_photos=8):
    """Sauvegarde les images valides et renvoie la liste de leurs URLs publiques."""
    cloud = _cloud_pret()
    if not cloud:
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    urls = []
    for f in fichiers:
        if not f or not f.filename:
            continue
        ext = _extension(f.filename)
        if not ext:
            continue
        if cloud:
            resultat = cloudinary.uploader.upload(
                f, folder=DOSSIER_CLOUDINARY, public_id=uuid.uuid4().hex,
                resource_type="image", overwrite=False,
            )
            urls.append(resultat["secure_url"])
        else:
            nom = f"{uuid.uuid4().hex}.{ext}"
            f.save(UPLOAD_DIR / nom)
            urls.append(f"/static/uploads/{nom}")
        if len(urls) >= max_photos:
            break
    return urls


def supprimer_fichiers(urls):
    """Efface les fichiers correspondant aux URLs fournies (Cloudinary ou disque local)."""
    cloud = _cloud_pret()
    for u in urls or []:
        if not u:
            continue
        if u.startswith("/static/uploads/"):
            try:
                (UPLOAD_DIR / Path(u).name).unlink(missing_ok=True)
            except OSError:
                pass
        elif cloud and "cloudinary.com" in u:
            public_id = _public_id_depuis_url(u)
            if public_id:
                try:
                    cloudinary.uploader.destroy(public_id, resource_type="image")
                except Exception:                          # noqa: BLE001
                    pass
