# Property Units CRUD API - Sistema Completo

from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_current_user
from sqlalchemy import or_, func, text
from sqlalchemy.exc import IntegrityError
from datetime import date, datetime, timedelta
from decimal import Decimal
from ...models.property_unit import PropertyUnit
from ...models.property_type import PropertyType
from ...models.company import Company
from ...schemas import (
    property_unit_schema, property_units_schema,
    property_unit_create_schema, property_unit_update_schema,
    property_unit_list_schema, property_unit_stats_schema,
    property_unit_duplicate_check_schema, property_unit_bulk_action_schema,
    property_unit_by_type_schema, property_unit_by_company_schema,
    property_unit_occupancy_schema, property_unit_address_search_schema
)
from ...extensions import db
from marshmallow import ValidationError
from . import api_v1_bp


def user_can_manage_property_units(user):
    """Verifica se l'utente può gestire le unità immobiliari (solo Rohirrim e Lord)."""
    return user and user.is_active and user.role and (user.role.is_rohirrim() or user.role.is_lord())


def user_can_view_property_units(user):
    """Verifica se l'utente può visualizzare le unità immobiliari."""
    if not user or not user.is_active:
        return False
    
    # Rohirrim, Lord e Dunedain possono tutti visualizzare le unità immobiliari
    if user.role and (user.role.is_rohirrim() or user.role.is_lord() or user.role.is_dunedain()):
        return True
    
    return False


