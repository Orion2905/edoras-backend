# Edoras Flask Application Entry Point

import os
import sys
from dotenv import load_dotenv

# Carica le variabili ambiente dal file .env
load_dotenv()

# Aggiungi src al path
sys.path.insert(0, 'src')

from src.app import create_app

# Ottieni la configurazione dall'environment
config_name = os.getenv('FLASK_ENV', 'development')

# Crea l'app Flask
app = create_app(config_name)

# Azure App Service compatibility
if __name__ == '__main__':
    # Development server - per Azure App Service usa gunicorn
    port = int(os.getenv('PORT', 8000))  # Azure App Service usa port 8000
    app.run(
        host='0.0.0.0',
        port=port,
        debug=app.config.get('DEBUG', False)
    )
else:
    # Production mode con gunicorn
    # Log info per Azure diagnostics
    app.logger.info(f'Starting Edoras API in {config_name} mode')
    app.logger.info(f'Database URL configured: {bool(os.getenv("DATABASE_URL"))}')
    app.logger.info(f'Key Vault URL configured: {bool(os.getenv("AZURE_KEYVAULT_URL"))}')
