# Minicategories CRUD API - Sistema Completo

from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_current_user
from sqlalchemy import or_, func, and_
from sqlalchemy.exc import IntegrityError
from datetime import date, datetime, timedelta
from ...models.minicategory import Minicategory
from ...models.subcategory import Subcategory
from ...models.category import Category
from ...models.invoice import Invoice
from ...schemas import (
    minicategory_schema, minicategories_schema,
    minicategory_create_schema, minicategory_update_schema,
    minicategory_list_schema, minicategory_stats_schema,
    minicategory_duplicate_check_schema, minicategory_bulk_action_schema,
    minicategory_by_subcategory_schema
)
from ...extensions import db
from marshmallow import ValidationError
from . import api_v1_bp


def user_can_manage_minicategories(user):
    """Verifica se l'utente può gestire le minicategorie (solo Rohirrim)."""
    return user and user.is_active and user.role and user.role.is_rohirrim()


def user_can_view_minicategories(user):
    """Verifica se l'utente può visualizzare le minicategorie."""
    if not user or not user.is_active:
        return False
    
    # Rohirrim, Lord e Dunedain possono tutti visualizzare le minicategorie
    if user.role and (user.role.is_rohirrim() or user.role.is_lord() or user.role.is_dunedain()):
        return True
    
    return False


@api_v1_bp.route('/minicategories', methods=['GET'])
@jwt_required()
def get_minicategories():
    """
    Ottiene la lista delle minicategorie con filtri avanzati.
    Tutti i ruoli possono visualizzare le minicategorie.
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_view_minicategories(current_user):
            return jsonify({
                'error': 'Accesso negato',
                'message': 'Permessi insufficienti per visualizzare le minicategorie'
            }), 403
        
        # Validazione parametri query
        args = minicategory_list_schema.load(request.args)
        
        # Query base con join per ottimizzazione
        query = Minicategory.query.join(Subcategory).join(Category)
        
        # Filtro attività
        if args.get('is_active') is not None:
            query = query.filter(Minicategory.is_active == args['is_active'])
        else:
            # Default: solo minicategorie attive
            query = query.filter(Minicategory.is_active == True)
        
        # Applica filtri
        if args.get('search'):
            search_term = f"%{args['search']}%"
            query = query.filter(
                or_(
                    Minicategory.name.ilike(search_term),
                    Minicategory.description.ilike(search_term),
                    Minicategory.code.ilike(search_term),
                    Subcategory.name.ilike(search_term),
                    Category.name.ilike(search_term)
                )
            )
        
        # Filtro per sottocategoria specifica
        if args.get('subcategory_id'):
            query = query.filter(Minicategory.subcategory_id == args['subcategory_id'])
        
        # Filtro per categoria specifica
        if args.get('category_id'):
            query = query.filter(Subcategory.category_id == args['category_id'])
        
        # Filtro per minicategorie con fatture
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
        
        if hasattr(Minicategory, sort_by):
            order_column = getattr(Minicategory, sort_by)
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
        minicategories_data = minicategories_schema.dump(pagination.items)
        
        return jsonify({
            'minicategories': minicategories_data,
            'pagination': {
                'page': pagination.page,
                'pages': pagination.pages,
                'per_page': pagination.per_page,
                'total': pagination.total,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            },
            'user_permissions': {
                'can_edit': user_can_manage_minicategories(current_user),
                'can_delete': user_can_manage_minicategories(current_user),
                'can_create': user_can_manage_minicategories(current_user)
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


@api_v1_bp.route('/minicategories/<int:minicategory_id>', methods=['GET'])
@jwt_required()
def get_minicategory(minicategory_id):
    """
    Ottiene i dettagli di una minicategoria specifica.
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_view_minicategories(current_user):
            return jsonify({
                'error': 'Accesso negato',
                'message': 'Permessi insufficienti per visualizzare le minicategorie'
            }), 403
        
        minicategory = Minicategory.query.filter_by(id=minicategory_id, is_active=True).first_or_404()
        
        # Serializzazione completa con relazioni
        minicategory_data = minicategory_schema.dump(minicategory)
        
        # Aggiungi statistiche extra
        minicategory_data['invoices_count'] = Invoice.query.filter_by(
            minicategory_id=minicategory.id, 
            is_active=True
        ).count()
        
        return jsonify(minicategory_data), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Errore nel recupero della minicategoria',
            'message': str(e)
        }), 500