@api_v1_bp.route('/property-units', methods=['GET'])
@jwt_required()
def get_property_units():
    """
    Ottiene la lista delle unità immobiliari con filtri avanzati.
    Tutti i ruoli possono visualizzare le unità immobiliari.
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_view_property_units(current_user):
            return jsonify({'error': 'Non autorizzato a visualizzare le unità immobiliari'}), 403
        
        # Validazione parametri
        try:
            args = property_unit_list_schema.load(request.args)
        except ValidationError as err:
            return jsonify({'error': 'Parametri non validi', 'details': err.messages}), 400
        
        # Query base
        query = PropertyUnit.query
        
        # Filtri
        if args.get('property_type_id'):
            query = query.filter(PropertyUnit.property_type_id == args['property_type_id'])
        
        if args.get('company_id'):
            query = query.filter(PropertyUnit.company_id == args['company_id'])
        
        if args.get('city'):
            query = query.filter(PropertyUnit.city.ilike(f"%{args['city']}%"))
        
        if args.get('province'):
            query = query.filter(PropertyUnit.province.ilike(f"%{args['province']}%"))
        
        if args.get('is_active') is not None:
            query = query.filter(PropertyUnit.is_active == args['is_active'])
        
        if args.get('is_occupied') is not None:
            query = query.filter(PropertyUnit.is_occupied == args['is_occupied'])
        
        # Filtri per metratura
        if args.get('min_square_meters'):
            query = query.filter(PropertyUnit.square_meters >= args['min_square_meters'])
        
        if args.get('max_square_meters'):
            query = query.filter(PropertyUnit.square_meters <= args['max_square_meters'])
        
        # Filtri per numero locali
        if args.get('min_rooms'):
            query = query.filter(PropertyUnit.rooms >= args['min_rooms'])
        
        if args.get('max_rooms'):
            query = query.filter(PropertyUnit.rooms <= args['max_rooms'])
        
        # Ricerca testuale
        if args.get('search'):
            search_term = f"%{args['search']}%"
            query = query.join(PropertyType, PropertyUnit.property_type_id == PropertyType.id).filter(
                or_(
                    PropertyUnit.name.ilike(search_term),
                    PropertyUnit.description.ilike(search_term),
                    PropertyUnit.address.ilike(search_term),
                    PropertyUnit.city.ilike(search_term),
                    PropertyType.name.ilike(search_term)
                )
            )
        
        # Ordinamento
        sort_by = args.get('sort_by', 'name')
        sort_order = args.get('sort_order', 'asc')
        
        if sort_by == 'property_type_name':
            query = query.join(PropertyType, PropertyUnit.property_type_id == PropertyType.id)
            sort_column = PropertyType.name
        else:
            sort_column = getattr(PropertyUnit, sort_by, PropertyUnit.name)
        
        if sort_order == 'desc':
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())
        
        # Paginazione
        page = args.get('page', 1)
        per_page = args.get('per_page', 20)
        
        units = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        # Serializzazione con dati aggiuntivi
        result = []
        for unit in units.items:
            unit_data = property_unit_schema.dump(unit)
            unit_data['property_type_name'] = unit.property_type.name if unit.property_type else None
            unit_data['company_name'] = unit.company_name
            unit_data['full_address'] = unit.get_full_address()
            unit_data['connected_pods_count'] = unit.property_pods.count()
            result.append(unit_data)
        
        return jsonify({
            'property_units': result,
            'pagination': {
                'page': units.page,
                'per_page': units.per_page,
                'total': units.total,
                'pages': units.pages,
                'has_next': units.has_next,
                'has_prev': units.has_prev
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Errore durante il recupero delle unità immobiliari', 'details': str(e)}), 500


@api_v1_bp.route('/property-units', methods=['POST'])
@jwt_required()
def create_property_unit():
    """
    Crea una nuova unità immobiliare.
    Solo gli utenti Rohirrim e Lord possono creare unità immobiliari.
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_manage_property_units(current_user):
            return jsonify({'error': 'Non autorizzato a creare unità immobiliari'}), 403
        
        # Validazione dati
        try:
            data = property_unit_create_schema.load(request.get_json())
        except ValidationError as err:
            return jsonify({'error': 'Dati non validi', 'details': err.messages}), 400
        
        # Verifica esistenza tipo proprietà
        property_type = PropertyType.query.filter_by(id=data['property_type_id'], is_active=True).first()
        if not property_type:
            return jsonify({'error': 'Tipo di proprietà non trovato o non attivo'}), 404
        
        # Verifica esistenza azienda se specificata
        if data.get('company_id'):
            company = Company.query.filter_by(id=data['company_id'], is_active=True).first()
            if not company:
                return jsonify({'error': 'Azienda non trovata o non attiva'}), 404
        
        # Controllo duplicati (nome + azienda)
        existing_query = PropertyUnit.query.filter_by(name=data['name'])
        if data.get('company_id'):
            existing_query = existing_query.filter_by(company_id=data['company_id'])
        else:
            existing_query = existing_query.filter(PropertyUnit.company_id.is_(None))
        
        existing = existing_query.first()
        if existing:
            return jsonify({
                'error': 'Unità immobiliare già esistente',
                'details': f"Già presente unità con nome '{data['name']}' per questa azienda"
            }), 409
        
        # Creazione nuova unità
        new_unit = PropertyUnit(
            name=data['name'],
            description=data.get('description'),
            square_meters=data['square_meters'],
            rooms=data.get('rooms'),
            bathrooms=data.get('bathrooms'),
            floor=data.get('floor'),
            address=data.get('address'),
            city=data.get('city'),
            postal_code=data.get('postal_code'),
            province=data.get('province'),
            property_type_id=data['property_type_id'],
            company_id=data.get('company_id')
        )
        
        db.session.add(new_unit)
        db.session.commit()
        
        # Ricarica per ottenere le relazioni
        db.session.refresh(new_unit)
        
        unit_data = property_unit_schema.dump(new_unit)
        unit_data['property_type_name'] = new_unit.property_type.name
        unit_data['company_name'] = new_unit.company_name
        unit_data['full_address'] = new_unit.get_full_address()
        unit_data['connected_pods_count'] = 0
        
        return jsonify({
            'message': 'Unità immobiliare creata con successo',
            'property_unit': unit_data
        }), 201
        
    except IntegrityError as e:
        db.session.rollback()
        return jsonify({'error': 'Errore di integrità dei dati', 'details': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Errore durante la creazione dell\'unità immobiliare', 'details': str(e)}), 500


