# Permissions CRUD API - Solo per Sviluppatori (Rohirrim)

from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_current_user
from sqlalchemy import or_, func, and_
from sqlalchemy.exc import IntegrityError
from ...models.permission import Permission
from ...models.role import Role
from ...schemas import (
    permission_schema, permissions_schema,
    permission_create_schema, permission_update_schema,
    permission_list_schema, permission_bulk_create_schema,
    permission_bulk_update_schema, permission_stats_schema,
    permission_import_schema
)
from ...extensions import db
from marshmallow import ValidationError
from . import api_v1_bp


def developer_required():
    """Decorator per verificare che l'utente sia un Rohirrim (developer)."""
    current_user = get_current_user()
    if not current_user:
        return False
    
    return current_user.role and current_user.role.is_rohirrim()


def require_developer_access():
    """Helper per verificare accesso sviluppatore."""
    if not developer_required():
        return jsonify({
            'error': 'Accesso negato',
            'message': 'Solo i Rohirrim (sviluppatori) possono accedere a questa funzionalità',
            'code': 'DEVELOPER_ACCESS_REQUIRED'
        }), 403
    return None


@api_v1_bp.route('/permissions', methods=['GET'])
@jwt_required()
def get_permissions():
    """
    Ottiene la lista di tutti i permessi con filtri avanzati.
    Solo per sviluppatori (Rohirrim).
    """
    # Verifica accesso sviluppatore
    access_error = require_developer_access()
    if access_error:
        return access_error
    
    try:
        # Validazione parametri query
        args = permission_list_schema.load(request.args)
        
        # Query base con join per ottimizzazione
        query = Permission.query.join(Role, Permission.role_id == Role.id)
        
        # Filtri
        if args.get('search'):
            search_term = f"%{args['search']}%"
            query = query.filter(
                or_(
                    Permission.name.ilike(search_term),
                    Permission.display_name.ilike(search_term),
                    Permission.description.ilike(search_term),
                    Role.name.ilike(search_term),
                    Role.display_name.ilike(search_term)
                )
            )
        
        if args.get('category'):
            query = query.filter(Permission.category == args['category'])
        
        if args.get('role_id'):
            query = query.filter(Permission.role_id == args['role_id'])
        
        if args.get('is_active') is not None:
            query = query.filter(Permission.is_active == args['is_active'])
        
        # Ordinamento
        query = query.order_by(
            Permission.category.asc(),
            Role.access_level.asc(),
            Permission.name.asc()
        )
        
        # Paginazione
        page = args.get('page', 1)
        per_page = args.get('per_page', 20)
        pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        # Serializzazione
        if args.get('include_role_info'):
            permissions_data = []
            for permission in pagination.items:
                perm_data = permission_schema.dump(permission)
                perm_data['role_info'] = {
                    'id': permission.role.id,
                    'name': permission.role.name,
                    'display_name': permission.role.display_name,
                    'access_level': permission.role.access_level
                }
                permissions_data.append(perm_data)
        else:
            permissions_data = permissions_schema.dump(pagination.items)
        
        return jsonify({
            'permissions': permissions_data,
            'pagination': {
                'page': pagination.page,
                'pages': pagination.pages,
                'per_page': pagination.per_page,
                'total': pagination.total,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            },
            'filters_applied': {
                'search': args.get('search'),
                'category': args.get('category'),
                'role_id': args.get('role_id'),
                'is_active': args.get('is_active'),
                'include_role_info': args.get('include_role_info')
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


@api_v1_bp.route('/permissions/<int:permission_id>', methods=['GET'])
@jwt_required()
def get_permission(permission_id):
    """
    Ottiene i dettagli di un permesso specifico.
    Solo per sviluppatori (Rohirrim).
    """
    # Verifica accesso sviluppatore
    access_error = require_developer_access()
    if access_error:
        return access_error
    
    try:
        permission = Permission.query.get_or_404(permission_id)
        
        # Serializzazione completa con informazioni ruolo
        permission_data = permission_schema.dump(permission)
        permission_data.update({
            'role_info': {
                'id': permission.role.id,
                'name': permission.role.name,
                'display_name': permission.role.display_name,
                'access_level': permission.role.access_level,
                'is_system_role': permission.role.name in ['rohirrim', 'lord', 'dunedain']
            },
            'usage_stats': {
                'created_days_ago': (func.current_date() - func.date(permission.created_at)).label('days'),
                'last_updated_days_ago': (func.current_date() - func.date(permission.updated_at)).label('days')
            }
        })
        
        return jsonify(permission_data), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Errore nel recupero del permesso',
            'message': str(e)
        }), 500


@api_v1_bp.route('/permissions', methods=['POST'])
@jwt_required()
def create_permission():
    """
    Crea un nuovo permesso.
    Solo per sviluppatori (Rohirrim).
    """
    # Verifica accesso sviluppatore
    access_error = require_developer_access()
    if access_error:
        return access_error
    
    try:
        # Validazione dati
        data = permission_create_schema.load(request.get_json())
        
        # Verifica univocità permesso per ruolo
        existing = Permission.query.filter_by(
            role_id=data['role_id'],
            name=data['name']
        ).first()
        
        if existing:
            return jsonify({
                'error': 'Permesso già esistente',
                'message': f'Il permesso "{data["name"]}" esiste già per questo ruolo',
                'existing_permission_id': existing.id
            }), 409
        
        # Creazione permesso
        permission = Permission(**data)
        db.session.add(permission)
        db.session.commit()
        
        return jsonify({
            'message': 'Permesso creato con successo',
            'permission': permission_schema.dump(permission)
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
            'message': 'Il permesso deve essere unico per ruolo'
        }), 409
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'Errore nella creazione del permesso',
            'message': str(e)
        }), 500


