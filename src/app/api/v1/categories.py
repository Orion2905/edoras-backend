# Categories CRUD API - Sistema Completo

from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_current_user
from sqlalchemy import or_, func, text
from sqlalchemy.exc import IntegrityError
from datetime import date, datetime, timedelta
from ...models.category import Category
from ...models.subcategory import Subcategory  
from ...models.invoice import Invoice
from ...schemas import (
    category_schema, categories_schema,
    category_create_schema, category_update_schema,
    category_list_schema, category_stats_schema,
    category_duplicate_check_schema, category_bulk_action_schema
)
from ...extensions import db
from marshmallow import ValidationError
from . import api_v1_bp


def user_can_manage_categories(user):
    """Verifica se l'utente può gestire le categorie (solo Rohirrim)."""
    return user and user.is_active and user.role and user.role.is_rohirrim()


def user_can_view_categories(user):
    """Verifica se l'utente può visualizzare le categorie."""
    if not user or not user.is_active:
        return False
    
    # Rohirrim, Lord e Dunedain possono tutti visualizzare le categorie
    if user.role and (user.role.is_rohirrim() or user.role.is_lord() or user.role.is_dunedain()):
        return True
    
    return False


@api_v1_bp.route('/categories', methods=['GET'])
@jwt_required()
def get_categories():
    """
    Ottiene la lista delle categorie con filtri avanzati.
    Tutti i ruoli possono visualizzare le categorie.
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_view_categories(current_user):
            return jsonify({
                'error': 'Accesso negato',
                'message': 'Permessi insufficienti per visualizzare le categorie'
            }), 403
        
        # Validazione parametri query
        args = category_list_schema.load(request.args)
        
        # Query base
        query = Category.query
        
        # Filtro attività
        if args.get('is_active') is not None:
            query = query.filter(Category.is_active == args['is_active'])
        else:
            # Default: solo categorie attive
            query = query.filter(Category.is_active == True)
        
        # Applica filtri
        if args.get('search'):
            search_term = f"%{args['search']}%"
            query = query.filter(
                or_(
                    Category.name.ilike(search_term),
                    Category.description.ilike(search_term),
                    Category.code.ilike(search_term)
                )
            )
        
        # Filtro per categorie con sottocategorie
        if args.get('has_subcategories') is not None:
            if args['has_subcategories']:
                query = query.join(Subcategory).distinct()
            else:
                query = query.outerjoin(Subcategory).filter(Subcategory.id == None)
        
        # Filtro per categorie con fatture
        if args.get('has_invoices') is not None:
            if args['has_invoices']:
                query = query.join(Invoice).filter(Invoice.is_active == True).distinct()
            else:
                query = query.outerjoin(Invoice).filter(
                    or_(Invoice.id == None, Invoice.is_active == False)
                )
        
        # Ordinamento
        sort_by = args.get('sort_by', 'name')
        sort_order = args.get('sort_order', 'asc')
        
        if hasattr(Category, sort_by):
            order_column = getattr(Category, sort_by)
            if sort_order == 'desc':
                query = query.order_by(order_column.desc())
            else:
                query = query.order_by(order_column.asc())
        
        # Paginazione
        page = args.get('page', 1)
        per_page = args.get('per_page', 20)
        pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        # Serializzazione
        categories_data = categories_schema.dump(pagination.items)
        
        return jsonify({
            'categories': categories_data,
            'pagination': {
                'page': pagination.page,
                'pages': pagination.pages,
                'per_page': pagination.per_page,
                'total': pagination.total,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            },
            'user_permissions': {
                'can_edit': user_can_manage_categories(current_user),
                'can_delete': user_can_manage_categories(current_user),
                'can_create': user_can_manage_categories(current_user)
            }
        }), 200
        
    except ValidationError as e:
        return jsonify({
            'error': 'Parametri non validi',
            'details': e.messages
        }), 400
    except Exception as e:
        return jsonify({
            'error': 'Errore interno del server',
            'message': str(e)
        }), 500


@api_v1_bp.route('/categories/<int:category_id>', methods=['GET'])
@jwt_required()
def get_category(category_id):
    """
    Ottiene i dettagli di una categoria specifica.
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_view_categories(current_user):
            return jsonify({
                'error': 'Accesso negato',
                'message': 'Permessi insufficienti per visualizzare le categorie'
            }), 403
        
        category = Category.query.filter_by(id=category_id, is_active=True).first_or_404()
        
        # Serializzazione completa con relazioni
        category_data = category_schema.dump(category)
        
        # Aggiungi statistiche extra
        category_data['invoices_count'] = Invoice.query.filter_by(
            category_id=category.id, 
            is_active=True
        ).count()
        
        return jsonify(category_data), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Errore nel recupero della categoria',
            'message': str(e)
        }), 500