@api_v1_bp.route('/property-units/<int:unit_id>', methods=['GET'])
@jwt_required()
def get_property_unit(unit_id):
    """
    Ottiene i dettagli di un'unità immobiliare specifica.
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_view_property_units(current_user):
            return jsonify({'error': 'Non autorizzato a visualizzare le unità immobiliari'}), 403
        
        # Trova l'unità
        unit = PropertyUnit.query.filter_by(id=unit_id).first()
        if not unit:
            return jsonify({'error': 'Unità immobiliare non trovata'}), 404
        
        # Serializzazione con dati aggiuntivi
        unit_data = property_unit_schema.dump(unit)
        unit_data['property_type_name'] = unit.property_type.name if unit.property_type else None
        unit_data['company_name'] = unit.company_name
        unit_data['full_address'] = unit.get_full_address()
        unit_data['connected_pods_count'] = unit.property_pods.count()
        
        # Aggiungi informazioni sui POD connessi
        connected_pods = []
        for property_pod in unit.property_pods:
            if property_pod.pod:
                connected_pods.append({
                    'id': property_pod.pod.id,
                    'code': property_pod.pod.code,
                    'pod_type': property_pod.pod.pod_type.value if property_pod.pod.pod_type else None,
                    'is_active': property_pod.pod.is_active
                })
        
        unit_data['connected_pods'] = connected_pods
        
        return jsonify({
            'property_unit': unit_data
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Errore durante il recupero dell\'unità immobiliare', 'details': str(e)}), 500


@api_v1_bp.route('/property-units/<int:unit_id>', methods=['PUT'])
@jwt_required()
def update_property_unit(unit_id):
    """
    Aggiorna un'unità immobiliare esistente.
    Solo gli utenti Rohirrim e Lord possono aggiornare unità immobiliari.
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_manage_property_units(current_user):
            return jsonify({'error': 'Non autorizzato a modificare unità immobiliari'}), 403
        
        # Trova l'unità
        unit = PropertyUnit.query.filter_by(id=unit_id).first()
        if not unit:
            return jsonify({'error': 'Unità immobiliare non trovata'}), 404
        
        # Validazione dati
        try:
            data = property_unit_update_schema.load(request.get_json())
        except ValidationError as err:
            return jsonify({'error': 'Dati non validi', 'details': err.messages}), 400
        
        # Verifica esistenza tipo proprietà se specificato
        if 'property_type_id' in data:
            property_type = PropertyType.query.filter_by(id=data['property_type_id'], is_active=True).first()
            if not property_type:
                return jsonify({'error': 'Tipo di proprietà non trovato o non attivo'}), 404
        
        # Verifica esistenza azienda se specificata
        if 'company_id' in data and data['company_id']:
            company = Company.query.filter_by(id=data['company_id'], is_active=True).first()
            if not company:
                return jsonify({'error': 'Azienda non trovata o non attiva'}), 404
        
        # Controllo duplicati se cambia nome
        if 'name' in data and data['name'] != unit.name:
            company_id = data.get('company_id', unit.company_id)
            existing_query = PropertyUnit.query.filter_by(name=data['name'])
            if company_id:
                existing_query = existing_query.filter_by(company_id=company_id)
            else:
                existing_query = existing_query.filter(PropertyUnit.company_id.is_(None))
            
            existing = existing_query.filter(PropertyUnit.id != unit_id).first()
            if existing:
                return jsonify({
                    'error': 'Nome unità già esistente',
                    'details': f"Già presente unità con nome '{data['name']}' per questa azienda"
                }), 409
        
        # Aggiornamento campi
        for field, value in data.items():
            setattr(unit, field, value)
        
        db.session.commit()
        
        # Ricarica per ottenere le relazioni aggiornate
        db.session.refresh(unit)
        
        unit_data = property_unit_schema.dump(unit)
        unit_data['property_type_name'] = unit.property_type.name if unit.property_type else None
        unit_data['company_name'] = unit.company_name
        unit_data['full_address'] = unit.get_full_address()
        unit_data['connected_pods_count'] = unit.property_pods.count()
        
        return jsonify({
            'message': 'Unità immobiliare aggiornata con successo',
            'property_unit': unit_data
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Errore durante l\'aggiornamento dell\'unità immobiliare', 'details': str(e)}), 500


