# Users Management Endpoints - Sistema CRUD Completo

from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_, or_

from ...models.user import User
from ...models.company import Company
from ...models.role import Role
from ...schemas.user import (
    user_schema, 
    users_schema, 
    user_update_schema, 
    password_change_schema,
    user_create_schema,
    user_admin_update_schema,
    user_password_reset_schema,
    user_role_assignment_schema
)
from ...extensions import db
from . import api_v1_bp


def user_can_manage_users(user):
    """Verifica se l'utente può gestire altri utenti (solo Rohirrim)."""
    return user and user.is_active and user.is_rohirrim()


def user_can_view_user(current_user, target_user_id=None):
    """Verifica se l'utente può visualizzare un altro utente."""
    if not current_user or not current_user.is_active:
        return False
    
    # Rohirrim può vedere tutti
    if current_user.is_rohirrim():
        return True
    
    # Lord può vedere utenti della propria company
    if current_user.is_lord() and current_user.company_id:
        if target_user_id:
            target_user = User.query.get(target_user_id)
            return target_user and target_user.company_id == current_user.company_id
        return True
    
    # Dunedain può vedere solo se stesso
    if current_user.is_dunedain():
        return target_user_id == current_user.id if target_user_id else False
    
    return False


# ===== GESTIONE PROFILO PERSONALE =====

@api_v1_bp.route('/users/me', methods=['GET'])
@jwt_required()
def get_my_profile():
    """
    Ottieni il profilo dell'utente corrente.
    
    Headers:
        Authorization: Bearer <access_token>
        
    Returns:
        JSON response con i dati del profilo
    """
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user:
        return jsonify({'message': 'User not found'}), 404
    
    return jsonify({
        'user': user_schema.dump(user)
    }), 200


@api_v1_bp.route('/users/me', methods=['PUT'])
@jwt_required()
def update_my_profile():
    """
    Aggiorna il profilo dell'utente corrente.
    
    Headers:
        Authorization: Bearer <access_token>
        
    Body:
        first_name (str, optional): Nome
        last_name (str, optional): Cognome
        avatar_url (str, optional): URL avatar
        
    Returns:
        JSON response con i dati aggiornati
    """
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user:
        return jsonify({'message': 'User not found'}), 404
    
    try:
        # Valida i dati in input
        data = user_update_schema.load(request.json)
    except ValidationError as err:
        return jsonify({'message': 'Validation error', 'errors': err.messages}), 400
    
    try:
        # Aggiorna i campi dell'utente
        for field, value in data.items():
            if hasattr(user, field):
                setattr(user, field, value)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Profile updated successfully',
            'user': user_schema.dump(user)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Internal server error'}), 500


@api_v1_bp.route('/users/me/password', methods=['PUT'])
@jwt_required()
def change_password():
    """
    Cambia la password dell'utente corrente.
    
    Headers:
        Authorization: Bearer <access_token>
        
    Body:
        current_password (str): Password attuale
        new_password (str): Nuova password
        
    Returns:
        JSON response di conferma
    """
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user:
        return jsonify({'message': 'User not found'}), 404
    
    try:
        # Valida i dati in input
        data = password_change_schema.load(request.json)
    except ValidationError as err:
        return jsonify({'message': 'Validation error', 'errors': err.messages}), 400
    
    # Verifica password attuale
    if not user.check_password(data['current_password']):
        return jsonify({'message': 'Current password is incorrect'}), 400
    
    try:
        # Aggiorna password
        user.set_password(data['new_password'])
        db.session.commit()
        
        return jsonify({
            'message': 'Password changed successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Internal server error'}), 500


# ===== GESTIONE AMMINISTRATIVA UTENTI =====