@api_v1_bp.route('/minicategories/by-subcategory', methods=['GET'])
@jwt_required()
def get_minicategories_by_subcategory():
    """
    Ottiene minicategorie per una sottocategoria specifica.
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_view_minicategories(current_user):
            return jsonify({
                'error': 'Accesso negato',
                'message': 'Permessi insufficienti'
            }), 403
        
        # Validazione parametri
        args = minicategory_by_subcategory_schema.load(request.args)
        
        # Verifica che la sottocategoria esista
        subcategory = Subcategory.query.filter_by(id=args['subcategory_id'], is_active=True).first_or_404()
        
        # Query minicategorie
        query = Minicategory.query.filter_by(subcategory_id=args['subcategory_id'])
        
        if not args.get('include_inactive'):
            query = query.filter_by(is_active=True)
        
        minicategories = query.order_by(Minicategory.name).all()
        
        return jsonify({
            'subcategory': {
                'id': subcategory.id,
                'name': subcategory.name,
                'category': {
                    'id': subcategory.category.id,
                    'name': subcategory.category.name
                } if subcategory.category else None
            },
            'minicategories': minicategories_schema.dump(minicategories),
            'total': len(minicategories)
        }), 200
        
    except ValidationError as e:
        return jsonify({
            'error': 'Parametri non validi',
            'details': e.messages
        }), 400
    except Exception as e:
        return jsonify({
            'error': 'Errore nel recupero delle minicategorie',
            'message': str(e)
        }), 500


@api_v1_bp.route('/minicategories', methods=['POST'])
@jwt_required()
def create_minicategory():
    """
    Crea una nuova minicategoria (solo Rohirrim).
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_manage_minicategories(current_user):
            return jsonify({
                'error': 'Accesso negato',
                'message': 'Solo i Rohirrim possono creare minicategorie'
            }), 403
        
        # Validazione dati
        data = minicategory_create_schema.load(request.get_json())
        
        # Verifica che la sottocategoria esista
        subcategory = Subcategory.query.filter_by(id=data['subcategory_id'], is_active=True).first()
        if not subcategory:
            return jsonify({
                'error': 'Sottocategoria non trovata',
                'message': f'La sottocategoria con ID {data["subcategory_id"]} non esiste o non è attiva'
            }), 404
        
        # Verifica unicità nome nella sottocategoria
        existing_name = Minicategory.query.filter_by(
            name=data['name'],
            subcategory_id=data['subcategory_id']
        ).first()
        if existing_name:
            return jsonify({
                'error': 'Nome minicategoria già esistente',
                'message': f'Una minicategoria con nome "{data["name"]}" esiste già in questa sottocategoria',
                'existing_minicategory_id': existing_name.id
            }), 409
        
        # Verifica unicità codice se fornito
        if data.get('code'):
            existing_code = Minicategory.query.filter_by(code=data['code']).first()
            if existing_code:
                return jsonify({
                    'error': 'Codice minicategoria già esistente',
                    'message': f'Una minicategoria con codice "{data["code"]}" esiste già',
                    'existing_minicategory_id': existing_code.id
                }), 409
        
        # Creazione minicategoria
        minicategory = Minicategory(**data)
        
        db.session.add(minicategory)
        db.session.commit()
        
        return jsonify({
            'message': 'Minicategoria creata con successo',
            'minicategory': minicategory_schema.dump(minicategory)
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
            'message': 'Nome o codice minicategoria già esistente'
        }), 409
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'Errore nella creazione della minicategoria',
            'message': str(e)
        }), 500