@api_v1_bp.route('/categories', methods=['POST'])
@jwt_required()
def create_category():
    """
    Crea una nuova categoria (solo Rohirrim).
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_manage_categories(current_user):
            return jsonify({
                'error': 'Accesso negato',
                'message': 'Solo i Rohirrim possono creare categorie'
            }), 403
        
        # Validazione dati
        data = category_create_schema.load(request.get_json())
        
        # Verifica unicità nome
        existing_name = Category.query.filter_by(name=data['name']).first()
        if existing_name:
            return jsonify({
                'error': 'Nome categoria già esistente',
                'message': f'Una categoria con nome "{data["name"]}" esiste già',
                'existing_category_id': existing_name.id
            }), 409
        
        # Verifica unicità codice se fornito
        if data.get('code'):
            existing_code = Category.query.filter_by(code=data['code']).first()
            if existing_code:
                return jsonify({
                    'error': 'Codice categoria già esistente',
                    'message': f'Una categoria con codice "{data["code"]}" esiste già',
                    'existing_category_id': existing_code.id
                }), 409
        
        # Creazione categoria
        category = Category(**data)
        
        db.session.add(category)
        db.session.commit()
        
        return jsonify({
            'message': 'Categoria creata con successo',
            'category': category_schema.dump(category)
        }), 201
        
    except ValidationError as e:
        return jsonify({
            'error': 'Dati non validi',
            'details': e.messages
        }), 400
    except IntegrityError as e:
        db.session.rollback()
        return jsonify({
            'error': 'Violazione vincolo di integrità',
            'message': 'Nome o codice categoria già esistente'
        }), 409
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'Errore nella creazione della categoria',
            'message': str(e)
        }), 500


@api_v1_bp.route('/categories/<int:category_id>', methods=['PUT'])
@jwt_required()
def update_category(category_id):
    """
    Aggiorna una categoria esistente (solo Rohirrim).
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_manage_categories(current_user):
            return jsonify({
                'error': 'Accesso negato',
                'message': 'Solo i Rohirrim possono modificare categorie'
            }), 403
        
        category = Category.query.filter_by(id=category_id, is_active=True).first_or_404()
        
        # Validazione dati
        data = category_update_schema.load(request.get_json())
        
        # Verifica unicità nome se cambiato
        if 'name' in data and data['name'] != category.name:
            existing_name = Category.query.filter_by(name=data['name']).first()
            if existing_name:
                return jsonify({
                    'error': 'Nome categoria già esistente',
                    'message': f'Una categoria con nome "{data["name"]}" esiste già'
                }), 409
        
        # Verifica unicità codice se cambiato
        if 'code' in data and data['code'] != category.code:
            if data['code']:  # Solo se non è None/vuoto
                existing_code = Category.query.filter_by(code=data['code']).first()
                if existing_code:
                    return jsonify({
                        'error': 'Codice categoria già esistente',
                        'message': f'Una categoria con codice "{data["code"]}" esiste già'
                    }), 409
        
        # Aggiornamento
        for key, value in data.items():
            if hasattr(category, key):
                setattr(category, key, value)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Categoria aggiornata con successo',
            'category': category_schema.dump(category)
        }), 200
        
    except ValidationError as e:
        return jsonify({
            'error': 'Dati non validi',
            'details': e.messages
        }), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'Errore nell\'aggiornamento della categoria',
            'message': str(e)
        }), 500