@api_v1_bp.route('/users', methods=['GET'])
@jwt_required()
def get_users():
    """
    Ottieni lista degli utenti con filtri e paginazione.
    
    Headers:
        Authorization: Bearer <access_token>
        
    Query Parameters:
        page (int, optional): Numero pagina (default: 1)
        per_page (int, optional): Elementi per pagina (default: 20, max: 100)
        search (str, optional): Ricerca per email, username, nome
        company_id (int, optional): Filtra per azienda
        role_id (int, optional): Filtra per ruolo
        active_only (bool, optional): Solo utenti attivi (default: true)
        include_stats (bool, optional): Includi statistiche (default: false)
        
    Returns:
        JSON response con la lista degli utenti
    """
    current_user_id = get_jwt_identity()
    current_user = User.query.get(current_user_id)
    
    if not current_user:
        return jsonify({'message': 'User not found'}), 404
    
    # Parsing parametri query
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    search = request.args.get('search', '').strip()
    company_id = request.args.get('company_id', type=int)
    role_id = request.args.get('role_id', type=int)
    active_only = request.args.get('active_only', 'true').lower() == 'true'
    include_stats = request.args.get('include_stats', 'false').lower() == 'true'
    
    # Base query
    query = User.query
    
    # Filtri di autorizzazione
    if current_user.is_rohirrim():
        # Rohirrim può vedere tutti gli utenti
        pass
    elif current_user.is_lord() and current_user.company_id:
        # Lord può vedere solo utenti della propria company
        query = query.filter(User.company_id == current_user.company_id)
    elif current_user.is_dunedain():
        # Dunedain può vedere solo se stesso
        query = query.filter(User.id == current_user.id)
    else:
        return jsonify({'message': 'Access denied'}), 403
    
    # Filtri aggiuntivi
    if active_only:
        query = query.filter(User.is_active == True)
    
    if company_id:
        # Verifica che l'utente possa vedere questa company
        if not current_user.is_rohirrim() and company_id != current_user.company_id:
            return jsonify({'message': 'Access denied to this company'}), 403
        query = query.filter(User.company_id == company_id)
    
    if role_id:
        query = query.filter(User.role_id == role_id)
    
    # Filtro di ricerca
    if search:
        search_filter = f'%{search}%'
        query = query.filter(
            or_(
                User.email.ilike(search_filter),
                User.username.ilike(search_filter),
                User.first_name.ilike(search_filter),
                User.last_name.ilike(search_filter)
            )
        )
    
    # Ordinamento
    query = query.order_by(User.created_at.desc())
    
    # Paginazione
    pagination = query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    
    users = pagination.items
    
    # Serializzazione
    users_data = []
    for user in users:
        user_dict = user_schema.dump(user)
        
        # Aggiungi informazioni aggiuntive se richieste
        if include_stats:
            user_dict['company_name'] = user.company.display_name if user.company else None
            user_dict['role_name'] = user.role.name if user.role else None
            user_dict['permissions'] = user.get_permissions_list()
        
        users_data.append(user_dict)
    
    return jsonify({
        'users': users_data,
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page,
        'per_page': per_page,
        'has_next': pagination.has_next,
        'has_prev': pagination.has_prev
    }), 200


@api_v1_bp.route('/users/<int:user_id>', methods=['GET'])
@jwt_required()
def get_user(user_id):
    """
    Ottieni dettagli di un utente specifico.
    
    Headers:
        Authorization: Bearer <access_token>
        
    Path Parameters:
        user_id (int): ID dell'utente
        
    Query Parameters:
        include_stats (bool, optional): Includi statistiche (default: true)
        
    Returns:
        JSON response con i dati dell'utente
    """
    current_user_id = get_jwt_identity()
    current_user = User.query.get(current_user_id)
    
    if not current_user:
        return jsonify({'message': 'User not found'}), 404
    
    # Verifica permessi
    if not user_can_view_user(current_user, user_id):
        return jsonify({'message': 'Access denied'}), 403
    
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'message': 'User not found'}), 404
    
    include_stats = request.args.get('include_stats', 'true').lower() == 'true'
    
    user_data = user_schema.dump(user)
    
    if include_stats:
        user_data['company_name'] = user.company.display_name if user.company else None
        user_data['role_name'] = user.role.name if user.role else None
        user_data['permissions'] = user.get_permissions_list()
    
    return jsonify({'user': user_data}), 200


