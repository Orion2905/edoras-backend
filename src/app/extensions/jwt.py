# JWT Configuration

from flask_jwt_extended import get_jwt_identity, get_jwt
from ..extensions import jwt


@jwt.user_identity_loader
def user_identity_lookup(user):
    """Configura come identificare l'utente nel JWT."""
    return user.id if hasattr(user, 'id') else user


@jwt.user_lookup_loader
def user_lookup_callback(_jwt_header, jwt_data):
    """Carica l'utente dal JWT."""
    from ..models.user import User
    identity = jwt_data["sub"]
    return User.query.filter_by(id=identity).one_or_none()


@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    """Callback per token scaduto."""
    return {'message': 'Token has expired'}, 401


@jwt.invalid_token_loader
def invalid_token_callback(error):
    """Callback per token non valido."""
    return {'message': 'Invalid token'}, 401


@jwt.unauthorized_loader
def missing_token_callback(error):
    """Callback per token mancante."""
    return {'message': 'Authorization token is required'}, 401