@api_v1_bp.route('/minicategories/<int:minicategory_id>', methods=['PUT'])
@jwt_required()
def update_minicategory(minicategory_id):
    """
    Aggiorna una minicategoria esistente (solo Rohirrim).
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_manage_minicategories(current_user):
            return jsonify({
                'error': 'Accesso negato',
                'message': 'Solo i Rohirrim possono modificare minicategorie'
            }), 403
        
        minicategory = Minicategory.query.filter_by(id=minicategory_id, is_active=True).first_or_404()
        
        # Validazione dati
        data = minicategory_update_schema.load(request.get_json())
        
        # Verifica sottocategoria se cambiata
        if 'subcategory_id' in data and data['subcategory_id'] != minicategory.subcategory_id:
            subcategory = Subcategory.query.filter_by(id=data['subcategory_id'], is_active=True).first()
            if not subcategory:
                return jsonify({
                    'error': 'Sottocategoria non trovata',
                    'message': f'La sottocategoria con ID {data["subcategory_id"]} non esiste o non è attiva'
                }), 404
        
        # Verifica unicità nome se cambiato
        if 'name' in data and data['name'] != minicategory.name:
            target_subcategory_id = data.get('subcategory_id', minicategory.subcategory_id)
            existing_name = Minicategory.query.filter_by(
                name=data['name'],
                subcategory_id=target_subcategory_id
            ).first()
            if existing_name:
                return jsonify({
                    'error': 'Nome minicategoria già esistente',
                    'message': f'Una minicategoria con nome "{data["name"]}" esiste già nella sottocategoria target'
                }), 409
        
        # Verifica unicità codice se cambiato
        if 'code' in data and data['code'] != minicategory.code:
            if data['code']:  # Solo se non è None/vuoto
                existing_code = Minicategory.query.filter_by(code=data['code']).first()
                if existing_code:
                    return jsonify({
                        'error': 'Codice minicategoria già esistente',
                        'message': f'Una minicategoria con codice "{data["code"]}" esiste già'
                    }), 409
        
        # Aggiornamento
        for key, value in data.items():
            if hasattr(minicategory, key):
                setattr(minicategory, key, value)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Minicategoria aggiornata con successo',
            'minicategory': minicategory_schema.dump(minicategory)
        }), 200
        
    except ValidationError as e:
        return jsonify({
            'error': 'Dati non validi',
            'details': e.messages
        }), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'Errore nell\'aggiornamento della minicategoria',
            'message': str(e)
        }), 500


@api_v1_bp.route('/minicategories/<int:minicategory_id>', methods=['DELETE'])
@jwt_required()
def delete_minicategory(minicategory_id):
    """
    Elimina una minicategoria (solo Rohirrim).
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_manage_minicategories(current_user):
            return jsonify({
                'error': 'Accesso negato',
                'message': 'Solo i Rohirrim possono eliminare minicategorie'
            }), 403
        
        minicategory = Minicategory.query.filter_by(id=minicategory_id, is_active=True).first_or_404()
        
        # Verifica se ci sono fatture associate
        invoices_count = Invoice.query.filter_by(minicategory_id=minicategory.id, is_active=True).count()
        if invoices_count > 0:
            return jsonify({
                'error': 'Impossibile eliminare la minicategoria',
                'message': f'La minicategoria è associata a {invoices_count} fatture attive',
                'invoices_count': invoices_count
            }), 409
        
        # Soft delete
        minicategory.is_active = False
        db.session.commit()
        
        return jsonify({
            'message': 'Minicategoria eliminata con successo',
            'minicategory_name': minicategory.name,
            'subcategory_name': minicategory.subcategory.name if minicategory.subcategory else None
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'Errore nell\'eliminazione della minicategoria',
            'message': str(e)
        }), 500


