# Configuration Classes

import os
from datetime import timedelta
from ..utils.keyvault import get_secret_or_env


class Config:
    """Configurazione base."""
    
    # Flask
    SECRET_KEY = get_secret_or_env('flask-secret', 'SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Database
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_RECORD_QUERIES = True
    
    # JWT
    JWT_SECRET_KEY = get_secret_or_env('jwt-secret', 'JWT_SECRET_KEY', SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_BLACKLIST_ENABLED = True
    JWT_BLACKLIST_TOKEN_CHECKS = ['access', 'refresh']
    
    # CORS
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:3000').split(',')
    
    # Azure Storage
    AZURE_STORAGE_CONNECTION_STRING = get_secret_or_env(
        'storage-connection-string',
        'AZURE_STORAGE_CONNECTION_STRING'
    )
    AZURE_STORAGE_CONTAINER_NAME = os.environ.get('AZURE_STORAGE_CONTAINER_NAME', 'uploads')
    
    # Key Vault
    AZURE_KEY_VAULT_URL = os.environ.get('AZURE_KEY_VAULT_URL')


class DevelopmentConfig(Config):
    """Configurazione per ambiente di sviluppo."""
    
    DEBUG = True
    # Azure SQL Database per development - legge direttamente da .env
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///edoras_dev.db')
    SQLALCHEMY_ECHO = True


class TestingConfig(Config):
    """Configurazione per testing."""
    
    TESTING = True
    SQLALCHEMY_DATABASE_URI = get_secret_or_env(
        'test-database-url',
        'TEST_DATABASE_URL',
        'sqlite:///edoras_test.db'
    )
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=5)
    WTF_CSRF_ENABLED = False


class ProductionConfig(Config):
    """Configurazione per produzione."""
    
    DEBUG = False
    # Azure SQL Database connection string con Key Vault
    SQLALCHEMY_DATABASE_URI = get_secret_or_env(
        'database-url',
        'DATABASE_URL'
    )
    
    # Sicurezza per produzione
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Database connection pool settings
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_timeout': 20,
        'pool_recycle': 3600,
        'pool_pre_ping': True
    }


# Mapping delle configurazioni
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}


def get_config(config_name=None):
    """
    Ottieni configurazione per environment
    
    Args:
        config_name: Nome configurazione (development, production, testing)
        
    Returns:
        Classe configurazione
    """
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    
    return config.get(config_name, config['default'])