@api_v1_bp.route('/permissions/<int:permission_id>', methods=['PUT'])
@jwt_required()
def update_permission(permission_id):
    """
    Aggiorna un permesso esistente.
    Solo per sviluppatori (Rohirrim).
    """
    # Verifica accesso sviluppatore
    access_error = require_developer_access()
    if access_error:
        return access_error
    
    try:
        permission = Permission.query.get_or_404(permission_id)
        
        # Protezione permessi di sistema critici
        if permission.category == 'system' and permission.name.startswith('system.'):
            protected_fields = ['name', 'category']
            data = request.get_json()
            if any(field in data for field in protected_fields):
                return jsonify({
                    'error': 'Permesso di sistema protetto',
                    'message': f'Non è possibile modificare nome o categoria del permesso di sistema {permission.name}',
                    'protected_fields': protected_fields
                }), 403
        
        # Validazione dati
        data = permission_update_schema.load(request.get_json())
        
        # Aggiornamento
        for key, value in data.items():
            setattr(permission, key, value)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Permesso aggiornato con successo',
            'permission': permission_schema.dump(permission)
        }), 200
        
    except ValidationError as e:
        return jsonify({
            'error': 'Dati non validi',
            'details': e.messages
        }), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'Errore nell\'aggiornamento del permesso',
            'message': str(e)
        }), 500


@api_v1_bp.route('/permissions/<int:permission_id>', methods=['DELETE'])
@jwt_required()
def delete_permission(permission_id):
    """
    Elimina un permesso (soft delete).
    Solo per sviluppatori (Rohirrim).
    """
    # Verifica accesso sviluppatore
    access_error = require_developer_access()
    if access_error:
        return access_error
    
    try:
        permission = Permission.query.get_or_404(permission_id)
        
        # Protezione permessi di sistema critici
        if permission.category == 'system':
            return jsonify({
                'error': 'Permesso di sistema protetto',
                'message': f'Non è possibile eliminare il permesso di sistema {permission.name}'
            }), 403
        
        # Soft delete
        permission.is_active = False
        permission.deleted_at = func.now()
        db.session.commit()
        
        return jsonify({
            'message': 'Permesso eliminato con successo',
            'permission_name': permission.name,
            'permission_display_name': permission.display_name
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'Errore nell\'eliminazione del permesso',
            'message': str(e)
        }), 500