@api_v1_bp.route('/categories/<int:category_id>', methods=['DELETE'])
@jwt_required()
def delete_category(category_id):
    """
    Elimina una categoria (solo Rohirrim).
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_manage_categories(current_user):
            return jsonify({
                'error': 'Accesso negato',
                'message': 'Solo i Rohirrim possono eliminare categorie'
            }), 403
        
        category = Category.query.filter_by(id=category_id, is_active=True).first_or_404()
        
        # Verifica se ci sono fatture associate
        invoices_count = Invoice.query.filter_by(category_id=category.id, is_active=True).count()
        if invoices_count > 0:
            return jsonify({
                'error': 'Impossibile eliminare la categoria',
                'message': f'La categoria è associata a {invoices_count} fatture attive',
                'invoices_count': invoices_count
            }), 409
        
        # Verifica se ci sono sottocategorie associate
        subcategories_count = len(category.subcategories) if category.subcategories else 0
        if subcategories_count > 0:
            return jsonify({
                'error': 'Impossibile eliminare la categoria',
                'message': f'La categoria ha {subcategories_count} sottocategorie associate',
                'subcategories_count': subcategories_count
            }), 409
        
        # Soft delete
        category.is_active = False
        db.session.commit()
        
        return jsonify({
            'message': 'Categoria eliminata con successo',
            'category_name': category.name,
            'category_code': category.code
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'Errore nell\'eliminazione della categoria',
            'message': str(e)
        }), 500


@api_v1_bp.route('/categories/check-duplicates', methods=['POST'])
@jwt_required()
def check_category_duplicates():
    """
    Controlla potenziali duplicati per una categoria.
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_manage_categories(current_user):
            return jsonify({
                'error': 'Accesso negato',
                'message': 'Permessi insufficienti'
            }), 403
        
        # Validazione dati
        data = category_duplicate_check_schema.load(request.get_json())
        
        duplicates = []
        
        # Controllo duplicato nome
        name_query = Category.query.filter(
            Category.name.ilike(f"%{data['name']}%"),
            Category.is_active == True
        )
        
        if data.get('exclude_id'):
            name_query = name_query.filter(Category.id != data['exclude_id'])
        
        name_duplicates = name_query.all()
        
        # Controllo duplicato codice se fornito
        code_duplicates = []
        if data.get('code'):
            code_query = Category.query.filter(
                Category.code == data['code'],
                Category.is_active == True
            )
            
            if data.get('exclude_id'):
                code_query = code_query.filter(Category.id != data['exclude_id'])
            
            code_duplicates = code_query.all()
        
        # Combina risultati
        all_duplicates = set(name_duplicates + code_duplicates)
        
        return jsonify({
            'potential_duplicates': len(all_duplicates),
            'duplicates': [
                {
                    'id': dup.id,
                    'name': dup.name,
                    'code': dup.code,
                    'description': dup.description,
                    'match_type': 'name' if dup in name_duplicates else 'code',
                    'subcategories_count': len(dup.subcategories) if dup.subcategories else 0
                } for dup in all_duplicates
            ],
            'search_criteria': data
        }), 200
        
    except ValidationError as e:
        return jsonify({
            'error': 'Dati non validi',
            'details': e.messages
        }), 400
    except Exception as e:
        return jsonify({
            'error': 'Errore nella ricerca duplicati',
            'message': str(e)
        }), 500


