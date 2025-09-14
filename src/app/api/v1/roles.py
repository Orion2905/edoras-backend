# Roles CRUD API - Solo per Sviluppatori (Rohirrim)

from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_current_user
from sqlalchemy import or_, func, and_
from sqlalchemy.exc import IntegrityError
from ...models.role import Role
from ...models.permission import Permission
from ...models.user import User
from ...schemas import (
    role_schema, roles_schema,
    role_create_schema, role_update_schema,
    role_permission_assignment_schema, role_list_schema,
    role_stats_schema
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


@api_v1_bp.route('/roles', methods=['GET'])
@jwt_required()
def get_roles():
    """
    Ottiene la lista di tutti i ruoli con filtri avanzati.
    Solo per sviluppatori (Rohirrim).
    """
    # Verifica accesso sviluppatore
    access_error = require_developer_access()
    if access_error:
        return access_error
    
    try:
        # Validazione parametri query
        args = role_list_schema.load(request.args)
        
        # Query base
        query = Role.query
        
        # Filtri
        if args.get('search'):
            search_term = f"%{args['search']}%"
            query = query.filter(
                or_(
                    Role.name.ilike(search_term),
                    Role.display_name.ilike(search_term),
                    Role.description.ilike(search_term)
                )
            )
        
        if args.get('access_level') is not None:
            query = query.filter(Role.access_level == args['access_level'])
        
        if args.get('is_active') is not None:
            query = query.filter(Role.is_active == args['is_active'])
        
        # Ordinamento
        query = query.order_by(Role.access_level.asc(), Role.name.asc())
        
        # Paginazione
        page = args.get('page', 1)
        per_page = args.get('per_page', 20)
        pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        # Serializzazione
        if args.get('include_permissions'):
            roles_data = []
            for role in pagination.items:
                role_data = role_schema.dump(role)
                if args.get('include_stats'):
                    role_data.update({
                        'permissions_count': role.permissions.filter_by(is_active=True).count(),
                        'users_count': role.users.filter_by(is_active=True).count()
                    })
                roles_data.append(role_data)
        else:
            roles_data = roles_schema.dump(pagination.items, exclude=['permissions_list'])
        
        return jsonify({
            'roles': roles_data,
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
                'access_level': args.get('access_level'),
                'is_active': args.get('is_active'),
                'include_permissions': args.get('include_permissions'),
                'include_stats': args.get('include_stats')
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


@api_v1_bp.route('/roles/<int:role_id>', methods=['GET'])
@jwt_required()
def get_role(role_id):
    """
    Ottiene i dettagli di un ruolo specifico.
    Solo per sviluppatori (Rohirrim).
    """
    # Verifica accesso sviluppatore
    access_error = require_developer_access()
    if access_error:
        return access_error
    
    try:
        role = Role.query.get_or_404(role_id)
        
        # Serializzazione completa con statistiche
        role_data = role_schema.dump(role)
        role_data.update({
            'permissions': [
                {
                    'id': perm.id,
                    'name': perm.name,
                    'display_name': perm.display_name,
                    'description': perm.description,
                    'is_active': perm.is_active
                }
                for perm in role.permissions.all()
            ],
            'users_count': role.users.filter_by(is_active=True).count(),
            'recent_users': [
                {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'full_name': user.full_name,
                    'is_active': user.is_active,
                    'last_login': user.last_login.isoformat() if user.last_login else None
                }
                for user in role.users.filter_by(is_active=True).order_by(User.last_login.desc()).limit(5).all()
            ]
        })
        
        return jsonify(role_data), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Errore nel recupero del ruolo',
            'message': str(e)
        }), 500


@api_v1_bp.route('/roles', methods=['POST'])
@jwt_required()
def create_role():
    """
    Crea un nuovo ruolo.
    Solo per sviluppatori (Rohirrim).
    """
    # Verifica accesso sviluppatore
    access_error = require_developer_access()
    if access_error:
        return access_error
    
    try:
        # Validazione dati
        data = role_create_schema.load(request.get_json())
        
        # Verifica che non ci sia già un ruolo di default se questo è marcato come default
        if data.get('is_default', False):
            existing_default = Role.query.filter_by(is_default=True).first()
            if existing_default:
                return jsonify({
                    'error': 'Ruolo di default esistente',
                    'message': f'Il ruolo "{existing_default.display_name}" è già impostato come default',
                    'suggestion': 'Rimuovi il flag default dal ruolo esistente prima di crearne uno nuovo'
                }), 409
        
        # Creazione ruolo
        role = Role(**data)
        db.session.add(role)
        db.session.commit()
        
        return jsonify({
            'message': 'Ruolo creato con successo',
            'role': role_schema.dump(role)
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
            'message': 'Il nome del ruolo deve essere unico'
        }), 409
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'Errore nella creazione del ruolo',
            'message': str(e)
        }), 500


