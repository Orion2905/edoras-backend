# Subcategories CRUD API - Sistema Completo

from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_current_user
from sqlalchemy import or_, func, and_
from sqlalchemy.exc import IntegrityError
from datetime import date, datetime, timedelta
from ...models.subcategory import Subcategory
from ...models.category import Category
from ...models.minicategory import Minicategory
from ...models.invoice import Invoice
from ...schemas import (
    subcategory_schema, subcategories_schema,
    subcategory_create_schema, subcategory_update_schema,
    subcategory_list_schema, subcategory_stats_schema,
    subcategory_duplicate_check_schema, subcategory_bulk_action_schema,
    subcategory_by_category_schema, subcategory_hierarchy_schema
)
from ...extensions import db
from marshmallow import ValidationError
from . import api_v1_bp


def user_can_manage_subcategories(user):
    """Verifica se l'utente può gestire le sottocategorie (solo Rohirrim)."""
    return user and user.is_active and user.role and user.role.is_rohirrim()


def user_can_view_subcategories(user):
    """Verifica se l'utente può visualizzare le sottocategorie."""
    if not user or not user.is_active:
        return False
    
    # Rohirrim, Lord e Dunedain possono tutti visualizzare le sottocategorie
    if user.role and (user.role.is_rohirrim() or user.role.is_lord() or user.role.is_dunedain()):
        return True
    
    return False


@api_v1_bp.route('/subcategories', methods=['GET'])
@jwt_required()
def get_subcategories():
    """
    Ottiene la lista delle sottocategorie con filtri avanzati.
    Tutti i ruoli possono visualizzare le sottocategorie.
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_view_subcategories(current_user):
            return jsonify({
                'error': 'Accesso negato',
                'message': 'Permessi insufficienti per visualizzare le sottocategorie'
            }), 403
        
        # Validazione parametri query
        args = subcategory_list_schema.load(request.args)
        
        # Query base con join per ottimizzazione
        query = Subcategory.query.join(Category)
        
        # Filtro attività
        if args.get('is_active') is not None:
            query = query.filter(Subcategory.is_active == args['is_active'])
        else:
            # Default: solo sottocategorie attive
            query = query.filter(Subcategory.is_active == True)
        
        # Applica filtri
        if args.get('search'):
            search_term = f"%{args['search']}%"
            query = query.filter(
                or_(
                    Subcategory.name.ilike(search_term),
                    Subcategory.description.ilike(search_term),
                    Subcategory.code.ilike(search_term),
                    Category.name.ilike(search_term)
                )
            )
        
        # Filtro per categoria specifica
        if args.get('category_id'):
            query = query.filter(Subcategory.category_id == args['category_id'])
        
        # Filtro per sottocategorie con minicategorie
        if args.get('has_minicategories') is not None:
            if args['has_minicategories']:
                query = query.join(Minicategory).filter(Minicategory.is_active == True).distinct()
            else:
                query = query.outerjoin(Minicategory).filter(
                    or_(Minicategory.id == None, Minicategory.is_active == False)
                )
        
        # Filtro per sottocategorie con fatture
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
        
        if hasattr(Subcategory, sort_by):
            order_column = getattr(Subcategory, sort_by)
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
        subcategories_data = subcategories_schema.dump(pagination.items)
        
        return jsonify({
            'subcategories': subcategories_data,
            'pagination': {
                'page': pagination.page,
                'pages': pagination.pages,
                'per_page': pagination.per_page,
                'total': pagination.total,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            },
            'user_permissions': {
                'can_edit': user_can_manage_subcategories(current_user),
                'can_delete': user_can_manage_subcategories(current_user),
                'can_create': user_can_manage_subcategories(current_user)
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


@api_v1_bp.route('/subcategories/<int:subcategory_id>', methods=['GET'])
@jwt_required()
def get_subcategory(subcategory_id):
    """
    Ottiene i dettagli di una sottocategoria specifica.
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_view_subcategories(current_user):
            return jsonify({
                'error': 'Accesso negato',
                'message': 'Permessi insufficienti per visualizzare le sottocategorie'
            }), 403
        
        subcategory = Subcategory.query.filter_by(id=subcategory_id, is_active=True).first_or_404()
        
        # Serializzazione completa con relazioni
        subcategory_data = subcategory_schema.dump(subcategory)
        
        # Aggiungi statistiche extra
        subcategory_data['invoices_count'] = Invoice.query.filter_by(
            subcategory_id=subcategory.id, 
            is_active=True
        ).count()
        
        subcategory_data['minicategories_count'] = Minicategory.query.filter_by(
            subcategory_id=subcategory.id,
            is_active=True
        ).count()
        
        return jsonify(subcategory_data), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Errore nel recupero della sottocategoria',
            'message': str(e)
        }), 500


