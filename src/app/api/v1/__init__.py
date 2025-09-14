# API v1 Package

from flask import Blueprint

# Blueprint per API v1
api_v1_bp = Blueprint('api_v1', __name__)

# Import di tutti gli endpoint
from . import auth, users, health, companies, roles, permissions, invoices, categories, subcategories, minicategories, scraper_accesses, property_units, property_types, pods, property_pods, bookings
