# Flask Extensions Configuration

from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_marshmallow import Marshmallow

# Inizializza le estensioni
db = SQLAlchemy()
jwt = JWTManager()
migrate = Migrate()
ma = Marshmallow()