@api_v1_bp.route('/subcategories/by-category', methods=['GET'])
@jwt_required()
def get_subcategories_by_category():
    """
    Ottiene sottocategorie per una categoria specifica.
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_view_subcategories(current_user):
            return jsonify({
                'error': 'Accesso negato',
                'message': 'Permessi insufficienti'
            }), 403
        
        # Validazione parametri
        args = subcategory_by_category_schema.load(request.args)
        
        # Verifica che la categoria esista
        category = Category.query.filter_by(id=args['category_id'], is_active=True).first_or_404()
        
        # Query sottocategorie
        query = Subcategory.query.filter_by(category_id=args['category_id'])
        
        if not args.get('include_inactive'):
            query = query.filter_by(is_active=True)
        
        subcategories = query.order_by(Subcategory.name).all()
        
        return jsonify({
            'category': {
                'id': category.id,
                'name': category.name,
                'code': category.code
            },
            'subcategories': subcategories_schema.dump(subcategories),
            'total': len(subcategories)
        }), 200
        
    except ValidationError as e:
        return jsonify({
            'error': 'Parametri non validi',
            'details': e.messages
        }), 400
    except Exception as e:
        return jsonify({
            'error': 'Errore nel recupero delle sottocategorie',
            'message': str(e)
        }), 500


@api_v1_bp.route('/subcategories/hierarchy', methods=['GET'])
@jwt_required()
def get_subcategories_hierarchy():
    """
    Ottiene la gerarchia completa categorie -> sottocategorie -> minicategorie.
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_view_subcategories(current_user):
            return jsonify({
                'error': 'Accesso negato',
                'message': 'Permessi insufficienti'
            }), 403
        
        # Validazione parametri
        args = subcategory_hierarchy_schema.load(request.args)
        
        # Query base categorie
        categories_query = Category.query
        if not args.get('include_inactive'):
            categories_query = categories_query.filter_by(is_active=True)
        
        # Filtro categoria specifica se richiesto
        if args.get('category_id'):
            categories_query = categories_query.filter_by(id=args['category_id'])
        
        categories = categories_query.order_by(Category.name).all()
        
        hierarchy = []
        for category in categories:
            # Query sottocategorie per questa categoria
            subcategories_query = Subcategory.query.filter_by(category_id=category.id)
            if not args.get('include_inactive'):
                subcategories_query = subcategories_query.filter_by(is_active=True)
            
            subcategories = subcategories_query.order_by(Subcategory.name).all()
            
            category_data = {
                'id': category.id,
                'name': category.name,
                'code': category.code,
                'description': category.description,
                'is_active': category.is_active,
                'subcategories': []
            }
            
            for subcategory in subcategories:
                subcategory_data = {
                    'id': subcategory.id,
                    'name': subcategory.name,
                    'code': subcategory.code,
                    'description': subcategory.description,
                    'is_active': subcategory.is_active
                }
                
                # Aggiungi conteggi se richiesto
                if args.get('include_counts'):
                    subcategory_data['minicategories_count'] = Minicategory.query.filter_by(
                        subcategory_id=subcategory.id,
                        is_active=True
                    ).count()
                    subcategory_data['invoices_count'] = Invoice.query.filter_by(
                        subcategory_id=subcategory.id,
                        is_active=True
                    ).count()
                
                # Aggiungi minicategorie se richiesto
                if args.get('include_minicategories'):
                    minicategories_query = Minicategory.query.filter_by(subcategory_id=subcategory.id)
                    if not args.get('include_inactive'):
                        minicategories_query = minicategories_query.filter_by(is_active=True)
                    
                    minicategories = minicategories_query.order_by(Minicategory.name).all()
                    subcategory_data['minicategories'] = [
                        {
                            'id': mini.id,
                            'name': mini.name,
                            'code': mini.code,
                            'description': mini.description,
                            'is_active': mini.is_active
                        } for mini in minicategories
                    ]
                
                category_data['subcategories'].append(subcategory_data)
            
            # Aggiungi conteggi categoria se richiesto
            if args.get('include_counts'):
                category_data['subcategories_count'] = len(category_data['subcategories'])
                category_data['total_minicategories'] = sum(
                    sub.get('minicategories_count', 0) for sub in category_data['subcategories']
                )
            
            hierarchy.append(category_data)
        
        return jsonify({
            'hierarchy': hierarchy,
            'total_categories': len(hierarchy),
            'filters_applied': {
                'category_id': args.get('category_id'),
                'include_inactive': args.get('include_inactive'),
                'include_minicategories': args.get('include_minicategories'),
                'include_counts': args.get('include_counts')
            }
        }), 200
        
    except ValidationError as e:
        return jsonify({
            'error': 'Parametri non validi',
            'details': e.messages
        }), 400
    except Exception as e:
        return jsonify({
            'error': 'Errore nel recupero della gerarchia',
            'message': str(e)
        }), 500


