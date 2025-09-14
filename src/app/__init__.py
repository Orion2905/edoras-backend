# Flask App Factory

from flask import Flask
from flask_cors import CORS

from .extensions import db, jwt, migrate, ma
from .api import api_bp


def create_app(config_name='development'):
    """
    Application factory per Flask.
    
    Args:
        config_name (str): Nome della configurazione da utilizzare
        
    Returns:
        Flask: Istanza dell'applicazione Flask configurata
    """
    app = Flask(__name__)
    
    # Carica configurazione usando il nuovo sistema
    from src.config import get_config
    config_class = get_config(config_name)
    app.config.from_object(config_class)
    
    # Configura logging per primo
    setup_logging_config(app)
    
    # Inizializza estensioni
    initialize_extensions(app)
    
    # Registra blueprints
    register_blueprints(app)
    
    # Configura CORS
    configure_cors(app)
    
    # Configura error handlers
    configure_error_handlers(app)
    
    return app


def setup_logging_config(app):
    """Configura il sistema di logging."""
    try:
        from .utils.logging import setup_logging, log_request_info, log_error_details
        setup_logging(app)
        log_request_info(app)
        log_error_details(app)
    except ImportError:
        # Fallback se il modulo logging non è disponibile
        app.logger.info("Logging utils not available, using basic logging")


def initialize_extensions(app):
    """Inizializza tutte le estensioni Flask."""
    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)
    ma.init_app(app)


def register_blueprints(app):
    """Registra tutti i blueprints dell'applicazione."""
    app.register_blueprint(api_bp, url_prefix='/api')


def configure_cors(app):
    """Configura CORS per l'applicazione."""
    CORS(app, resources={
        r"/api/*": {
            "origins": app.config.get('CORS_ORIGINS', ["http://localhost:3000"]),
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })


def configure_error_handlers(app):
    """Configura gli error handlers globali."""
    
    @app.errorhandler(404)
    def not_found(error):
        return {'message': 'Resource not found'}, 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return {'message': 'Internal server error'}, 500
    
    @app.errorhandler(400)
    def bad_request(error):
        return {'message': 'Bad request'}, 400
