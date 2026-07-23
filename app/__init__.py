"""Usine à application Flask.

C'est ici qu'on assemble tous les modules (blueprints).
Pour ajouter une page : créer un dossier dans app/modules/, y définir un
blueprint `bp`, puis l'enregistrer ci-dessous. Rien d'autre à toucher.
"""
from datetime import datetime

from flask import Flask, flash, redirect, request, url_for

from .config import Config
from . import db
from . import security


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Connexion base de données + socle de sécurité (session, utilisateur courant)
    db.init_app(app)
    security.init_app(app)

    @app.context_processor
    def injecter_globales():
        return {"annee": datetime.now().year}

    @app.errorhandler(413)
    def fichier_trop_gros(e):
        flash("Photo(s) trop volumineuse(s) : 12 Mo maximum au total.", "erreur")
        return redirect(request.referrer or url_for("home.index"))

    # ── Enregistrement des modules (un import + un register par page) ──
    from .modules.home.routes import bp as home_bp
    from .modules.zones.routes import bp as zones_bp
    from .modules.properties.routes import bp as properties_bp
    from .modules.search.routes import bp as search_bp
    from .modules.deposer.routes import bp as deposer_bp
    from .modules.auth.routes import bp as auth_bp
    from .modules.mes_annonces.routes import bp as mes_annonces_bp
    from .modules.reservations.routes import bp as reservations_bp
    from .modules.commissions.routes import bp as commissions_bp

    app.register_blueprint(home_bp)
    app.register_blueprint(zones_bp)
    app.register_blueprint(properties_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(deposer_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(mes_annonces_bp)
    app.register_blueprint(reservations_bp)
    app.register_blueprint(commissions_bp)

    return app