@api_v1_bp.route('/roles/<int:role_id>', methods=['PUT'])
@jwt_required()
def update_role(role_id):
    """
    Aggiorna un ruolo esistente.
    Solo per sviluppatori (Rohirrim).
    """
    # Verifica accesso sviluppatore
    access_error = require_developer_access()
    if access_error:
        return access_error
    
    try:
        role = Role.query.get_or_404(role_id)
        
        # Protezione ruoli di sistema
        if role.name in ['rohirrim', 'lord', 'dunedain']:
            protected_fields = ['name', 'access_level']
            data = request.get_json()
            if any(field in data for field in protected_fields):
                return jsonify({
                    'error': 'Ruolo di sistema protetto',
                    'message': f'Non è possibile modificare nome o livello di accesso del ruolo {role.display_name}',
                    'protected_fields': protected_fields
                }), 403
        
        # Validazione dati
        data = role_update_schema.load(request.get_json())
        
        # Verifica ruolo di default
        if data.get('is_default', False) and not role.is_default:
            existing_default = Role.query.filter_by(is_default=True).first()
            if existing_default:
                return jsonify({
                    'error': 'Ruolo di default esistente',
                    'message': f'Il ruolo "{existing_default.display_name}" è già impostato come default'
                }), 409
        
        # Aggiornamento
        for key, value in data.items():
            setattr(role, key, value)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Ruolo aggiornato con successo',
            'role': role_schema.dump(role)
        }), 200
        
    except ValidationError as e:
        return jsonify({
            'error': 'Dati non validi',
            'details': e.messages
        }), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'Errore nell\'aggiornamento del ruolo',
            'message': str(e)
        }), 500


@api_v1_bp.route('/roles/<int:role_id>', methods=['DELETE'])
@jwt_required()
def delete_role(role_id):
    """
    Elimina un ruolo (soft delete).
    Solo per sviluppatori (Rohirrim).
    """
    # Verifica accesso sviluppatore
    access_error = require_developer_access()
    if access_error:
        return access_error
    
    try:
        role = Role.query.get_or_404(role_id)
        
        # Protezione ruoli di sistema
        if role.name in ['rohirrim', 'lord', 'dunedain']:
            return jsonify({
                'error': 'Ruolo di sistema protetto',
                'message': f'Non è possibile eliminare il ruolo di sistema {role.display_name}'
            }), 403
        
        # Verifica utenti associati
        active_users_count = role.users.filter_by(is_active=True).count()
        if active_users_count > 0:
            return jsonify({
                'error': 'Ruolo in uso',
                'message': f'Il ruolo ha {active_users_count} utenti attivi associati',
                'suggestion': 'Riassegna gli utenti ad altri ruoli prima di eliminare questo ruolo'
            }), 409
        
        # Soft delete
        role.is_active = False
        role.deleted_at = func.now()
        db.session.commit()
        
        return jsonify({
            'message': 'Ruolo eliminato con successo',
            'role_name': role.display_name
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'Errore nell\'eliminazione del ruolo',
            'message': str(e)
        }), 500