@api_v1_bp.route('/property-units/<int:unit_id>', methods=['DELETE'])
@jwt_required()
def delete_property_unit(unit_id):
    """
    Elimina un'unità immobiliare.
    Solo gli utenti Rohirrim e Lord possono eliminare unità immobiliari.
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_manage_property_units(current_user):
            return jsonify({'error': 'Non autorizzato a eliminare unità immobiliari'}), 403
        
        # Trova l'unità
        unit = PropertyUnit.query.filter_by(id=unit_id).first()
        if not unit:
            return jsonify({'error': 'Unità immobiliare non trovata'}), 404
        
        # Verifica se ci sono POD connessi
        if unit.property_pods.count() > 0:
            return jsonify({
                'error': 'Impossibile eliminare unità con POD connessi',
                'details': 'Rimuovere prima tutti i POD collegati a questa unità'
            }), 400
        
        # Soft delete - disattiva invece di eliminare fisicamente
        unit.is_active = False
        db.session.commit()
        
        return jsonify({
            'message': 'Unità immobiliare eliminata con successo',
            'unit_id': unit_id
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Errore durante l\'eliminazione dell\'unità immobiliare', 'details': str(e)}), 500


@api_v1_bp.route('/property-units/<int:unit_id>/occupancy', methods=['PATCH'])
@jwt_required()
def update_property_unit_occupancy(unit_id):
    """
    Aggiorna lo stato di occupazione di un'unità immobiliare.
    Solo gli utenti Rohirrim e Lord possono modificare l'occupazione.
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_manage_property_units(current_user):
            return jsonify({'error': 'Non autorizzato a modificare l\'occupazione'}), 403
        
        # Trova l'unità
        unit = PropertyUnit.query.filter_by(id=unit_id).first()
        if not unit:
            return jsonify({'error': 'Unità immobiliare non trovata'}), 404
        
        # Validazione dati
        try:
            data = property_unit_occupancy_schema.load(request.get_json())
        except ValidationError as err:
            return jsonify({'error': 'Dati non validi', 'details': err.messages}), 400
        
        # Aggiorna occupazione
        unit.is_occupied = data['is_occupied']
        
        # Aggiungi nota se fornita (potresti voler salvare questo in un campo notes)
        if data.get('notes'):
            if unit.description:
                unit.description += f"\n\nNota occupazione: {data['notes']}"
            else:
                unit.description = f"Nota occupazione: {data['notes']}"
        
        db.session.commit()
        
        unit_data = property_unit_schema.dump(unit)
        unit_data['property_type_name'] = unit.property_type.name if unit.property_type else None
        unit_data['company_name'] = unit.company_name
        unit_data['full_address'] = unit.get_full_address()
        unit_data['connected_pods_count'] = unit.property_pods.count()
        
        return jsonify({
            'message': f'Unità immobiliare marcata come {"occupata" if data["is_occupied"] else "libera"}',
            'property_unit': unit_data
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Errore durante l\'aggiornamento dell\'occupazione', 'details': str(e)}), 500


