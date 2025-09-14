# Property Types CRUD API - Sistema Completo

from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_current_user
from sqlalchemy import or_, func, text
from sqlalchemy.exc import IntegrityError
from datetime import date, datetime, timedelta
from ...models.property_type import PropertyType
from ...models.property_unit import PropertyUnit
from ...schemas import (
    property_type_schema, property_types_schema,
    property_type_create_schema, property_type_update_schema,
    property_type_list_schema, property_type_stats_schema,
    property_type_duplicate_check_schema, property_type_bulk_action_schema,
    property_type_units_schema, property_type_validation_schema,
    property_type_template_schema
)
from ...extensions import db
from marshmallow import ValidationError
from . import api_v1_bp


def user_can_manage_property_types(user):
    """Verifica se l'utente può gestire i tipi di proprietà (solo Rohirrim e Lord)."""
    return user and user.is_active and user.role and (user.role.is_rohirrim() or user.role.is_lord())


def user_can_view_property_types(user):
    """Verifica se l'utente può visualizzare i tipi di proprietà."""
    if not user or not user.is_active:
        return False
    
    # Rohirrim, Lord e Dunedain possono tutti visualizzare i tipi di proprietà
    if user.role and (user.role.is_rohirrim() or user.role.is_lord() or user.role.is_dunedain()):
        return True
    
    return False