@api_v1_bp.route('/subcategories', methods=['POST'])
@jwt_required()
def create_subcategory():
    """
    Crea una nuova sottocategoria (solo Rohirrim).
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_manage_subcategories(current_user):
            return jsonify({
                'error': 'Accesso negato',
                'message': 'Solo i Rohirrim possono creare sottocategorie'
            }), 403
        
        # Validazione dati
        data = subcategory_create_schema.load(request.get_json())
        
        # Verifica che la categoria esista
        category = Category.query.filter_by(id=data['category_id'], is_active=True).first()
        if not category:
            return jsonify({
                'error': 'Categoria non trovata',
                'message': f'La categoria con ID {data["category_id"]} non esiste o non è attiva'
            }), 404
        
        # Verifica unicità nome nella categoria
        existing_name = Subcategory.query.filter_by(
            name=data['name'],
            category_id=data['category_id']
        ).first()
        if existing_name:
            return jsonify({
                'error': 'Nome sottocategoria già esistente',
                'message': f'Una sottocategoria con nome "{data["name"]}" esiste già in questa categoria',
                'existing_subcategory_id': existing_name.id
            }), 409
        
        # Verifica unicità codice se fornito
        if data.get('code'):
            existing_code = Subcategory.query.filter_by(code=data['code']).first()
            if existing_code:
                return jsonify({
                    'error': 'Codice sottocategoria già esistente',
                    'message': f'Una sottocategoria con codice "{data["code"]}" esiste già',
                    'existing_subcategory_id': existing_code.id
                }), 409
        
        # Creazione sottocategoria
        subcategory = Subcategory(**data)
        
        db.session.add(subcategory)
        db.session.commit()
        
        return jsonify({
            'message': 'Sottocategoria creata con successo',
            'subcategory': subcategory_schema.dump(subcategory)
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
            'message': 'Nome o codice sottocategoria già esistente'
        }), 409
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'Errore nella creazione della sottocategoria',
            'message': str(e)
        }), 500


@api_v1_bp.route('/subcategories/<int:subcategory_id>', methods=['PUT'])
@jwt_required()
def update_subcategory(subcategory_id):
    """
    Aggiorna una sottocategoria esistente (solo Rohirrim).
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_manage_subcategories(current_user):
            return jsonify({
                'error': 'Accesso negato',
                'message': 'Solo i Rohirrim possono modificare sottocategorie'
            }), 403
        
        subcategory = Subcategory.query.filter_by(id=subcategory_id, is_active=True).first_or_404()
        
        # Validazione dati
        data = subcategory_update_schema.load(request.get_json())
        
        # Verifica categoria se cambiata
        if 'category_id' in data and data['category_id'] != subcategory.category_id:
            category = Category.query.filter_by(id=data['category_id'], is_active=True).first()
            if not category:
                return jsonify({
                    'error': 'Categoria non trovata',
                    'message': f'La categoria con ID {data["category_id"]} non esiste o non è attiva'
                }), 404
        
        # Verifica unicità nome se cambiato
        if 'name' in data and data['name'] != subcategory.name:
            target_category_id = data.get('category_id', subcategory.category_id)
            existing_name = Subcategory.query.filter_by(
                name=data['name'],
                category_id=target_category_id
            ).first()
            if existing_name:
                return jsonify({
                    'error': 'Nome sottocategoria già esistente',
                    'message': f'Una sottocategoria con nome "{data["name"]}" esiste già nella categoria target'
                }), 409
        
        # Verifica unicità codice se cambiato
        if 'code' in data and data['code'] != subcategory.code:
            if data['code']:  # Solo se non è None/vuoto
                existing_code = Subcategory.query.filter_by(code=data['code']).first()
                if existing_code:
                    return jsonify({
                        'error': 'Codice sottocategoria già esistente',
                        'message': f'Una sottocategoria con codice "{data["code"]}" esiste già'
                    }), 409
        
        # Aggiornamento
        for key, value in data.items():
            if hasattr(subcategory, key):
                setattr(subcategory, key, value)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Sottocategoria aggiornata con successo',
            'subcategory': subcategory_schema.dump(subcategory)
        }), 200
        
    except ValidationError as e:
        return jsonify({
            'error': 'Dati non validi',
            'details': e.messages
        }), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'Errore nell\'aggiornamento della sottocategoria',
            'message': str(e)
        }), 500


