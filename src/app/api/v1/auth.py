# Authentication Endpoints

from flask import request, jsonify
from flask_jwt_extended import (
    create_access_token, 
    create_refresh_token,
    jwt_required, 
    get_jwt_identity,
    get_jwt
)
from marshmallow import ValidationError

from ...models.user import User
from ...schemas.user import user_login_schema, user_registration_schema, user_schema
from ...extensions import db
from . import api_v1_bp


@api_v1_bp.route('/auth/register', methods=['POST'])
def register():
    """
    Registrazione nuovo utente.
    
    Body:
        email (str): Email dell'utente
        username (str): Username dell'utente
        password (str): Password dell'utente
        first_name (str, optional): Nome
        last_name (str, optional): Cognome
        
    Returns:
        JSON response con i dati dell'utente creato
    """
    try:
        # Valida i dati in input
        data = user_registration_schema.load(request.json)
    except ValidationError as err:
        return jsonify({'errors': err.messages}), 400
    
    # Verifica se l'utente esiste già
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'message': 'Email already registered'}), 409
        
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'message': 'Username already taken'}), 409
    
    # Crea nuovo utente
    user = User(
        email=data['email'],
        username=data['username'],
        first_name=data.get('first_name'),
        last_name=data.get('last_name')
    )
    user.set_password(data['password'])
    user.save()
    
    # Crea token di accesso
    access_token = create_access_token(identity=user)
    refresh_token = create_refresh_token(identity=user)
    
    return jsonify({
        'message': 'User registered successfully',
        'user': user_schema.dump(user),
        'access_token': access_token,
        'refresh_token': refresh_token
    }), 201


@api_v1_bp.route('/auth/login', methods=['POST'])
def login():
    """
    Login utente.
    
    Body:
        email (str): Email dell'utente
        password (str): Password dell'utente
        
    Returns:
        JSON response con token di accesso
    """
    try:
        # Valida i dati in input
        data = user_login_schema.load(request.json)
    except ValidationError as err:
        return jsonify({'errors': err.messages}), 400
    
    # Trova l'utente
    user = User.query.filter_by(email=data['email']).first()
    
    if not user or not user.check_password(data['password']):
        return jsonify({'message': 'Invalid credentials'}), 401
    
    if not user.is_active:
        return jsonify({'message': 'Account deactivated'}), 403
    
    # Aggiorna ultimo login
    user.update_last_login()
    
    # Crea token di accesso
    access_token = create_access_token(identity=user)
    refresh_token = create_refresh_token(identity=user)
    
    return jsonify({
        'message': 'Login successful',
        'user': user_schema.dump(user),
        'access_token': access_token,
        'refresh_token': refresh_token
    }), 200


@api_v1_bp.route('/auth/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """
    Refresh del token di accesso.
    
    Headers:
        Authorization: Bearer <refresh_token>
        
    Returns:
        JSON response con nuovo token di accesso
    """
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user or not user.is_active:
        return jsonify({'message': 'User not found or inactive'}), 404
    
    new_access_token = create_access_token(identity=user)
    
    return jsonify({
        'access_token': new_access_token
    }), 200


@api_v1_bp.route('/auth/logout', methods=['POST'])
@jwt_required()
def logout():
    """
    Logout utente.
    
    Headers:
        Authorization: Bearer <access_token>
        
    Returns:
        JSON response di conferma logout
    """
    # TODO: Implementare blacklist dei token se necessario
    return jsonify({'message': 'Successfully logged out'}), 200


@api_v1_bp.route('/auth/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """
    Ottieni informazioni dell'utente corrente.
    
    Headers:
        Authorization: Bearer <access_token>
        
    Returns:
        JSON response con i dati dell'utente
    """
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user:
        return jsonify({'message': 'User not found'}), 404
    
    return jsonify({
        'user': user_schema.dump(user)
    }), 200