@api_v1_bp.route('/property-units/bulk-actions', methods=['POST'])
@jwt_required()
def bulk_actions_property_units():
    """
    Esegue azioni bulk su unità immobiliari.
    Solo gli utenti Rohirrim e Lord possono eseguire azioni bulk.
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_manage_property_units(current_user):
            return jsonify({'error': 'Non autorizzato a eseguire azioni bulk'}), 403
        
        # Validazione dati
        try:
            data = property_unit_bulk_action_schema.load(request.get_json())
        except ValidationError as err:
            return jsonify({'error': 'Dati non validi', 'details': err.messages}), 400
        
        # Trova le unità
        units = PropertyUnit.query.filter(PropertyUnit.id.in_(data['ids'])).all()
        
        if not units:
            return jsonify({'error': 'Nessuna unità immobiliare trovata'}), 404
        
        if len(units) != len(data['ids']):
            return jsonify({'error': 'Alcune unità immobiliari non sono state trovate'}), 404
        
        # Verifica parametri aggiuntivi per azioni specifiche
        action = data['action']
        if action == 'change_company' and not data.get('target_company_id'):
            return jsonify({'error': 'ID azienda target obbligatorio per cambio azienda'}), 400
        
        if action == 'change_type' and not data.get('target_property_type_id'):
            return jsonify({'error': 'ID tipo proprietà target obbligatorio per cambio tipo'}), 400
        
        # Verifica esistenza target per azioni specifiche
        if action == 'change_company':
            target_company = Company.query.filter_by(id=data['target_company_id'], is_active=True).first()
            if not target_company:
                return jsonify({'error': 'Azienda target non trovata o non attiva'}), 404
        
        if action == 'change_type':
            target_type = PropertyType.query.filter_by(id=data['target_property_type_id'], is_active=True).first()
            if not target_type:
                return jsonify({'error': 'Tipo proprietà target non trovato o non attivo'}), 404
        
        # Esegui azione
        updated_count = 0
        
        for unit in units:
            if action == 'activate':
                unit.is_active = True
                updated_count += 1
            elif action == 'deactivate':
                unit.is_active = False
                updated_count += 1
            elif action == 'occupy':
                unit.is_occupied = True
                updated_count += 1
            elif action == 'vacate':
                unit.is_occupied = False
                updated_count += 1
            elif action == 'change_company':
                unit.company_id = data['target_company_id']
                updated_count += 1
            elif action == 'change_type':
                unit.property_type_id = data['target_property_type_id']
                updated_count += 1
            elif action == 'delete':
                # Verifica se ha POD connessi
                if unit.property_pods.count() == 0:
                    unit.is_active = False  # Soft delete
                    updated_count += 1
        
        db.session.commit()
        
        return jsonify({
            'message': f'Azione {action} eseguita con successo',
            'updated_count': updated_count,
            'total_requested': len(data['ids'])
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Errore durante l\'esecuzione dell\'azione bulk', 'details': str(e)}), 500


@api_v1_bp.route('/property-units/stats', methods=['GET'])
@jwt_required()
def get_property_unit_stats():
    """
    Ottiene statistiche sulle unità immobiliari.
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_view_property_units(current_user):
            return jsonify({'error': 'Non autorizzato a visualizzare le statistiche'}), 403
        
        # Statistiche generali
        total_units = PropertyUnit.query.count()
        active_units = PropertyUnit.query.filter_by(is_active=True).count()
        occupied_units = PropertyUnit.query.filter_by(is_active=True, is_occupied=True).count()
        available_units = active_units - occupied_units
        
        # Calcoli metratura
        total_sqm_result = db.session.query(func.sum(PropertyUnit.square_meters)).filter_by(is_active=True).scalar()
        total_square_meters = float(total_sqm_result) if total_sqm_result else 0.0
        
        avg_sqm_result = db.session.query(func.avg(PropertyUnit.square_meters)).filter_by(is_active=True).scalar()
        average_square_meters = float(avg_sqm_result) if avg_sqm_result else 0.0
        
        # Statistiche per tipo proprietà
        type_stats = db.session.query(
            PropertyType.name,
            func.count(PropertyUnit.id).label('count')
        ).join(PropertyUnit, PropertyType.id == PropertyUnit.property_type_id)\
        .filter(PropertyUnit.is_active == True).group_by(PropertyType.name).all()
        
        by_property_type = {stat[0]: stat[1] for stat in type_stats}
        
        # Statistiche per città
        city_stats = db.session.query(
            PropertyUnit.city,
            func.count(PropertyUnit.id).label('count')
        ).filter(PropertyUnit.is_active == True, PropertyUnit.city.isnot(None))\
        .group_by(PropertyUnit.city).all()
        
        by_city = {stat[0]: stat[1] for stat in city_stats}
        
        # Statistiche per azienda
        company_stats = db.session.query(
            Company.display_name,
            func.count(PropertyUnit.id).label('count')
        ).join(PropertyUnit, Company.id == PropertyUnit.company_id)\
        .filter(PropertyUnit.is_active == True).group_by(Company.display_name).all()
        
        by_company = {stat[0]: stat[1] for stat in company_stats}
        
        # Tasso di occupazione
        occupancy_rate = (occupied_units / active_units * 100) if active_units > 0 else 0.0
        
        stats = {
            'total_units': total_units,
            'active_units': active_units,
            'occupied_units': occupied_units,
            'available_units': available_units,
            'total_square_meters': round(total_square_meters, 2),
            'average_square_meters': round(average_square_meters, 2),
            'by_property_type': by_property_type,
            'by_city': by_city,
            'by_company': by_company,
            'occupancy_rate': round(occupancy_rate, 2)
        }
        
        return jsonify({'stats': stats}), 200
        
    except Exception as e:
        return jsonify({'error': 'Errore durante il calcolo delle statistiche', 'details': str(e)}), 500


