import logging
import sys
from logging.handlers import RotatingFileHandler
import os


def setup_logging(app):
    """
    Configura il logging per l'applicazione.
    
    Args:
        app: Istanza Flask
    """
    # Configura il livello di logging
    log_level = getattr(logging, os.getenv('LOG_LEVEL', 'INFO').upper())
    
    # Formato dei log
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
    )
    
    # Configura il logger dell'app
    app.logger.setLevel(log_level)
    
    # Rimuovi handler esistenti
    for handler in app.logger.handlers[:]:
        app.logger.removeHandler(handler)
    
    # Handler per stdout (per container)
    if os.getenv('LOG_TO_STDOUT', 'False').lower() == 'true':
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setLevel(log_level)
        stream_handler.setFormatter(formatter)
        app.logger.addHandler(stream_handler)
    
    # Handler per file (per development)
    if app.config.get('LOG_TO_FILE', False):
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        file_handler = RotatingFileHandler(
            'logs/edoras-api.log', 
            maxBytes=10240000,  # 10MB
            backupCount=10
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        app.logger.addHandler(file_handler)
    
    # Log startup
    app.logger.info('Edoras API startup')
    
    # Configura SQLAlchemy logging
    if app.config.get('SQLALCHEMY_ECHO', False):
        logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
    
    # Configura urllib3 logging (per Azure SDK)
    logging.getLogger('urllib3.connectionpool').setLevel(logging.WARNING)
    logging.getLogger('azure').setLevel(logging.WARNING)


def log_request_info(app):
    """
    Configura il logging delle richieste HTTP.
    
    Args:
        app: Istanza Flask
    """
    @app.before_request
    def before_request():
        if app.config.get('LOG_REQUESTS', False):
            from flask import request
            app.logger.info(f'{request.method} {request.url} - {request.remote_addr}')
    
    @app.after_request
    def after_request(response):
        if app.config.get('LOG_REQUESTS', False):
            from flask import request
            app.logger.info(
                f'{request.method} {request.url} - {response.status_code} - {request.remote_addr}'
            )
        return response


def log_error_details(app):
    """
    Configura il logging dettagliato degli errori.
    
    Args:
        app: Istanza Flask
    """
    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f'Server Error: {error}', exc_info=True)
        return {'error': 'Internal server error'}, 500
    
    @app.errorhandler(Exception)
    def unhandled_exception(e):
        app.logger.error(f'Unhandled Exception: {e}', exc_info=True)
        return {'error': 'Internal server error'}, 500
