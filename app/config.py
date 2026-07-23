"""Configuration de l'application, lue depuis le fichier .env"""
import os
from dotenv import load_dotenv

load_dotenv()  # charge les variables du fichier .env


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/rbnb_togo",
    )
    DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"

    # Taille maximale d'un envoi (photos) : 12 Mo au total
    MAX_CONTENT_LENGTH = 12 * 1024 * 1024

    # CinetPay (vide = paiement simulé)
    CINETPAY_API_KEY = os.getenv("CINETPAY_API_KEY", "").strip()
    CINETPAY_SITE_ID = os.getenv("CINETPAY_SITE_ID", "").strip()
    CINETPAY_BASE_URL = os.getenv("CINETPAY_BASE_URL", "https://api-checkout.cinetpay.com/v2").strip()

    # Cloudinary (vide = les photos restent stockées sur le disque local — à éviter en production)
    CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME", "").strip()
    CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY", "").strip()
    CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET", "").strip()