@api_v1_bp.route('/permissions/bulk', methods=['POST'])
@jwt_required()
def create_permissions_bulk():
    """
    Crea permessi in batch.
    Solo per sviluppatori (Rohirrim).
    """
    # Verifica accesso sviluppatore
    access_error = require_developer_access()
    if access_error:
        return access_error
    
    try:
        # Validazione dati
        data = permission_bulk_create_schema.load(request.get_json())
        permissions_data = data['permissions']
        
        created_permissions = []
        errors = []
        
        for i, perm_data in enumerate(permissions_data):
            try:
                # Verifica univocità per ogni permesso
                existing = Permission.query.filter_by(
                    role_id=perm_data['role_id'],
                    name=perm_data['name']
                ).first()
                
                if existing:
                    errors.append({
                        'index': i,
                        'name': perm_data['name'],
                        'error': 'Permesso già esistente per questo ruolo'
                    })
                    continue
                
                # Creazione permesso
                permission = Permission(**perm_data)
                db.session.add(permission)
                db.session.flush()  # Per ottenere l'ID
                created_permissions.append(permission_schema.dump(permission))
                
            except Exception as e:
                errors.append({
                    'index': i,
                    'name': perm_data.get('name', 'unknown'),
                    'error': str(e)
                })
        
        if errors and not created_permissions:
            db.session.rollback()
            return jsonify({
                'error': 'Nessun permesso creato',
                'errors': errors
            }), 400
        
        db.session.commit()
        
        return jsonify({
            'message': f'{len(created_permissions)} permessi creati con successo',
            'created_permissions': created_permissions,
            'errors': errors if errors else None,
            'summary': {
                'total_requested': len(permissions_data),
                'created': len(created_permissions),
                'failed': len(errors)
            }
        }), 201 if created_permissions else 400
        
    except ValidationError as e:
        return jsonify({
            'error': 'Dati non validi',
            'details': e.messages
        }), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'Errore nella creazione batch dei permessi',
            'message': str(e)
        }), 500


@api_v1_bp.route('/permissions/bulk', methods=['PUT'])
@jwt_required()
def update_permissions_bulk():
    """
    Aggiorna permessi in batch.
    Solo per sviluppatori (Rohirrim).
    """
    # Verifica accesso sviluppatore
    access_error = require_developer_access()
    if access_error:
        return access_error
    
    try:
        # Validazione dati
        data = permission_bulk_update_schema.load(request.get_json())
        permission_ids = data['permission_ids']
        updates = data['updates']
        
        # Recupera i permessi
        permissions = Permission.query.filter(Permission.id.in_(permission_ids)).all()
        if len(permissions) != len(permission_ids):
            return jsonify({
                'error': 'Alcuni permessi non trovati',
                'message': 'Uno o più permission_id non esistono'
            }), 404
        
        updated_permissions = []
        protected_count = 0
        
        for permission in permissions:
            # Protezione permessi di sistema
            if permission.category == 'system' and 'category' in updates:
                protected_count += 1
                continue
            
            # Applica gli aggiornamenti
            for key, value in updates.items():
                if hasattr(permission, key):
                    setattr(permission, key, value)
            
            updated_permissions.append(permission_schema.dump(permission))
        
        db.session.commit()
        
        return jsonify({
            'message': f'{len(updated_permissions)} permessi aggiornati con successo',
            'updated_permissions': updated_permissions,
            'protected_permissions_skipped': protected_count,
            'summary': {
                'total_requested': len(permission_ids),
                'updated': len(updated_permissions),
                'protected_skipped': protected_count
            }
        }), 200
        
    except ValidationError as e:
        return jsonify({
            'error': 'Dati non validi',
            'details': e.messages
        }), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'Errore nell\'aggiornamento batch dei permessi',
            'message': str(e)
        }), 500