@api_v1_bp.route('/subcategories/<int:subcategory_id>', methods=['DELETE'])
@jwt_required()
def delete_subcategory(subcategory_id):
    """
    Elimina una sottocategoria (solo Rohirrim).
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_manage_subcategories(current_user):
            return jsonify({
                'error': 'Accesso negato',
                'message': 'Solo i Rohirrim possono eliminare sottocategorie'
            }), 403
        
        subcategory = Subcategory.query.filter_by(id=subcategory_id, is_active=True).first_or_404()
        
        # Verifica se ci sono fatture associate
        invoices_count = Invoice.query.filter_by(subcategory_id=subcategory.id, is_active=True).count()
        if invoices_count > 0:
            return jsonify({
                'error': 'Impossibile eliminare la sottocategoria',
                'message': f'La sottocategoria è associata a {invoices_count} fatture attive',
                'invoices_count': invoices_count
            }), 409
        
        # Verifica se ci sono minicategorie associate
        minicategories_count = Minicategory.query.filter_by(subcategory_id=subcategory.id, is_active=True).count()
        if minicategories_count > 0:
            return jsonify({
                'error': 'Impossibile eliminare la sottocategoria',
                'message': f'La sottocategoria ha {minicategories_count} minicategorie associate',
                'minicategories_count': minicategories_count
            }), 409
        
        # Soft delete
        subcategory.is_active = False
        db.session.commit()
        
        return jsonify({
            'message': 'Sottocategoria eliminata con successo',
            'subcategory_name': subcategory.name,
            'category_name': subcategory.category.name if subcategory.category else None
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'Errore nell\'eliminazione della sottocategoria',
            'message': str(e)
        }), 500


@api_v1_bp.route('/subcategories/check-duplicates', methods=['POST'])
@jwt_required()
def check_subcategory_duplicates():
    """
    Controlla potenziali duplicati per una sottocategoria.
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_manage_subcategories(current_user):
            return jsonify({
                'error': 'Accesso negato',
                'message': 'Permessi insufficienti'
            }), 403
        
        # Validazione dati
        data = subcategory_duplicate_check_schema.load(request.get_json())
        
        duplicates = []
        
        # Controllo duplicato nome nella stessa categoria
        name_query = Subcategory.query.filter(
            Subcategory.name.ilike(f"%{data['name']}%"),
            Subcategory.category_id == data['category_id'],
            Subcategory.is_active == True
        )
        
        if data.get('exclude_id'):
            name_query = name_query.filter(Subcategory.id != data['exclude_id'])
        
        name_duplicates = name_query.all()
        
        # Controllo duplicato codice globale se fornito
        code_duplicates = []
        if data.get('code'):
            code_query = Subcategory.query.filter(
                Subcategory.code == data['code'],
                Subcategory.is_active == True
            )
            
            if data.get('exclude_id'):
                code_query = code_query.filter(Subcategory.id != data['exclude_id'])
            
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
                    'category': {
                        'id': dup.category.id,
                        'name': dup.category.name
                    } if dup.category else None,
                    'match_type': 'name' if dup in name_duplicates else 'code',
                    'minicategories_count': len(dup.minicategories) if dup.minicategories else 0
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