@api_v1_bp.route('/users', methods=['POST'])
@jwt_required()
def create_user():
    """
    Crea un nuovo utente (solo Rohirrim).
    
    Headers:
        Authorization: Bearer <access_token>
        Content-Type: application/json
        
    Body:
        email (str): Email dell'utente
        username (str): Username
        password (str): Password
        first_name (str, optional): Nome
        last_name (str, optional): Cognome
        company_id (int, optional): ID azienda
        role_id (int, optional): ID ruolo
        avatar_url (str, optional): URL avatar
        is_active (bool, optional): Stato attivo (default: true)
        email_verified (bool, optional): Email verificata (default: false)
        
    Returns:
        JSON response con l'utente creato
    """
    current_user_id = get_jwt_identity()
    current_user = User.query.get(current_user_id)
    
    if not current_user:
        return jsonify({'message': 'User not found'}), 404
    
    # Solo Rohirrim può creare utenti
    if not user_can_manage_users(current_user):
        return jsonify({'message': 'Access denied. Only Rohirrim can create users'}), 403
    
    try:
        # Validazione dati
        user_data = user_create_schema.load(request.json)
    except ValidationError as err:
        return jsonify({'message': 'Validation error', 'errors': err.messages}), 400
    
    # Verifica che company e role esistano se specificati
    if user_data.get('company_id'):
        company = Company.query.get(user_data['company_id'])
        if not company or not company.is_active:
            return jsonify({'message': 'Invalid or inactive company'}), 400
    
    if user_data.get('role_id'):
        role = Role.query.get(user_data['role_id'])
        if not role or not role.is_active:
            return jsonify({'message': 'Invalid or inactive role'}), 400
    
    try:
        # Estrai password per gestirla separatamente
        password = user_data.pop('password')
        
        # Crea utente
        user = User(**user_data)
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        return jsonify({
            'message': 'User created successfully',
            'user': user_schema.dump(user)
        }), 201
        
    except IntegrityError as e:
        db.session.rollback()
        
        # Controllo per errori di duplicazione
        if 'email' in str(e.orig):
            return jsonify({'message': 'Email already exists'}), 409
        elif 'username' in str(e.orig):
            return jsonify({'message': 'Username already exists'}), 409
        else:
            return jsonify({'message': 'Database integrity error'}), 409
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Internal server error'}), 500


@api_v1_bp.route('/users/<int:user_id>', methods=['PUT'])
@jwt_required()
def update_user(user_id):
    """
    Aggiorna un utente esistente.
    
    Headers:
        Authorization: Bearer <access_token>
        Content-Type: application/json
        
    Path Parameters:
        user_id (int): ID dell'utente
        
    Body:
        email (str, optional): Email
        username (str, optional): Username
        first_name (str, optional): Nome
        last_name (str, optional): Cognome
        company_id (int, optional): ID azienda
        role_id (int, optional): ID ruolo
        avatar_url (str, optional): URL avatar
        is_active (bool, optional): Stato attivo
        email_verified (bool, optional): Email verificata
        
    Returns:
        JSON response con l'utente aggiornato
    """
    current_user_id = get_jwt_identity()
    current_user = User.query.get(current_user_id)
    
    if not current_user:
        return jsonify({'message': 'User not found'}), 404
    
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'message': 'User not found'}), 404
    
    # Verifica permessi
    is_self_update = user_id == current_user.id
    can_admin_update = user_can_manage_users(current_user)
    can_lord_update = (current_user.is_lord() and 
                      current_user.company_id and 
                      user.company_id == current_user.company_id)
    
    if not (is_self_update or can_admin_update or can_lord_update):
        return jsonify({'message': 'Access denied'}), 403
    
    try:
        # Usa schema diverso per admin vs self-update
        if is_self_update and not can_admin_update:
            user_data = user_update_schema.load(request.json)
        else:
            user_data = user_admin_update_schema.load(request.json)
    except ValidationError as err:
        return jsonify({'message': 'Validation error', 'errors': err.messages}), 400
    
    # Verifica che company e role esistano se specificati
    if 'company_id' in user_data and user_data['company_id']:
        company = Company.query.get(user_data['company_id'])
        if not company or not company.is_active:
            return jsonify({'message': 'Invalid or inactive company'}), 400
    
    if 'role_id' in user_data and user_data['role_id']:
        role = Role.query.get(user_data['role_id'])
        if not role or not role.is_active:
            return jsonify({'message': 'Invalid or inactive role'}), 400
    
    try:
        # Aggiorna campi
        for field, value in user_data.items():
            if hasattr(user, field):
                setattr(user, field, value)
        
        db.session.commit()
        
        return jsonify({
            'message': 'User updated successfully',
            'user': user_schema.dump(user)
        }), 200
        
    except IntegrityError as e:
        db.session.rollback()
        
        # Controllo per errori di duplicazione
        if 'email' in str(e.orig):
            return jsonify({'message': 'Email already exists'}), 409
        elif 'username' in str(e.orig):
            return jsonify({'message': 'Username already exists'}), 409
        else:
            return jsonify({'message': 'Database integrity error'}), 409
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Internal server error'}), 500