@api_v1_bp.route('/minicategories/check-duplicates', methods=['POST'])
@jwt_required()
def check_minicategory_duplicates():
    """
    Controlla potenziali duplicati per una minicategoria.
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_manage_minicategories(current_user):
            return jsonify({
                'error': 'Accesso negato',
                'message': 'Permessi insufficienti'
            }), 403
        
        # Validazione dati
        data = minicategory_duplicate_check_schema.load(request.get_json())
        
        duplicates = []
        
        # Controllo duplicato nome nella stessa sottocategoria
        name_query = Minicategory.query.filter(
            Minicategory.name.ilike(f"%{data['name']}%"),
            Minicategory.subcategory_id == data['subcategory_id'],
            Minicategory.is_active == True
        )
        
        if data.get('exclude_id'):
            name_query = name_query.filter(Minicategory.id != data['exclude_id'])
        
        name_duplicates = name_query.all()
        
        # Controllo duplicato codice globale se fornito
        code_duplicates = []
        if data.get('code'):
            code_query = Minicategory.query.filter(
                Minicategory.code == data['code'],
                Minicategory.is_active == True
            )
            
            if data.get('exclude_id'):
                code_query = code_query.filter(Minicategory.id != data['exclude_id'])
            
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
                    'subcategory': {
                        'id': dup.subcategory.id,
                        'name': dup.subcategory.name
                    } if dup.subcategory else None,
                    'match_type': 'name' if dup in name_duplicates else 'code'
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


@api_v1_bp.route('/minicategories/bulk-action', methods=['POST'])
@jwt_required()
def minicategories_bulk_action():
    """
    Esegue azioni bulk su minicategorie (solo Rohirrim).
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_manage_minicategories(current_user):
            return jsonify({
                'error': 'Accesso negato',
                'message': 'Solo i Rohirrim possono eseguire azioni bulk'
            }), 403
        
        # Validazione dati
        data = minicategory_bulk_action_schema.load(request.get_json())
        
        minicategory_ids = data['minicategory_ids']
        action = data['action']
        
        # Trova minicategorie
        minicategories = Minicategory.query.filter(
            Minicategory.id.in_(minicategory_ids),
            Minicategory.is_active == True
        ).all()
        
        if len(minicategories) != len(minicategory_ids):
            found_ids = [m.id for m in minicategories]
            missing_ids = [mid for mid in minicategory_ids if mid not in found_ids]
            return jsonify({
                'error': 'Alcune minicategorie non sono state trovate',
                'missing_ids': missing_ids
            }), 404
        
        # Esegui azione
        results = []
        
        if action == 'activate':
            for minicategory in minicategories:
                minicategory.is_active = True
                results.append({
                    'id': minicategory.id,
                    'name': minicategory.name,
                    'status': 'activated'
                })
        
        elif action == 'deactivate':
            for minicategory in minicategories:
                minicategory.is_active = False
                results.append({
                    'id': minicategory.id,
                    'name': minicategory.name,
                    'status': 'deactivated'
                })
        
        elif action == 'delete':
            # Controlla dipendenze per ogni minicategoria
            for minicategory in minicategories:
                invoices_count = Invoice.query.filter_by(
                    minicategory_id=minicategory.id, 
                    is_active=True
                ).count()
                
                if invoices_count > 0:
                    results.append({
                        'id': minicategory.id,
                        'name': minicategory.name,
                        'status': 'skipped',
                        'reason': f'Ha {invoices_count} fatture associate'
                    })
                else:
                    minicategory.is_active = False
                    results.append({
                        'id': minicategory.id,
                        'name': minicategory.name,
                        'status': 'deleted'
                    })
        
        elif action == 'move_to_subcategory':
            target_subcategory_id = data['target_subcategory_id']
            
            # Verifica che la sottocategoria target esista
            target_subcategory = Subcategory.query.filter_by(id=target_subcategory_id, is_active=True).first()
            if not target_subcategory:
                return jsonify({
                    'error': 'Sottocategoria target non trovata',
                    'message': f'La sottocategoria con ID {target_subcategory_id} non esiste o non è attiva'
                }), 404
            
            for minicategory in minicategories:
                # Controlla conflitti nome nella sottocategoria target
                existing = Minicategory.query.filter_by(
                    name=minicategory.name,
                    subcategory_id=target_subcategory_id,
                    is_active=True
                ).first()
                
                if existing and existing.id != minicategory.id:
                    results.append({
                        'id': minicategory.id,
                        'name': minicategory.name,
                        'status': 'skipped',
                        'reason': 'Nome già esistente nella sottocategoria target'
                    })
                else:
                    minicategory.subcategory_id = target_subcategory_id
                    results.append({
                        'id': minicategory.id,
                        'name': minicategory.name,
                        'status': 'moved',
                        'target_subcategory': target_subcategory.name
                    })
        
        db.session.commit()
        
        return jsonify({
            'message': f'Azione "{action}" eseguita su {len(minicategory_ids)} minicategorie',
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


@api_v1_bp.route('/minicategories/stats', methods=['GET'])
@jwt_required()
def get_minicategories_stats():
    """
    Ottiene statistiche delle minicategorie.
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_view_minicategories(current_user):
            return jsonify({
                'error': 'Accesso negato',
                'message': 'Permessi insufficienti'
            }), 403
        
        # Statistiche base
        total_minicategories = Minicategory.query.count()
        active_minicategories = Minicategory.query.filter_by(is_active=True).count()
        
        # Minicategorie con fatture
        minicategories_with_invoices = Minicategory.query.join(Invoice).filter(
            Invoice.is_active == True
        ).distinct().count()
        
        # Minicategoria più utilizzata
        most_used_result = db.session.query(
            Minicategory.name,
            func.count(Invoice.id).label('invoice_count')
        ).join(Invoice).filter(
            Invoice.is_active == True,
            Minicategory.is_active == True
        ).group_by(Minicategory.id, Minicategory.name).order_by(
            func.count(Invoice.id).desc()
        ).first()
        
        most_used_minicategory = most_used_result.name if most_used_result else None
        
        # Minicategoria meno utilizzata (tra quelle che hanno almeno una fattura)
        least_used_result = db.session.query(
            Minicategory.name,
            func.count(Invoice.id).label('invoice_count')
        ).join(Invoice).filter(
            Invoice.is_active == True,
            Minicategory.is_active == True
        ).group_by(Minicategory.id, Minicategory.name).order_by(
            func.count(Invoice.id).asc()
        ).first()
        
        least_used_minicategory = least_used_result.name if least_used_result else None
        
        # Statistiche per sottocategoria
        by_subcategory = db.session.query(
            Subcategory.name.label('subcategory_name'),
            func.count(Minicategory.id).label('minicategories_count')
        ).join(Minicategory).filter(
            Minicategory.is_active == True,
            Subcategory.is_active == True
        ).group_by(Subcategory.id, Subcategory.name).all()
        
        # Statistiche per categoria
        by_category = db.session.query(
            Category.name.label('category_name'),
            func.count(Minicategory.id).label('minicategories_count')
        ).join(Subcategory).join(Minicategory).filter(
            Minicategory.is_active == True,
            Subcategory.is_active == True,
            Category.is_active == True
        ).group_by(Category.id, Category.name).all()
        
        stats = {
            'total_minicategories': total_minicategories,
            'active_minicategories': active_minicategories,
            'minicategories_with_invoices': minicategories_with_invoices,
            'most_used_minicategory': most_used_minicategory,
            'least_used_minicategory': least_used_minicategory,
            'by_subcategory': [
                {
                    'subcategory_name': row.subcategory_name,
                    'minicategories_count': row.minicategories_count
                } for row in by_subcategory
            ],
            'by_category': [
                {
                    'category_name': row.category_name,
                    'minicategories_count': row.minicategories_count
                } for row in by_category
            ],
            'user_permissions': {
                'can_manage': user_can_manage_minicategories(current_user)
            }
        }
        
        return jsonify(stats), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Errore nel recupero delle statistiche',
            'message': str(e)
        }), 500