@api_v1_bp.route('/roles/<int:role_id>/assign-permissions', methods=['POST'])
@jwt_required()
def assign_permissions_to_role(role_id):
    """
    Assegna permessi a un ruolo.
    Solo per sviluppatori (Rohirrim).
    """
    # Verifica accesso sviluppatore
    access_error = require_developer_access()
    if access_error:
        return access_error
    
    try:
        role = Role.query.get_or_404(role_id)
        
        # Validazione dati
        data = role_permission_assignment_schema.load(request.get_json())
        permission_ids = data['permission_ids']
        
        # Recupera i permessi
        permissions = Permission.query.filter(Permission.id.in_(permission_ids)).all()
        if len(permissions) != len(permission_ids):
            return jsonify({
                'error': 'Permessi non trovati',
                'message': 'Alcuni permission_id non esistono'
            }), 404
        
        # Assegnazione permessi (sostituisce i permessi esistenti)
        role.permissions = permissions
        db.session.commit()
        
        return jsonify({
            'message': 'Permessi assegnati con successo',
            'role': role.display_name,
            'permissions_assigned': len(permissions),
            'permissions': [
                {
                    'id': perm.id,
                    'name': perm.name,
                    'display_name': perm.display_name
                }
                for perm in permissions
            ]
        }), 200
        
    except ValidationError as e:
        return jsonify({
            'error': 'Dati non validi',
            'details': e.messages
        }), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'Errore nell\'assegnazione dei permessi',
            'message': str(e)
        }), 500


@api_v1_bp.route('/roles/<int:role_id>/activate', methods=['POST'])
@jwt_required()
def activate_role(role_id):
    """
    Riattiva un ruolo disattivato.
    Solo per sviluppatori (Rohirrim).
    """
    # Verifica accesso sviluppatore
    access_error = require_developer_access()
    if access_error:
        return access_error
    
    try:
        role = Role.query.get_or_404(role_id)
        
        if role.is_active:
            return jsonify({
                'message': 'Il ruolo è già attivo',
                'role': role.display_name
            }), 200
        
        # Riattivazione
        role.is_active = True
        role.deleted_at = None
        db.session.commit()
        
        return jsonify({
            'message': 'Ruolo riattivato con successo',
            'role': role_schema.dump(role)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'Errore nella riattivazione del ruolo',
            'message': str(e)
        }), 500


@api_v1_bp.route('/roles/stats', methods=['GET'])
@jwt_required()
def get_roles_stats():
    """
    Ottiene statistiche complete sui ruoli.
    Solo per sviluppatori (Rohirrim).
    """
    # Verifica accesso sviluppatore
    access_error = require_developer_access()
    if access_error:
        return access_error
    
    try:
        # Statistiche base
        total_roles = Role.query.count()
        active_roles = Role.query.filter_by(is_active=True).count()
        inactive_roles = total_roles - active_roles
        
        # Distribuzione per livello di accesso
        roles_by_level = {}
        level_stats = db.session.query(
            Role.access_level,
            func.count(Role.id).label('count')
        ).filter_by(is_active=True).group_by(Role.access_level).all()
        
        for level, count in level_stats:
            roles_by_level[str(level)] = count
        
        # Ruolo di default
        default_role = Role.query.filter_by(is_default=True).first()
        
        # Statistiche dettagliate per ruolo
        role_details = []
        for role in Role.query.filter_by(is_active=True).order_by(Role.access_level.asc()).all():
            users_count = role.users.filter_by(is_active=True).count()
            permissions_count = role.permissions.filter_by(is_active=True).count()
            
            role_details.append({
                'id': role.id,
                'name': role.name,
                'display_name': role.display_name,
                'access_level': role.access_level,
                'users_count': users_count,
                'permissions_count': permissions_count,
                'is_default': role.is_default,
                'is_system': role.name in ['rohirrim', 'lord', 'dunedain']
            })
        
        stats = {
            'total_roles': total_roles,
            'active_roles': active_roles,
            'inactive_roles': inactive_roles,
            'roles_by_level': roles_by_level,
            'default_role': role_schema.dump(default_role, exclude=['permissions_list']) if default_role else None,
            'role_details': role_details,
            'system_roles': ['rohirrim', 'lord', 'dunedain']
        }
        
        return jsonify(stats), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Errore nel recupero delle statistiche',
            'message': str(e)
        }), 500