@api_v1_bp.route('/permissions/<int:permission_id>/activate', methods=['POST'])
@jwt_required()
def activate_permission(permission_id):
    """
    Riattiva un permesso disattivato.
    Solo per sviluppatori (Rohirrim).
    """
    # Verifica accesso sviluppatore
    access_error = require_developer_access()
    if access_error:
        return access_error
    
    try:
        permission = Permission.query.get_or_404(permission_id)
        
        if permission.is_active:
            return jsonify({
                'message': 'Il permesso è già attivo',
                'permission': permission.name
            }), 200
        
        # Riattivazione
        permission.is_active = True
        permission.deleted_at = None
        db.session.commit()
        
        return jsonify({
            'message': 'Permesso riattivato con successo',
            'permission': permission_schema.dump(permission)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'Errore nella riattivazione del permesso',
            'message': str(e)
        }), 500


@api_v1_bp.route('/permissions/stats', methods=['GET'])
@jwt_required()
def get_permissions_stats():
    """
    Ottiene statistiche complete sui permessi.
    Solo per sviluppatori (Rohirrim).
    """
    # Verifica accesso sviluppatore
    access_error = require_developer_access()
    if access_error:
        return access_error
    
    try:
        # Statistiche base
        total_permissions = Permission.query.count()
        active_permissions = Permission.query.filter_by(is_active=True).count()
        inactive_permissions = total_permissions - active_permissions
        
        # Statistiche per categoria
        category_stats = {}
        categories = db.session.query(Permission.category).distinct().all()
        
        for (category,) in categories:
            total_cat = Permission.query.filter_by(category=category).count()
            active_cat = Permission.query.filter_by(category=category, is_active=True).count()
            roles_with_cat = db.session.query(Permission.role_id).filter_by(
                category=category, is_active=True
            ).distinct().count()
            
            category_stats[category] = {
                'total': total_cat,
                'active': active_cat,
                'inactive': total_cat - active_cat,
                'roles_with_permissions': roles_with_cat
            }
        
        # Permessi per ruolo
        permissions_by_role = {}
        roles_data = db.session.query(
            Role.id, Role.name, Role.display_name,
            func.count(Permission.id).label('permissions_count')
        ).outerjoin(Permission).group_by(Role.id).all()
        
        for role_id, role_name, role_display, perm_count in roles_data:
            permissions_by_role[role_name] = {
                'role_id': role_id,
                'display_name': role_display,
                'permissions_count': perm_count
            }
        
        # Permessi più comuni (per nome base)
        common_permissions = db.session.query(
            func.regexp_replace(Permission.name, r'\..*$', '').label('base_name'),
            func.count(Permission.id).label('count')
        ).filter_by(is_active=True).group_by('base_name').order_by(
            func.count(Permission.id).desc()
        ).limit(10).all()
        
        stats = {
            'total_permissions': total_permissions,
            'active_permissions': active_permissions,
            'inactive_permissions': inactive_permissions,
            'categories_count': len(categories),
            'category_stats': category_stats,
            'permissions_by_role': permissions_by_role,
            'common_permission_patterns': [
                {'pattern': pattern, 'count': count} 
                for pattern, count in common_permissions
            ],
            'available_categories': [cat[0] for cat in categories]
        }
        
        return jsonify(stats), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Errore nel recupero delle statistiche',
            'message': str(e)
        }), 500


@api_v1_bp.route('/permissions/categories', methods=['GET'])
@jwt_required()
def get_permission_categories():
    """
    Ottiene le categorie di permessi disponibili con conteggi.
    Solo per sviluppatori (Rohirrim).
    """
    # Verifica accesso sviluppatore
    access_error = require_developer_access()
    if access_error:
        return access_error
    
    try:
        categories_data = db.session.query(
            Permission.category,
            func.count(Permission.id).label('total'),
            func.sum(func.case([(Permission.is_active == True, 1)], else_=0)).label('active')
        ).group_by(Permission.category).order_by(Permission.category).all()
        
        categories = []
        for category, total, active in categories_data:
            categories.append({
                'name': category,
                'total_permissions': total,
                'active_permissions': active,
                'inactive_permissions': total - active
            })
        
        return jsonify({
            'categories': categories,
            'total_categories': len(categories)
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Errore nel recupero delle categorie',
            'message': str(e)
        }), 500