@api_v1_bp.route('/categories/bulk-action', methods=['POST'])
@jwt_required()
def categories_bulk_action():
    """
    Esegue azioni bulk su categorie (solo Rohirrim).
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_manage_categories(current_user):
            return jsonify({
                'error': 'Accesso negato',
                'message': 'Solo i Rohirrim possono eseguire azioni bulk'
            }), 403
        
        # Validazione dati
        data = category_bulk_action_schema.load(request.get_json())
        
        category_ids = data['category_ids']
        action = data['action']
        
        # Trova categorie
        categories = Category.query.filter(
            Category.id.in_(category_ids),
            Category.is_active == True
        ).all()
        
        if len(categories) != len(category_ids):
            found_ids = [c.id for c in categories]
            missing_ids = [cid for cid in category_ids if cid not in found_ids]
            return jsonify({
                'error': 'Alcune categorie non sono state trovate',
                'missing_ids': missing_ids
            }), 404
        
        # Esegui azione
        results = []
        
        if action == 'activate':
            for category in categories:
                category.is_active = True
                results.append({
                    'id': category.id,
                    'name': category.name,
                    'status': 'activated'
                })
        
        elif action == 'deactivate':
            for category in categories:
                category.is_active = False
                results.append({
                    'id': category.id,
                    'name': category.name,
                    'status': 'deactivated'
                })
        
        elif action == 'delete':
            # Controlla dipendenze per ogni categoria
            for category in categories:
                invoices_count = Invoice.query.filter_by(
                    category_id=category.id, 
                    is_active=True
                ).count()
                
                subcategories_count = len(category.subcategories) if category.subcategories else 0
                
                if invoices_count > 0 or subcategories_count > 0:
                    results.append({
                        'id': category.id,
                        'name': category.name,
                        'status': 'skipped',
                        'reason': f'Ha {invoices_count} fatture e {subcategories_count} sottocategorie'
                    })
                else:
                    category.is_active = False
                    results.append({
                        'id': category.id,
                        'name': category.name,
                        'status': 'deleted'
                    })
        
        db.session.commit()
        
        return jsonify({
            'message': f'Azione "{action}" eseguita su {len(category_ids)} categorie',
            'results': results,
            'action': action
        }), 200
        
    except ValidationError as e:
        return jsonify({
            'error': 'Dati non validi',
            'details': e.messages
        }), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'Errore nell\'esecuzione dell\'azione bulk',
            'message': str(e)
        }), 500


@api_v1_bp.route('/categories/stats', methods=['GET'])
@jwt_required()
def get_categories_stats():
    """
    Ottiene statistiche delle categorie.
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_view_categories(current_user):
            return jsonify({
                'error': 'Accesso negato',
                'message': 'Permessi insufficienti'
            }), 403
        
        # Statistiche base
        total_categories = Category.query.count()
        active_categories = Category.query.filter_by(is_active=True).count()
        
        # Categorie con sottocategorie
        categories_with_subcategories = Category.query.join(Subcategory).distinct().count()
        
        # Categorie con fatture
        categories_with_invoices = Category.query.join(Invoice).filter(
            Invoice.is_active == True
        ).distinct().count()
        
        # Categoria più utilizzata
        most_used_result = db.session.query(
            Category.name,
            func.count(Invoice.id).label('invoice_count')
        ).join(Invoice).filter(
            Invoice.is_active == True,
            Category.is_active == True
        ).group_by(Category.id, Category.name).order_by(
            func.count(Invoice.id).desc()
        ).first()
        
        most_used_category = most_used_result.name if most_used_result else None
        
        # Categoria meno utilizzata (tra quelle che hanno almeno una fattura)
        least_used_result = db.session.query(
            Category.name,
            func.count(Invoice.id).label('invoice_count')
        ).join(Invoice).filter(
            Invoice.is_active == True,
            Category.is_active == True
        ).group_by(Category.id, Category.name).order_by(
            func.count(Invoice.id).asc()
        ).first()
        
        least_used_category = least_used_result.name if least_used_result else None
        
        stats = {
            'total_categories': total_categories,
            'active_categories': active_categories,
            'categories_with_subcategories': categories_with_subcategories,
            'categories_with_invoices': categories_with_invoices,
            'most_used_category': most_used_category,
            'least_used_category': least_used_category,
            'user_permissions': {
                'can_manage': user_can_manage_categories(current_user)
            }
        }
        
        return jsonify(stats), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Errore nel recupero delle statistiche',
            'message': str(e)
        }), 500