@api_v1_bp.route('/property-units/check-duplicate', methods=['POST'])
@jwt_required()
def check_duplicate_property_unit():
    """
    Controlla se esiste già un'unità immobiliare con lo stesso nome per l'azienda.
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_view_property_units(current_user):
            return jsonify({'error': 'Non autorizzato'}), 403
        
        # Validazione dati
        try:
            data = property_unit_duplicate_check_schema.load(request.get_json())
        except ValidationError as err:
            return jsonify({'error': 'Dati non validi', 'details': err.messages}), 400
        
        # Controllo duplicato
        query = PropertyUnit.query.filter_by(name=data['name'])
        
        if data.get('company_id'):
            query = query.filter_by(company_id=data['company_id'])
        else:
            query = query.filter(PropertyUnit.company_id.is_(None))
        
        if data.get('exclude_id'):
            query = query.filter(PropertyUnit.id != data['exclude_id'])
        
        existing = query.first()
        
        return jsonify({
            'exists': existing is not None,
            'existing_unit': property_unit_schema.dump(existing) if existing else None
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Errore durante il controllo duplicati', 'details': str(e)}), 500


@api_v1_bp.route('/property-units/property-types/<int:type_id>', methods=['GET'])
@jwt_required()
def get_property_units_by_type(type_id):
    """
    Ottiene tutte le unità immobiliari per un tipo specifico.
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_view_property_units(current_user):
            return jsonify({'error': 'Non autorizzato'}), 403
        
        # Verifica esistenza tipo proprietà
        property_type = PropertyType.query.filter_by(id=type_id).first()
        if not property_type:
            return jsonify({'error': 'Tipo di proprietà non trovato'}), 404
        
        # Ottieni parametri query
        include_inactive = request.args.get('include_inactive', 'false').lower() == 'true'
        
        # Ottieni unità per tipo
        if include_inactive:
            units = PropertyUnit.query.filter_by(property_type_id=type_id).order_by(PropertyUnit.name).all()
        else:
            units = PropertyUnit.get_by_type(type_id)
        
        # Serializzazione
        result = []
        for unit in units:
            unit_data = property_unit_schema.dump(unit)
            unit_data['property_type_name'] = property_type.name
            unit_data['company_name'] = unit.company_name
            unit_data['full_address'] = unit.get_full_address()
            unit_data['connected_pods_count'] = unit.property_pods.count()
            result.append(unit_data)
        
        return jsonify({
            'property_type': {
                'id': property_type.id,
                'name': property_type.name,
                'description': property_type.description
            },
            'property_units': result,
            'total_count': len(result)
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Errore durante il recupero delle unità immobiliari', 'details': str(e)}), 500


@api_v1_bp.route('/property-units/companies/<int:company_id>', methods=['GET'])
@jwt_required()
def get_property_units_by_company(company_id):
    """
    Ottiene tutte le unità immobiliari per un'azienda specifica.
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_view_property_units(current_user):
            return jsonify({'error': 'Non autorizzato'}), 403
        
        # Verifica esistenza azienda
        company = Company.query.filter_by(id=company_id).first()
        if not company:
            return jsonify({'error': 'Azienda non trovata'}), 404
        
        # Ottieni parametri query
        include_inactive = request.args.get('include_inactive', 'false').lower() == 'true'
        
        # Ottieni unità per azienda
        units = PropertyUnit.get_by_company(company_id, active_only=not include_inactive)
        
        # Serializzazione
        result = []
        for unit in units:
            unit_data = property_unit_schema.dump(unit)
            unit_data['property_type_name'] = unit.property_type.name if unit.property_type else None
            unit_data['company_name'] = company.display_name
            unit_data['full_address'] = unit.get_full_address()
            unit_data['connected_pods_count'] = unit.property_pods.count()
            result.append(unit_data)
        
        return jsonify({
            'company': {
                'id': company.id,
                'name': company.display_name
            },
            'property_units': result,
            'total_count': len(result)
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Errore durante il recupero delle unità immobiliari', 'details': str(e)}), 500


@api_v1_bp.route('/property-units/search-by-address', methods=['POST'])
@jwt_required()
def search_property_units_by_address():
    """
    Cerca unità immobiliari per indirizzo.
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_view_property_units(current_user):
            return jsonify({'error': 'Non autorizzato'}), 403
        
        # Validazione dati
        try:
            data = property_unit_address_search_schema.load(request.get_json())
        except ValidationError as err:
            return jsonify({'error': 'Dati non validi', 'details': err.messages}), 400
        
        query_term = data['address_query']
        exact_match = data.get('exact_match', False)
        
        # Costruisci query di ricerca
        if exact_match:
            # Ricerca esatta
            query = PropertyUnit.query.filter(
                or_(
                    PropertyUnit.address == query_term,
                    PropertyUnit.city == query_term
                )
            )
        else:
            # Ricerca fuzzy
            search_term = f"%{query_term}%"
            query = PropertyUnit.query.filter(
                or_(
                    PropertyUnit.address.ilike(search_term),
                    PropertyUnit.city.ilike(search_term),
                    PropertyUnit.postal_code.ilike(search_term)
                )
            )
        
        # Solo unità attive
        query = query.filter_by(is_active=True)
        units = query.order_by(PropertyUnit.name).all()
        
        # Serializzazione
        result = []
        for unit in units:
            unit_data = property_unit_schema.dump(unit)
            unit_data['property_type_name'] = unit.property_type.name if unit.property_type else None
            unit_data['company_name'] = unit.company_name
            unit_data['full_address'] = unit.get_full_address()
            unit_data['connected_pods_count'] = unit.property_pods.count()
            result.append(unit_data)
        
        return jsonify({
            'search_query': query_term,
            'exact_match': exact_match,
            'property_units': result,
            'total_found': len(result)
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Errore durante la ricerca per indirizzo', 'details': str(e)}), 500
