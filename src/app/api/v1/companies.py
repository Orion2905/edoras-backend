# Company Management Endpoints

from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError

from ...models.company import Company
from ...models.user import User
from ...schemas.company import (
    company_schema, 
    companies_schema, 
    company_create_schema, 
    company_update_schema
)
from ...extensions import db
from . import api_v1_bp


def user_can_manage_companies(user):
    """Verifica se l'utente può gestire le aziende (solo Rohirrim)."""
    return user and user.is_active and user.is_rohirrim()


def user_can_view_company(user, company_id=None):
    """Verifica se l'utente può visualizzare una specifica azienda."""
    if not user or not user.is_active:
        return False
    
    # Rohirrim può vedere tutte le aziende
    if user.is_rohirrim():
        return True
    
    # Lord e Dunedain possono vedere solo la propria azienda
    return company_id == user.company_id


@api_v1_bp.route('/companies', methods=['GET'])
@jwt_required()
def get_companies():
    """
    Ottieni la lista delle aziende.
    
    Headers:
        Authorization: Bearer <access_token>
        
    Query Parameters:
        page (int, optional): Numero pagina (default: 1)
        per_page (int, optional): Elementi per pagina (default: 20, max: 100)
        search (str, optional): Ricerca per nome o ragione sociale
        active_only (bool, optional): Solo aziende attive (default: true)
        include_stats (bool, optional): Includi statistiche (default: false)
        
    Returns:
        JSON response con la lista delle aziende
    """
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user:
        return jsonify({'message': 'User not found'}), 404
    
    # Parsing parametri query
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    search = request.args.get('search', '').strip()
    active_only = request.args.get('active_only', 'true').lower() == 'true'
    include_stats = request.args.get('include_stats', 'false').lower() == 'true'
    
    # Base query
    query = Company.query
    
    # Filtro per utenti non Rohirrim - possono vedere solo la propria azienda
    if not user.is_rohirrim():
        if not user.company_id:
            return jsonify({'companies': [], 'total': 0, 'pages': 0}), 200
        query = query.filter(Company.id == user.company_id)
    
    # Filtro per aziende attive
    if active_only:
        query = query.filter(Company.is_active == True)
    
    # Filtro di ricerca
    if search:
        search_filter = f'%{search}%'
        query = query.filter(
            db.or_(
                Company.name.ilike(search_filter),
                Company.legal_name.ilike(search_filter),
                Company.vat_number.ilike(search_filter),
                Company.tax_code.ilike(search_filter)
            )
        )
    
    # Ordinamento
    query = query.order_by(Company.name.asc())
    
    # Paginazione
    pagination = query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    
    companies = pagination.items
    
    # Serializzazione con o senza statistiche
    if include_stats:
        companies_data = []
        for company in companies:
            company_dict = company.to_dict(include_relationships=True)
            companies_data.append(company_dict)
    else:
        companies_data = companies_schema.dump(companies)
    
    return jsonify({
        'companies': companies_data,
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page,
        'per_page': per_page,
        'has_next': pagination.has_next,
        'has_prev': pagination.has_prev
    }), 200


@api_v1_bp.route('/companies/<int:company_id>', methods=['GET'])
@jwt_required()
def get_company(company_id):
    """
    Ottieni una specifica azienda.
    
    Headers:
        Authorization: Bearer <access_token>
        
    Path Parameters:
        company_id (int): ID dell'azienda
        
    Query Parameters:
        include_stats (bool, optional): Includi statistiche (default: true)
        
    Returns:
        JSON response con i dati dell'azienda
    """
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user:
        return jsonify({'message': 'User not found'}), 404
    
    # Verifica permessi
    if not user_can_view_company(user, company_id):
        return jsonify({'message': 'Access denied'}), 403
    
    company = Company.query.get(company_id)
    
    if not company:
        return jsonify({'message': 'Company not found'}), 404
    
    include_stats = request.args.get('include_stats', 'true').lower() == 'true'
    
    if include_stats:
        company_data = company.to_dict(include_relationships=True)
    else:
        company_data = company_schema.dump(company)
    
    return jsonify({'company': company_data}), 200