@api_v1_bp.route('/property-types', methods=['GET'])
@jwt_required()
def get_property_types():
    """
    Ottiene la lista dei tipi di proprietà con filtri.
    Tutti i ruoli possono visualizzare i tipi di proprietà.
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_view_property_types(current_user):
            return jsonify({'error': 'Non autorizzato a visualizzare i tipi di proprietà'}), 403
        
        # Validazione parametri
        try:
            args = property_type_list_schema.load(request.args)
        except ValidationError as err:
            return jsonify({'error': 'Parametri non validi', 'details': err.messages}), 400
        
        # Query base
        query = PropertyType.query
        
        # Filtri
        if args.get('is_active') is not None:
            query = query.filter(PropertyType.is_active == args['is_active'])
        
        # Ricerca testuale
        if args.get('search'):
            search_term = f"%{args['search']}%"
            query = query.filter(
                or_(
                    PropertyType.name.ilike(search_term),
                    PropertyType.description.ilike(search_term),
                    PropertyType.code.ilike(search_term)
                )
            )
        
        # Ordinamento
        sort_by = args.get('sort_by', 'name')
        sort_order = args.get('sort_order', 'asc')
        
        if sort_by == 'units_count':
            # Ordinamento per numero di unità (tramite subquery)
            units_count_subquery = db.session.query(
                PropertyUnit.property_type_id,
                func.count(PropertyUnit.id).label('units_count')
            ).group_by(PropertyUnit.property_type_id).subquery()
            
            query = query.outerjoin(
                units_count_subquery,
                PropertyType.id == units_count_subquery.c.property_type_id
            )
            
            sort_column = units_count_subquery.c.units_count
        else:
            sort_column = getattr(PropertyType, sort_by, PropertyType.name)
        
        if sort_order == 'desc':
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())
        
        # Paginazione
        page = args.get('page', 1)
        per_page = args.get('per_page', 20)
        
        types = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        # Serializzazione con dati aggiuntivi
        result = []
        for property_type in types.items:
            type_data = property_type_schema.dump(property_type)
            type_data['units_count'] = property_type.get_units_count()
            result.append(type_data)
        
        return jsonify({
            'property_types': result,
            'pagination': {
                'page': types.page,
                'per_page': types.per_page,
                'total': types.total,
                'pages': types.pages,
                'has_next': types.has_next,
                'has_prev': types.has_prev
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Errore durante il recupero dei tipi di proprietà', 'details': str(e)}), 500


@api_v1_bp.route('/property-types', methods=['POST'])
@jwt_required()
def create_property_type():
    """
    Crea un nuovo tipo di proprietà.
    Solo gli utenti Rohirrim e Lord possono creare tipi di proprietà.
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_manage_property_types(current_user):
            return jsonify({'error': 'Non autorizzato a creare tipi di proprietà'}), 403
        
        # Validazione dati
        try:
            data = property_type_create_schema.load(request.get_json())
        except ValidationError as err:
            return jsonify({'error': 'Dati non validi', 'details': err.messages}), 400
        
        # Controllo duplicati per nome
        existing_name = PropertyType.query.filter_by(name=data['name']).first()
        if existing_name:
            return jsonify({
                'error': 'Tipo di proprietà già esistente',
                'details': f"Già presente tipo di proprietà con nome '{data['name']}'"
            }), 409
        
        # Controllo duplicati per codice se specificato
        if data.get('code'):
            existing_code = PropertyType.query.filter_by(code=data['code']).first()
            if existing_code:
                return jsonify({
                    'error': 'Codice già esistente',
                    'details': f"Già presente tipo di proprietà con codice '{data['code']}'"
                }), 409
        
        # Creazione nuovo tipo
        new_type = PropertyType(
            name=data['name'],
            description=data.get('description'),
            code=data.get('code')
        )
        
        db.session.add(new_type)
        db.session.commit()
        
        # Ricarica per ottenere i dati completi
        db.session.refresh(new_type)
        
        type_data = property_type_schema.dump(new_type)
        type_data['units_count'] = 0
        
        return jsonify({
            'message': 'Tipo di proprietà creato con successo',
            'property_type': type_data
        }), 201
        
    except IntegrityError as e:
        db.session.rollback()
        return jsonify({'error': 'Errore di integrità dei dati', 'details': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Errore durante la creazione del tipo di proprietà', 'details': str(e)}), 500


@api_v1_bp.route('/property-types/<int:type_id>', methods=['GET'])
@jwt_required()
def get_property_type(type_id):
    """
    Ottiene i dettagli di un tipo di proprietà specifico.
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_view_property_types(current_user):
            return jsonify({'error': 'Non autorizzato a visualizzare i tipi di proprietà'}), 403
        
        # Trova il tipo
        property_type = PropertyType.query.filter_by(id=type_id).first()
        if not property_type:
            return jsonify({'error': 'Tipo di proprietà non trovato'}), 404
        
        # Serializzazione con dati aggiuntivi
        type_data = property_type_schema.dump(property_type)
        type_data['units_count'] = property_type.get_units_count()
        
        # Aggiungi statistiche delle unità associate
        units = property_type.property_units.filter_by(is_active=True).all()
        units_stats = {
            'total_units': len(units),
            'occupied_units': sum(1 for unit in units if unit.is_occupied),
            'available_units': sum(1 for unit in units if not unit.is_occupied),
            'total_square_meters': sum(float(unit.square_meters) for unit in units if unit.square_meters),
            'average_square_meters': 0
        }
        
        if units_stats['total_units'] > 0:
            units_stats['average_square_meters'] = units_stats['total_square_meters'] / units_stats['total_units']
        
        type_data['units_statistics'] = units_stats
        
        return jsonify({
            'property_type': type_data
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Errore durante il recupero del tipo di proprietà', 'details': str(e)}), 500


@api_v1_bp.route('/property-types/<int:type_id>', methods=['PUT'])
@jwt_required()
def update_property_type(type_id):
    """
    Aggiorna un tipo di proprietà esistente.
    Solo gli utenti Rohirrim e Lord possono aggiornare tipi di proprietà.
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_manage_property_types(current_user):
            return jsonify({'error': 'Non autorizzato a modificare tipi di proprietà'}), 403
        
        # Trova il tipo
        property_type = PropertyType.query.filter_by(id=type_id).first()
        if not property_type:
            return jsonify({'error': 'Tipo di proprietà non trovato'}), 404
        
        # Validazione dati
        try:
            data = property_type_update_schema.load(request.get_json())
        except ValidationError as err:
            return jsonify({'error': 'Dati non validi', 'details': err.messages}), 400
        
        # Controllo duplicati per nome se cambia
        if 'name' in data and data['name'] != property_type.name:
            existing_name = PropertyType.query.filter_by(name=data['name']).filter(PropertyType.id != type_id).first()
            if existing_name:
                return jsonify({
                    'error': 'Nome già esistente',
                    'details': f"Già presente tipo di proprietà con nome '{data['name']}'"
                }), 409
        
        # Controllo duplicati per codice se cambia
        if 'code' in data and data.get('code') and data['code'] != property_type.code:
            existing_code = PropertyType.query.filter_by(code=data['code']).filter(PropertyType.id != type_id).first()
            if existing_code:
                return jsonify({
                    'error': 'Codice già esistente',
                    'details': f"Già presente tipo di proprietà con codice '{data['code']}'"
                }), 409
        
        # Controllo se si sta disattivando un tipo con unità associate
        if 'is_active' in data and not data['is_active'] and property_type.get_units_count() > 0:
            return jsonify({
                'error': 'Impossibile disattivare tipo con unità associate',
                'details': f"Il tipo ha {property_type.get_units_count()} unità immobiliari associate. Riassegnare prima le unità."
            }), 400
        
        # Aggiornamento campi
        for field, value in data.items():
            setattr(property_type, field, value)
        
        db.session.commit()
        
        type_data = property_type_schema.dump(property_type)
        type_data['units_count'] = property_type.get_units_count()
        
        return jsonify({
            'message': 'Tipo di proprietà aggiornato con successo',
            'property_type': type_data
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Errore durante l\'aggiornamento del tipo di proprietà', 'details': str(e)}), 500


@api_v1_bp.route('/property-types/<int:type_id>', methods=['DELETE'])
@jwt_required()
def delete_property_type(type_id):
    """
    Elimina un tipo di proprietà.
    Solo gli utenti Rohirrim e Lord possono eliminare tipi di proprietà.
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_manage_property_types(current_user):
            return jsonify({'error': 'Non autorizzato a eliminare tipi di proprietà'}), 403
        
        # Trova il tipo
        property_type = PropertyType.query.filter_by(id=type_id).first()
        if not property_type:
            return jsonify({'error': 'Tipo di proprietà non trovato'}), 404
        
        # Verifica se ci sono unità associate
        units_count = property_type.get_units_count()
        if units_count > 0:
            return jsonify({
                'error': 'Impossibile eliminare tipo con unità associate',
                'details': f"Il tipo ha {units_count} unità immobiliari associate. Riassegnare prima le unità."
            }), 400
        
        # Soft delete - disattiva invece di eliminare fisicamente
        property_type.is_active = False
        db.session.commit()
        
        return jsonify({
            'message': 'Tipo di proprietà eliminato con successo',
            'type_id': type_id
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Errore durante l\'eliminazione del tipo di proprietà', 'details': str(e)}), 500


@api_v1_bp.route('/property-types/<int:type_id>/units', methods=['GET'])
@jwt_required()
def get_property_type_units(type_id):
    """
    Ottiene tutte le unità immobiliari per un tipo di proprietà specifico.
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_view_property_types(current_user):
            return jsonify({'error': 'Non autorizzato'}), 403
        
        # Verifica esistenza tipo
        property_type = PropertyType.query.filter_by(id=type_id).first()
        if not property_type:
            return jsonify({'error': 'Tipo di proprietà non trovato'}), 404
        
        # Validazione parametri opzionali
        try:
            args = property_type_units_schema.load(request.args)
        except ValidationError as err:
            return jsonify({'error': 'Parametri non validi', 'details': err.messages}), 400
        
        # Ottieni unità
        query = property_type.property_units
        
        if not args.get('include_inactive_units', False):
            query = query.filter_by(is_active=True)
        
        units = query.order_by(PropertyUnit.name).all()
        
        # Serializzazione
        from ...schemas import property_unit_schema
        
        if args.get('include_unit_details', True):
            result = []
            for unit in units:
                unit_data = property_unit_schema.dump(unit)
                unit_data['property_type_name'] = property_type.name
                unit_data['company_name'] = unit.company_name
                unit_data['full_address'] = unit.get_full_address()
                unit_data['connected_pods_count'] = unit.property_pods.count()
                result.append(unit_data)
        else:
            # Solo dati essenziali
            result = [
                {
                    'id': unit.id,
                    'name': unit.name,
                    'square_meters': float(unit.square_meters) if unit.square_meters else 0,
                    'is_active': unit.is_active,
                    'is_occupied': unit.is_occupied
                }
                for unit in units
            ]
        
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
        return jsonify({'error': 'Errore durante il recupero delle unità', 'details': str(e)}), 500


@api_v1_bp.route('/property-types/bulk-actions', methods=['POST'])
@jwt_required()
def bulk_actions_property_types():
    """
    Esegue azioni bulk su tipi di proprietà.
    Solo gli utenti Rohirrim e Lord possono eseguire azioni bulk.
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_manage_property_types(current_user):
            return jsonify({'error': 'Non autorizzato a eseguire azioni bulk'}), 403
        
        # Validazione dati
        try:
            data = property_type_bulk_action_schema.load(request.get_json())
        except ValidationError as err:
            return jsonify({'error': 'Dati non validi', 'details': err.messages}), 400
        
        # Trova i tipi
        types = PropertyType.query.filter(PropertyType.id.in_(data['ids'])).all()
        
        if not types:
            return jsonify({'error': 'Nessun tipo di proprietà trovato'}), 404
        
        if len(types) != len(data['ids']):
            return jsonify({'error': 'Alcuni tipi di proprietà non sono stati trovati'}), 404
        
        # Esegui azione
        action = data['action']
        updated_count = 0
        errors = []
        
        for property_type in types:
            try:
                if action == 'activate':
                    property_type.is_active = True
                    updated_count += 1
                elif action == 'deactivate':
                    # Verifica se ha unità associate
                    if property_type.get_units_count() > 0:
                        errors.append(f"Tipo '{property_type.name}' ha unità associate")
                    else:
                        property_type.is_active = False
                        updated_count += 1
                elif action == 'delete':
                    # Verifica se ha unità associate
                    if property_type.get_units_count() > 0:
                        errors.append(f"Tipo '{property_type.name}' ha unità associate")
                    else:
                        property_type.is_active = False  # Soft delete
                        updated_count += 1
            except Exception as e:
                errors.append(f"Errore su tipo '{property_type.name}': {str(e)}")
        
        db.session.commit()
        
        response = {
            'message': f'Azione {action} eseguita',
            'updated_count': updated_count,
            'total_requested': len(data['ids'])
        }
        
        if errors:
            response['errors'] = errors
        
        return jsonify(response), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Errore durante l\'esecuzione dell\'azione bulk', 'details': str(e)}), 500


@api_v1_bp.route('/property-types/stats', methods=['GET'])
@jwt_required()
def get_property_type_stats():
    """
    Ottiene statistiche sui tipi di proprietà.
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_view_property_types(current_user):
            return jsonify({'error': 'Non autorizzato a visualizzare le statistiche'}), 403
        
        # Statistiche generali
        total_types = PropertyType.query.count()
        active_types = PropertyType.query.filter_by(is_active=True).count()
        inactive_types = total_types - active_types
        
        # Statistiche unità
        total_units = PropertyUnit.query.filter_by(is_active=True).count()
        
        # Distribuzione unità per tipo
        units_distribution_raw = db.session.query(
            PropertyType.name,
            func.count(PropertyUnit.id).label('count')
        ).join(PropertyUnit, PropertyType.id == PropertyUnit.property_type_id)\
        .filter(PropertyUnit.is_active == True)\
        .group_by(PropertyType.name).all()
        
        units_distribution = {stat[0]: stat[1] for stat in units_distribution_raw}
        
        # Tipo più e meno usato
        most_used_type = None
        least_used_type = None
        
        if units_distribution:
            most_used_type = max(units_distribution, key=units_distribution.get)
            least_used_type = min(units_distribution, key=units_distribution.get)
        
        # Tipi con e senza unità
        types_with_units = len([t for t in units_distribution.values() if t > 0])
        types_without_units = active_types - types_with_units
        
        stats = {
            'total_types': total_types,
            'active_types': active_types,
            'inactive_types': inactive_types,
            'total_units': total_units,
            'most_used_type': most_used_type,
            'least_used_type': least_used_type,
            'types_with_units': types_with_units,
            'types_without_units': types_without_units,
            'units_distribution': units_distribution
        }
        
        return jsonify({'stats': stats}), 200
        
    except Exception as e:
        return jsonify({'error': 'Errore durante il calcolo delle statistiche', 'details': str(e)}), 500


@api_v1_bp.route('/property-types/check-duplicate', methods=['POST'])
@jwt_required()
def check_duplicate_property_type():
    """
    Controlla se esiste già un tipo di proprietà con lo stesso nome o codice.
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_view_property_types(current_user):
            return jsonify({'error': 'Non autorizzato'}), 403
        
        # Validazione dati
        try:
            data = property_type_duplicate_check_schema.load(request.get_json())
        except ValidationError as err:
            return jsonify({'error': 'Dati non validi', 'details': err.messages}), 400
        
        # Controllo duplicato nome
        name_query = PropertyType.query.filter_by(name=data['name'])
        if data.get('exclude_id'):
            name_query = name_query.filter(PropertyType.id != data['exclude_id'])
        
        existing_name = name_query.first()
        
        # Controllo duplicato codice se specificato
        existing_code = None
        if data.get('code'):
            code_query = PropertyType.query.filter_by(code=data['code'])
            if data.get('exclude_id'):
                code_query = code_query.filter(PropertyType.id != data['exclude_id'])
            existing_code = code_query.first()
        
        return jsonify({
            'name_exists': existing_name is not None,
            'code_exists': existing_code is not None,
            'existing_name_type': property_type_schema.dump(existing_name) if existing_name else None,
            'existing_code_type': property_type_schema.dump(existing_code) if existing_code else None
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Errore durante il controllo duplicati', 'details': str(e)}), 500


@api_v1_bp.route('/property-types/templates', methods=['GET'])
@jwt_required()
def get_property_type_templates():
    """
    Ottiene template predefiniti per tipi di proprietà.
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_view_property_types(current_user):
            return jsonify({'error': 'Non autorizzato'}), 403
        
        # Validazione parametri
        try:
            args = property_type_template_schema.load(request.args)
        except ValidationError as err:
            return jsonify({'error': 'Parametri non validi', 'details': err.messages}), 400
        
        category = args.get('category', 'residenziale')
        
        # Template predefiniti per categoria
        templates = {
            'residenziale': [
                {'name': 'Villa', 'code': 'VILLA', 'description': 'Villa unifamiliare'},
                {'name': 'Appartamento', 'code': 'APP', 'description': 'Appartamento in condominio'},
                {'name': 'Attico', 'code': 'ATTICO', 'description': 'Appartamento all\'ultimo piano'},
                {'name': 'Loft', 'code': 'LOFT', 'description': 'Spazio aperto convertito'},
                {'name': 'Monolocale', 'code': 'MONO', 'description': 'Appartamento di un locale'},
                {'name': 'Bilocale', 'code': 'BILO', 'description': 'Appartamento di due locali'},
                {'name': 'Trilocale', 'code': 'TRILO', 'description': 'Appartamento di tre locali'},
                {'name': 'Quadrilocale', 'code': 'QUADRI', 'description': 'Appartamento di quattro locali'},
                {'name': 'Rustico', 'code': 'RUSTICO', 'description': 'Proprietà rurale da ristrutturare'},
                {'name': 'Casale', 'code': 'CASALE', 'description': 'Casa di campagna'}
            ],
            'commerciale': [
                {'name': 'Ufficio', 'code': 'UFF', 'description': 'Spazio per uffici'},
                {'name': 'Negozio', 'code': 'NEG', 'description': 'Locale commerciale'},
                {'name': 'Showroom', 'code': 'SHOW', 'description': 'Spazio espositivo'},
                {'name': 'Ristorante', 'code': 'RIST', 'description': 'Locale per ristorazione'},
                {'name': 'Albergo', 'code': 'HOTEL', 'description': 'Struttura ricettiva'}
            ],
            'industriale': [
                {'name': 'Magazzino', 'code': 'MAG', 'description': 'Spazio per stoccaggio'},
                {'name': 'Capannone', 'code': 'CAP', 'description': 'Struttura industriale'},
                {'name': 'Laboratorio', 'code': 'LAB', 'description': 'Spazio per produzione'},
                {'name': 'Deposito', 'code': 'DEP', 'description': 'Area di deposito'}
            ],
            'altro': [
                {'name': 'Garage', 'code': 'GAR', 'description': 'Box auto'},
                {'name': 'Cantina', 'code': 'CANT', 'description': 'Locale interrato'},
                {'name': 'Soffitta', 'code': 'SOFF', 'description': 'Locale sottotetto'},
                {'name': 'Terreno', 'code': 'TERR', 'description': 'Area edificabile o agricola'}
            ]
        }
        
        return jsonify({
            'category': category,
            'templates': templates.get(category, []),
            'all_categories': list(templates.keys())
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Errore durante il recupero dei template', 'details': str(e)}), 500


@api_v1_bp.route('/property-types/validate', methods=['POST'])
@jwt_required()
def validate_property_type():
    """
    Valida i dati di un tipo di proprietà senza salvare.
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_view_property_types(current_user):
            return jsonify({'error': 'Non autorizzato'}), 403
        
        # Validazione dati
        try:
            data = property_type_validation_schema.load(request.get_json())
        except ValidationError as err:
            return jsonify({'error': 'Dati non validi', 'details': err.messages}), 400
        
        # Controlli aggiuntivi
        validations = {
            'name_valid': True,
            'code_valid': True,
            'name_available': True,
            'code_available': True,
            'suggestions': []
        }
        
        # Controllo disponibilità nome
        existing_name = PropertyType.query.filter_by(name=data['name']).first()
        if existing_name:
            validations['name_available'] = False
        
        # Controllo disponibilità codice
        if data.get('code'):
            existing_code = PropertyType.query.filter_by(code=data['code']).first()
            if existing_code:
                validations['code_available'] = False
        
        # Suggerimenti se nome non è nella lista comune
        common_types = [
            'Villa', 'Appartamento', 'Attico', 'Loft', 'Ufficio', 'Negozio', 
            'Magazzino', 'Garage', 'Cantina'
        ]
        
        if data['name'] not in common_types:
            # Trova suggerimenti simili
            suggestions = [t for t in common_types if data['name'].lower() in t.lower() or t.lower() in data['name'].lower()]
            validations['suggestions'] = suggestions[:3]  # Primi 3 suggerimenti
        
        return jsonify({
            'valid': all([
                validations['name_valid'],
                validations['code_valid'],
                validations['name_available'],
                validations['code_available']
            ]),
            'validations': validations
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Errore durante la validazione', 'details': str(e)}), 500
