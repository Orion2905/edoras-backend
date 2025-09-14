# API Package

from flask import Blueprint

# Blueprint principale per le API
api_bp = Blueprint('api', __name__)

# Import dei sub-blueprints
from .v1 import api_v1_bp

# Registra i sub-blueprints
api_bp.register_blueprint(api_v1_bp, url_prefix='/v1')