@api_v1_bp.route('/companies', methods=['POST'])
@jwt_required()
def create_company():
    """
    Crea una nuova azienda.
    
    Headers:
        Authorization: Bearer <access_token>
        Content-Type: application/json
        
    Body:
        name (str): Nome dell'azienda
        legal_name (str, optional): Ragione sociale
        vat_number (str, optional): Partita IVA
        tax_code (str, optional): Codice fiscale
        email (str, optional): Email
        phone (str, optional): Telefono
        website (str, optional): Sito web
        address (str, optional): Indirizzo
        city (str, optional): Città
        province (str, optional): Provincia
        postal_code (str, optional): CAP
        country (str, optional): Codice paese (default: IT)
        
    Returns:
        JSON response con l'azienda creata
    """
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user:
        return jsonify({'message': 'User not found'}), 404
    
    # Solo Rohirrim può creare aziende
    if not user_can_manage_companies(user):
        return jsonify({'message': 'Access denied. Only Rohirrim can create companies'}), 403
    
    try:
        # Validazione dati
        company_data = company_create_schema.load(request.json)
    except ValidationError as err:
        return jsonify({'message': 'Validation error', 'errors': err.messages}), 400
    
    try:
        # Creazione azienda
        company = Company(**company_data)
        db.session.add(company)
        db.session.commit()
        
        return jsonify({
            'message': 'Company created successfully',
            'company': company_schema.dump(company)
        }), 201
        
    except IntegrityError as e:
        db.session.rollback()
        
        # Controllo per errori di duplicazione
        if 'vat_number' in str(e.orig):
            return jsonify({'message': 'VAT number already exists'}), 409
        elif 'tax_code' in str(e.orig):
            return jsonify({'message': 'Tax code already exists'}), 409
        else:
            return jsonify({'message': 'Database integrity error'}), 409
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Internal server error'}), 500


@api_v1_bp.route('/companies/<int:company_id>', methods=['PUT'])
@jwt_required()
def update_company(company_id):
    """
    Aggiorna un'azienda esistente.
    
    Headers:
        Authorization: Bearer <access_token>
        Content-Type: application/json
        
    Path Parameters:
        company_id (int): ID dell'azienda
        
    Body:
        name (str, optional): Nome dell'azienda
        legal_name (str, optional): Ragione sociale
        vat_number (str, optional): Partita IVA
        tax_code (str, optional): Codice fiscale
        email (str, optional): Email
        phone (str, optional): Telefono
        website (str, optional): Sito web
        address (str, optional): Indirizzo
        city (str, optional): Città
        province (str, optional): Provincia
        postal_code (str, optional): CAP
        country (str, optional): Codice paese
        is_active (bool, optional): Stato attivo
        
    Returns:
        JSON response con l'azienda aggiornata
    """
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user:
        return jsonify({'message': 'User not found'}), 404
    
    company = Company.query.get(company_id)
    
    if not company:
        return jsonify({'message': 'Company not found'}), 404
    
    # Verifica permessi
    if not user.can_manage_company(company_id):
        return jsonify({'message': 'Access denied'}), 403
    
    try:
        # Validazione dati
        company_data = company_update_schema.load(request.json)
    except ValidationError as err:
        return jsonify({'message': 'Validation error', 'errors': err.messages}), 400
    
    try:
        # Aggiornamento campi
        for field, value in company_data.items():
            if hasattr(company, field):
                setattr(company, field, value)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Company updated successfully',
            'company': company_schema.dump(company)
        }), 200
        
    except IntegrityError as e:
        db.session.rollback()
        
        # Controllo per errori di duplicazione
        if 'vat_number' in str(e.orig):
            return jsonify({'message': 'VAT number already exists'}), 409
        elif 'tax_code' in str(e.orig):
            return jsonify({'message': 'Tax code already exists'}), 409
        else:
            return jsonify({'message': 'Database integrity error'}), 409
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Internal server error'}), 500


@api_v1_bp.route('/companies/<int:company_id>', methods=['DELETE'])
@jwt_required()
def delete_company(company_id):
    """
    Elimina un'azienda (soft delete).
    
    Headers:
        Authorization: Bearer <access_token>
        
    Path Parameters:
        company_id (int): ID dell'azienda
        
    Returns:
        JSON response di conferma
    """
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user:
        return jsonify({'message': 'User not found'}), 404
    
    # Solo Rohirrim può eliminare aziende
    if not user_can_manage_companies(user):
        return jsonify({'message': 'Access denied. Only Rohirrim can delete companies'}), 403
    
    company = Company.query.get(company_id)
    
    if not company:
        return jsonify({'message': 'Company not found'}), 404
    
    try:
        # Soft delete
        company.is_active = False
        db.session.commit()
        
        return jsonify({'message': 'Company deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Internal server error'}), 500


@api_v1_bp.route('/companies/<int:company_id>/activate', methods=['POST'])
@jwt_required()
def activate_company(company_id):
    """
    Riattiva un'azienda disattivata.
    
    Headers:
        Authorization: Bearer <access_token>
        
    Path Parameters:
        company_id (int): ID dell'azienda
        
    Returns:
        JSON response di conferma
    """
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user:
        return jsonify({'message': 'User not found'}), 404
    
    # Solo Rohirrim può riattivare aziende
    if not user_can_manage_companies(user):
        return jsonify({'message': 'Access denied. Only Rohirrim can activate companies'}), 403
    
    company = Company.query.get(company_id)
    
    if not company:
        return jsonify({'message': 'Company not found'}), 404
    
    try:
        company.is_active = True
        db.session.commit()
        
        return jsonify({
            'message': 'Company activated successfully',
            'company': company_schema.dump(company)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Internal server error'}), 500