@api_v1_bp.route('/subcategories/bulk-action', methods=['POST'])
@jwt_required()
def subcategories_bulk_action():
    """
    Esegue azioni bulk su sottocategorie (solo Rohirrim).
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_manage_subcategories(current_user):
            return jsonify({
                'error': 'Accesso negato',
                'message': 'Solo i Rohirrim possono eseguire azioni bulk'
            }), 403
        
        # Validazione dati
        data = subcategory_bulk_action_schema.load(request.get_json())
        
        subcategory_ids = data['subcategory_ids']
        action = data['action']
        
        # Trova sottocategorie
        subcategories = Subcategory.query.filter(
            Subcategory.id.in_(subcategory_ids),
            Subcategory.is_active == True
        ).all()
        
        if len(subcategories) != len(subcategory_ids):
            found_ids = [s.id for s in subcategories]
            missing_ids = [sid for sid in subcategory_ids if sid not in found_ids]
            return jsonify({
                'error': 'Alcune sottocategorie non sono state trovate',
                'missing_ids': missing_ids
            }), 404
        
        # Esegui azione
        results = []
        
        if action == 'activate':
            for subcategory in subcategories:
                subcategory.is_active = True
                results.append({
                    'id': subcategory.id,
                    'name': subcategory.name,
                    'status': 'activated'
                })
        
        elif action == 'deactivate':
            for subcategory in subcategories:
                subcategory.is_active = False
                results.append({
                    'id': subcategory.id,
                    'name': subcategory.name,
                    'status': 'deactivated'
                })
        
        elif action == 'delete':
            # Controlla dipendenze per ogni sottocategoria
            for subcategory in subcategories:
                invoices_count = Invoice.query.filter_by(
                    subcategory_id=subcategory.id, 
                    is_active=True
                ).count()
                
                minicategories_count = Minicategory.query.filter_by(
                    subcategory_id=subcategory.id,
                    is_active=True
                ).count()
                
                if invoices_count > 0 or minicategories_count > 0:
                    results.append({
                        'id': subcategory.id,
                        'name': subcategory.name,
                        'status': 'skipped',
                        'reason': f'Ha {invoices_count} fatture e {minicategories_count} minicategorie'
                    })
                else:
                    subcategory.is_active = False
                    results.append({
                        'id': subcategory.id,
                        'name': subcategory.name,
                        'status': 'deleted'
                    })
        
        elif action == 'move_to_category':
            target_category_id = data['target_category_id']
            
            # Verifica che la categoria target esista
            target_category = Category.query.filter_by(id=target_category_id, is_active=True).first()
            if not target_category:
                return jsonify({
                    'error': 'Categoria target non trovata',
                    'message': f'La categoria con ID {target_category_id} non esiste o non è attiva'
                }), 404
            
            for subcategory in subcategories:
                # Controlla conflitti nome nella categoria target
                existing = Subcategory.query.filter_by(
                    name=subcategory.name,
                    category_id=target_category_id,
                    is_active=True
                ).first()
                
                if existing and existing.id != subcategory.id:
                    results.append({
                        'id': subcategory.id,
                        'name': subcategory.name,
                        'status': 'skipped',
                        'reason': 'Nome già esistente nella categoria target'
                    })
                else:
                    subcategory.category_id = target_category_id
                    results.append({
                        'id': subcategory.id,
                        'name': subcategory.name,
                        'status': 'moved',
                        'target_category': target_category.name
                    })
        
        db.session.commit()
        
        return jsonify({
            'message': f'Azione "{action}" eseguita su {len(subcategory_ids)} sottocategorie',
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


@api_v1_bp.route('/subcategories/stats', methods=['GET'])
@jwt_required()
def get_subcategories_stats():
    """
    Ottiene statistiche delle sottocategorie.
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_view_subcategories(current_user):
            return jsonify({
                'error': 'Accesso negato',
                'message': 'Permessi insufficienti'
            }), 403
        
        # Statistiche base
        total_subcategories = Subcategory.query.count()
        active_subcategories = Subcategory.query.filter_by(is_active=True).count()
        
        # Sottocategorie con minicategorie
        subcategories_with_minicategories = Subcategory.query.join(Minicategory).filter(
            Minicategory.is_active == True
        ).distinct().count()
        
        # Sottocategorie con fatture
        subcategories_with_invoices = Subcategory.query.join(Invoice).filter(
            Invoice.is_active == True
        ).distinct().count()
        
        # Sottocategoria più utilizzata
        most_used_result = db.session.query(
            Subcategory.name,
            func.count(Invoice.id).label('invoice_count')
        ).join(Invoice).filter(
            Invoice.is_active == True,
            Subcategory.is_active == True
        ).group_by(Subcategory.id, Subcategory.name).order_by(
            func.count(Invoice.id).desc()
        ).first()
        
        most_used_subcategory = most_used_result.name if most_used_result else None
        
        # Sottocategoria meno utilizzata (tra quelle che hanno almeno una fattura)
        least_used_result = db.session.query(
            Subcategory.name,
            func.count(Invoice.id).label('invoice_count')
        ).join(Invoice).filter(
            Invoice.is_active == True,
            Subcategory.is_active == True
        ).group_by(Subcategory.id, Subcategory.name).order_by(
            func.count(Invoice.id).asc()
        ).first()
        
        least_used_subcategory = least_used_result.name if least_used_result else None
        
        # Statistiche per categoria
        by_category = db.session.query(
            Category.name.label('category_name'),
            func.count(Subcategory.id).label('subcategories_count')
        ).join(Subcategory).filter(
            Subcategory.is_active == True,
            Category.is_active == True
        ).group_by(Category.id, Category.name).all()
        
        # Media minicategorie per sottocategoria
        avg_minicategories = db.session.query(
            func.avg(func.count(Minicategory.id))
        ).join(Subcategory).filter(
            Minicategory.is_active == True,
            Subcategory.is_active == True
        ).group_by(Subcategory.id).scalar() or 0.0
        
        stats = {
            'total_subcategories': total_subcategories,
            'active_subcategories': active_subcategories,
            'subcategories_with_minicategories': subcategories_with_minicategories,
            'subcategories_with_invoices': subcategories_with_invoices,
            'most_used_subcategory': most_used_subcategory,
            'least_used_subcategory': least_used_subcategory,
            'average_minicategories_per_subcategory': float(avg_minicategories),
            'by_category': [
                {
                    'category_name': row.category_name,
                    'subcategories_count': row.subcategories_count
                } for row in by_category
            ],
            'user_permissions': {
                'can_manage': user_can_manage_subcategories(current_user)
            }
        }
        
        return jsonify(stats), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Errore nel recupero delle statistiche',
            'message': str(e)
        }), 500