@api_v1_bp.route('/users/<int:user_id>', methods=['DELETE'])
@jwt_required()
def delete_user(user_id):
    """
    Elimina un utente (soft delete).
    
    Headers:
        Authorization: Bearer <access_token>
        
    Path Parameters:
        user_id (int): ID dell'utente
        
    Returns:
        JSON response di conferma
    """
    current_user_id = get_jwt_identity()
    current_user = User.query.get(current_user_id)
    
    if not current_user:
        return jsonify({'message': 'User not found'}), 404
    
    # Solo Rohirrim può eliminare utenti
    if not user_can_manage_users(current_user):
        return jsonify({'message': 'Access denied. Only Rohirrim can delete users'}), 403
    
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'message': 'User not found'}), 404
    
    # Non può eliminare se stesso
    if user_id == current_user.id:
        return jsonify({'message': 'Cannot delete yourself'}), 400
    
    try:
        # Soft delete
        user.is_active = False
        db.session.commit()
        
        return jsonify({'message': 'User deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Internal server error'}), 500


# ===== GESTIONE RUOLI E AZIENDE =====

@api_v1_bp.route('/users/<int:user_id>/assign-company-role', methods=['POST'])
@jwt_required()
def assign_company_role(user_id):
    """
    Assegna azienda e ruolo a un utente.
    
    Headers:
        Authorization: Bearer <access_token>
        Content-Type: application/json
        
    Path Parameters:
        user_id (int): ID dell'utente
        
    Body:
        company_id (int): ID dell'azienda
        role_id (int, optional): ID del ruolo (default: Lord)
        
    Returns:
        JSON response di conferma
    """
    current_user_id = get_jwt_identity()
    current_user = User.query.get(current_user_id)
    
    if not current_user:
        return jsonify({'message': 'User not found'}), 404
    
    # Solo Rohirrim può assegnare company/role
    if not user_can_manage_users(current_user):
        return jsonify({'message': 'Access denied. Only Rohirrim can assign company/role'}), 403
    
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'message': 'User not found'}), 404
    
    try:
        # Validazione dati
        data = user_role_assignment_schema.load(request.json)
    except ValidationError as err:
        return jsonify({'message': 'Validation error', 'errors': err.messages}), 400
    
    # Verifica che company esista
    company = Company.query.get(data['company_id'])
    if not company or not company.is_active:
        return jsonify({'message': 'Invalid or inactive company'}), 400
    
    # Verifica role se specificato
    role_id = data.get('role_id')
    if role_id:
        role = Role.query.get(role_id)
        if not role or not role.is_active:
            return jsonify({'message': 'Invalid or inactive role'}), 400
    
    try:
        # Assegna company e role
        user.set_company_and_role(data['company_id'], role_id)
        db.session.commit()
        
        return jsonify({
            'message': 'Company and role assigned successfully',
            'user': user_schema.dump(user)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Internal server error'}), 500


@api_v1_bp.route('/users/<int:user_id>/reset-password', methods=['POST'])
@jwt_required()
def admin_reset_password(user_id):
    """
    Reset password amministrativo.
    
    Headers:
        Authorization: Bearer <access_token>
        Content-Type: application/json
        
    Path Parameters:
        user_id (int): ID dell'utente
        
    Body:
        new_password (str): Nuova password
        
    Returns:
        JSON response di conferma
    """
    current_user_id = get_jwt_identity()
    current_user = User.query.get(current_user_id)
    
    if not current_user:
        return jsonify({'message': 'User not found'}), 404
    
    # Solo Rohirrim può resettare password
    if not user_can_manage_users(current_user):
        return jsonify({'message': 'Access denied. Only Rohirrim can reset passwords'}), 403
    
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'message': 'User not found'}), 404
    
    try:
        # Validazione dati
        data = user_password_reset_schema.load(request.json)
    except ValidationError as err:
        return jsonify({'message': 'Validation error', 'errors': err.messages}), 400
    
    try:
        # Reset password
        user.set_password(data['new_password'])
        db.session.commit()
        
        return jsonify({'message': 'Password reset successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Internal server error'}), 500


@api_v1_bp.route('/users/<int:user_id>/activate', methods=['POST'])
@jwt_required()
def activate_user(user_id):
    """
    Riattiva un utente disattivato.
    
    Headers:
        Authorization: Bearer <access_token>
        
    Path Parameters:
        user_id (int): ID dell'utente
        
    Returns:
        JSON response di conferma
    """
    current_user_id = get_jwt_identity()
    current_user = User.query.get(current_user_id)
    
    if not current_user:
        return jsonify({'message': 'User not found'}), 404
    
    # Solo Rohirrim può riattivare utenti
    if not user_can_manage_users(current_user):
        return jsonify({'message': 'Access denied. Only Rohirrim can activate users'}), 403
    
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'message': 'User not found'}), 404
    
    try:
        user.is_active = True
        db.session.commit()
        
        return jsonify({
            'message': 'User activated successfully',
            'user': user_schema.dump(user)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Internal server error'}), 500
