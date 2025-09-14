"""
Utilities for authentication and authorization
"""

from functools import wraps
from flask import jsonify
from flask_jwt_extended import get_current_user
from typing import List, Union


def require_role(allowed_roles: Union[str, List[str]]):
    """
    Decorator per verificare che l'utente abbia uno dei ruoli richiesti.
    
    Args:
        allowed_roles: Un ruolo singolo (stringa) o lista di ruoli permessi
                      Es: 'Rohirrim' oppure ['Rohirrim', 'Lord']
    
    Returns:
        Decorator function che controlla i ruoli dell'utente
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            current_user = get_current_user()
            
            if not current_user:
                return jsonify({
                    'error': 'Authentication required',
                    'message': 'Devi essere autenticato per accedere a questa risorsa',
                    'code': 'AUTHENTICATION_REQUIRED'
                }), 401
            
            if not current_user.role:
                return jsonify({
                    'error': 'Role required',
                    'message': 'Utente senza ruolo assegnato',
                    'code': 'NO_ROLE_ASSIGNED'
                }), 403
            
            # Normalizza allowed_roles a lista
            if isinstance(allowed_roles, str):
                roles_list = [allowed_roles]
            else:
                roles_list = allowed_roles
            
            # Verifica se il ruolo dell'utente è tra quelli permessi
            user_role_name = current_user.role.display_name
            if user_role_name not in roles_list:
                return jsonify({
                    'error': 'Insufficient privileges',
                    'message': f'Accesso negato. Ruoli richiesti: {", ".join(roles_list)}. Ruolo attuale: {user_role_name}',
                    'code': 'INSUFFICIENT_PRIVILEGES',
                    'required_roles': roles_list,
                    'current_role': user_role_name
                }), 403
            
            # Se tutto ok, esegui la funzione originale
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def require_developer_access():
    """
    Helper per verificare accesso sviluppatore (Rohirrim only).
    Compatibile con il pattern esistente in roles.py e permissions.py
    """
    current_user = get_current_user()
    
    if not current_user:
        return jsonify({
            'error': 'Authentication required',
            'message': 'Devi essere autenticato per accedere a questa risorsa',
            'code': 'AUTHENTICATION_REQUIRED'
        }), 401
    
    if not current_user.role or not current_user.role.is_rohirrim():
        return jsonify({
            'error': 'Accesso negato',
            'message': 'Solo i Rohirrim (sviluppatori) possono accedere a questa funzionalità',
            'code': 'DEVELOPER_ACCESS_REQUIRED'
        }), 403
    
    return None


def developer_required():
    """
    Helper per verificare che l'utente sia un Rohirrim (developer).
    Restituisce True/False invece di una response.
    """
    current_user = get_current_user()
    if not current_user:
        return False
    
    return current_user.role and current_user.role.is_rohirrim()


def user_has_role(role_name: str) -> bool:
    """
    Verifica se l'utente corrente ha un ruolo specifico.
    
    Args:
        role_name: Nome del ruolo da verificare (display_name)
    
    Returns:
        True se l'utente ha il ruolo, False altrimenti
    """
    current_user = get_current_user()
    if not current_user or not current_user.role:
        return False
    
    return current_user.role.display_name == role_name


def user_has_access_level(required_level: int) -> bool:
    """
    Verifica se l'utente corrente ha almeno il livello di accesso richiesto.
    
    Args:
        required_level: Livello di accesso richiesto (1=massimo, 3=minimo)
    
    Returns:
        True se l'utente ha accesso sufficiente, False altrimenti
    """
    current_user = get_current_user()
    if not current_user or not current_user.role:
        return False
    
    return current_user.role.access_level <= required_level
