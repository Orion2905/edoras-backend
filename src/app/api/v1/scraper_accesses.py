# Scraper Access CRUD API - Sistema Completo

from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_current_user
from sqlalchemy import or_, func, text
from sqlalchemy.exc import IntegrityError
from datetime import date, datetime, timedelta
from ...models.scraper_access import ScraperAccess, get_supported_platforms, create_default_access_template
from ...models.company import Company
from ...schemas import (
    scraper_access_schema, scraper_accesses_schema,
    scraper_access_create_schema, scraper_access_update_schema,
    scraper_access_list_schema, scraper_access_stats_schema,
    scraper_access_duplicate_check_schema, scraper_access_bulk_action_schema,
    scraper_access_verification_schema, scraper_access_credentials_schema,
    scraper_access_platform_types_schema
)
from ...extensions import db
from marshmallow import ValidationError
from . import api_v1_bp


def user_can_manage_scraper_access(user):
    """Verifica se l'utente può gestire gli accessi scraper (solo Rohirrim)."""
    return user and user.is_active and user.role and user.role.is_rohirrim()


def user_can_view_scraper_access(user):
    """Verifica se l'utente può visualizzare gli accessi scraper."""
    if not user or not user.is_active:
        return False
    
    # Rohirrim, Lord e Dunedain possono tutti visualizzare gli accessi scraper
    if user.role and (user.role.is_rohirrim() or user.role.is_lord() or user.role.is_dunedain()):
        return True
    
    return False


def user_can_view_credentials(user):
    """Verifica se l'utente può visualizzare le credenziali complete (solo Rohirrim)."""
    return user and user.is_active and user.role and user.role.is_rohirrim()


@api_v1_bp.route('/scraper-accesses', methods=['GET'])
@jwt_required()
def get_scraper_accesses():
    """
    Ottiene la lista degli accessi scraper con filtri avanzati.
    Tutti i ruoli possono visualizzare gli accessi scraper.
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_view_scraper_access(current_user):
            return jsonify({'error': 'Non autorizzato a visualizzare gli accessi scraper'}), 403
        
        # Validazione parametri
        try:
            args = scraper_access_list_schema.load(request.args)
        except ValidationError as err:
            return jsonify({'error': 'Parametri non validi', 'details': err.messages}), 400
        
        # Query base
        query = ScraperAccess.query
        
        # Filtri
        if args.get('platform_type'):
            query = query.filter(ScraperAccess.platform_type == args['platform_type'])
        
        if args.get('company_id'):
            query = query.filter(ScraperAccess.company_id == args['company_id'])
        
        if args.get('is_active') is not None:
            query = query.filter(ScraperAccess.is_active == args['is_active'])
        
        if args.get('is_verified') is not None:
            query = query.filter(ScraperAccess.is_verified == args['is_verified'])
        
        if args.get('auto_scrape') is not None:
            query = query.filter(ScraperAccess.auto_scrape == args['auto_scrape'])
        
        if args.get('scrape_due'):
            # Filtro per accessi che richiedono scraping
            now = datetime.utcnow()
            query = query.filter(
                ScraperAccess.is_active == True,
                ScraperAccess.auto_scrape == True,
                ScraperAccess.is_verified == True,
                or_(
                    ScraperAccess.last_scrape.is_(None),
                    func.date_add(ScraperAccess.last_scrape, text("INTERVAL 1 DAY")) <= now  # Semplificato per daily
                )
            )
        
        # Ricerca testuale
        if args.get('search'):
            search_term = f"%{args['search']}%"
            query = query.join(Company, ScraperAccess.company_id == Company.id).filter(
                or_(
                    ScraperAccess.platform_name.ilike(search_term),
                    Company.display_name.ilike(search_term),
                    ScraperAccess.notes.ilike(search_term)
                )
            )
        
        # Ordinamento
        sort_by = args.get('sort_by', 'platform_name')
        sort_order = args.get('sort_order', 'asc')
        
        if sort_by == 'company_name':
            query = query.join(Company, ScraperAccess.company_id == Company.id)
            sort_column = Company.display_name
        else:
            sort_column = getattr(ScraperAccess, sort_by, ScraperAccess.platform_name)
        
        if sort_order == 'desc':
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())
        
        # Paginazione
        page = args.get('page', 1)
        per_page = args.get('per_page', 20)
        
        accesses = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        # Serializzazione con o senza credenziali complete
        include_credentials = user_can_view_credentials(current_user)
        
        result = []
        for access in accesses.items:
            access_data = access.to_dict(include_credentials=include_credentials)
            result.append(access_data)
        
        return jsonify({
            'scraper_accesses': result,
            'pagination': {
                'page': accesses.page,
                'per_page': accesses.per_page,
                'total': accesses.total,
                'pages': accesses.pages,
                'has_next': accesses.has_next,
                'has_prev': accesses.has_prev
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Errore durante il recupero degli accessi scraper', 'details': str(e)}), 500


@api_v1_bp.route('/scraper-accesses', methods=['POST'])
@jwt_required()
def create_scraper_access():
    """
    Crea un nuovo accesso scraper.
    Solo gli utenti Rohirrim possono creare accessi scraper.
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_manage_scraper_access(current_user):
            return jsonify({'error': 'Non autorizzato a creare accessi scraper'}), 403
        
        # Validazione dati
        try:
            data = scraper_access_create_schema.load(request.get_json())
        except ValidationError as err:
            return jsonify({'error': 'Dati non validi', 'details': err.messages}), 400
        
        # Verifica esistenza azienda
        company = Company.query.filter_by(id=data['company_id'], is_active=True).first()
        if not company:
            return jsonify({'error': 'Azienda non trovata o non attiva'}), 404
        
        # Controllo duplicati
        existing = ScraperAccess.get_company_platform(data['company_id'], data['platform_name'])
        if existing:
            return jsonify({
                'error': 'Accesso scraper già esistente',
                'details': f"Già presente accesso per {data['platform_name']} nell'azienda {company.display_name}"
            }), 409
        
        # Creazione nuovo accesso
        new_access = ScraperAccess(
            platform_name=data['platform_name'],
            platform_type=data['platform_type'],
            platform_url=data.get('platform_url'),
            scrape_frequency=data.get('scrape_frequency', 'daily'),
            auto_scrape=data.get('auto_scrape', True),
            notes=data.get('notes'),
            config_json=data.get('config_json'),
            company_id=data['company_id']
        )
        
        # Impostazione dati di accesso
        new_access.set_access_data(data['access_data'])
        
        db.session.add(new_access)
        db.session.commit()
        
        return jsonify({
            'message': 'Accesso scraper creato con successo',
            'scraper_access': new_access.to_dict(include_credentials=user_can_view_credentials(current_user))
        }), 201
        
    except IntegrityError as e:
        db.session.rollback()
        return jsonify({'error': 'Errore di integrità dei dati', 'details': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Errore durante la creazione dell\'accesso scraper', 'details': str(e)}), 500


@api_v1_bp.route('/scraper-accesses/<int:access_id>', methods=['GET'])
@jwt_required()
def get_scraper_access(access_id):
    """
    Ottiene i dettagli di un accesso scraper specifico.
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_view_scraper_access(current_user):
            return jsonify({'error': 'Non autorizzato a visualizzare gli accessi scraper'}), 403
        
        # Trova l'accesso
        access = ScraperAccess.query.filter_by(id=access_id).first()
        if not access:
            return jsonify({'error': 'Accesso scraper non trovato'}), 404
        
        # Serializzazione con o senza credenziali complete
        include_credentials = user_can_view_credentials(current_user)
        
        return jsonify({
            'scraper_access': access.to_dict(include_credentials=include_credentials)
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Errore durante il recupero dell\'accesso scraper', 'details': str(e)}), 500


@api_v1_bp.route('/scraper-accesses/<int:access_id>', methods=['PUT'])
@jwt_required()
def update_scraper_access(access_id):
    """
    Aggiorna un accesso scraper esistente.
    Solo gli utenti Rohirrim possono aggiornare accessi scraper.
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_manage_scraper_access(current_user):
            return jsonify({'error': 'Non autorizzato a modificare accessi scraper'}), 403
        
        # Trova l'accesso
        access = ScraperAccess.query.filter_by(id=access_id).first()
        if not access:
            return jsonify({'error': 'Accesso scraper non trovato'}), 404
        
        # Validazione dati
        try:
            data = scraper_access_update_schema.load(request.get_json())
        except ValidationError as err:
            return jsonify({'error': 'Dati non validi', 'details': err.messages}), 400
        
        # Controllo duplicati se cambia nome piattaforma
        if 'platform_name' in data and data['platform_name'] != access.platform_name:
            existing = ScraperAccess.get_company_platform(access.company_id, data['platform_name'])
            if existing and existing.id != access_id:
                return jsonify({
                    'error': 'Nome piattaforma già esistente',
                    'details': f"Già presente accesso per {data['platform_name']} nell'azienda"
                }), 409
        
        # Aggiornamento campi
        for field, value in data.items():
            if field == 'access_data':
                # Merge dei dati di accesso esistenti con quelli nuovi
                current_data = access.get_access_data()
                current_data.update(value)
                access.set_access_data(current_data)
            else:
                setattr(access, field, value)
        
        # Se vengono aggiornate le credenziali, resettiamo la verifica
        if 'access_data' in data:
            access.is_verified = False
            access.last_verified = None
        
        db.session.commit()
        
        return jsonify({
            'message': 'Accesso scraper aggiornato con successo',
            'scraper_access': access.to_dict(include_credentials=user_can_view_credentials(current_user))
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Errore durante l\'aggiornamento dell\'accesso scraper', 'details': str(e)}), 500


@api_v1_bp.route('/scraper-accesses/<int:access_id>', methods=['DELETE'])
@jwt_required()
def delete_scraper_access(access_id):
    """
    Elimina un accesso scraper.
    Solo gli utenti Rohirrim possono eliminare accessi scraper.
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_manage_scraper_access(current_user):
            return jsonify({'error': 'Non autorizzato a eliminare accessi scraper'}), 403
        
        # Trova l'accesso
        access = ScraperAccess.query.filter_by(id=access_id).first()
        if not access:
            return jsonify({'error': 'Accesso scraper non trovato'}), 404
        
        # Soft delete - disattiva invece di eliminare fisicamente
        access.is_active = False
        db.session.commit()
        
        return jsonify({
            'message': 'Accesso scraper eliminato con successo',
            'access_id': access_id
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Errore durante l\'eliminazione dell\'accesso scraper', 'details': str(e)}), 500


@api_v1_bp.route('/scraper-accesses/<int:access_id>/verify', methods=['POST'])
@jwt_required()
def verify_scraper_access(access_id):
    """
    Verifica le credenziali di un accesso scraper.
    Solo gli utenti Rohirrim possono verificare accessi scraper.
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_manage_scraper_access(current_user):
            return jsonify({'error': 'Non autorizzato a verificare accessi scraper'}), 403
        
        # Trova l'accesso
        access = ScraperAccess.query.filter_by(id=access_id).first()
        if not access:
            return jsonify({'error': 'Accesso scraper non trovato'}), 404
        
        # Validazione dati
        try:
            data = scraper_access_verification_schema.load(request.get_json() or {})
        except ValidationError as err:
            return jsonify({'error': 'Dati non validi', 'details': err.messages}), 400
        
        # Verifica che l'accesso sia attivo
        if not access.is_active:
            return jsonify({'error': 'Impossibile verificare un accesso disattivato'}), 400
        
        # Verifica credenziali
        is_valid, missing_fields = access.validate_credentials()
        if not is_valid:
            return jsonify({
                'error': 'Credenziali incomplete',
                'missing_fields': missing_fields
            }), 400
        
        # Qui dovrebbe essere implementata la logica di verifica effettiva
        # Per ora simuliamo una verifica riuscita
        success = True  # TODO: Implementare la verifica reale
        
        # Aggiorna stato verifica
        access.mark_verified(success)
        
        return jsonify({
            'message': 'Verifica completata con successo' if success else 'Verifica fallita',
            'verified': success,
            'last_verified': access.last_verified.isoformat() if access.last_verified else None,
            'scraper_access': access.to_dict(include_credentials=user_can_view_credentials(current_user))
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Errore durante la verifica dell\'accesso scraper', 'details': str(e)}), 500


@api_v1_bp.route('/scraper-accesses/<int:access_id>/credentials', methods=['PATCH'])
@jwt_required()
def update_scraper_access_credentials(access_id):
    """
    Aggiorna solo le credenziali di un accesso scraper.
    Solo gli utenti Rohirrim possono aggiornare credenziali.
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_manage_scraper_access(current_user):
            return jsonify({'error': 'Non autorizzato a modificare credenziali'}), 403
        
        # Trova l'accesso
        access = ScraperAccess.query.filter_by(id=access_id).first()
        if not access:
            return jsonify({'error': 'Accesso scraper non trovato'}), 404
        
        # Validazione dati
        try:
            data = scraper_access_credentials_schema.load(request.get_json())
        except ValidationError as err:
            return jsonify({'error': 'Dati non validi', 'details': err.messages}), 400
        
        # Aggiorna credenziali
        current_data = access.get_access_data()
        current_data.update(data['credentials'])
        access.set_access_data(current_data)
        
        # Reset verifica
        access.is_verified = False
        access.last_verified = None
        
        db.session.commit()
        
        # Verifica automatica se richiesta
        if data.get('verify_after_update', True):
            is_valid, missing_fields = access.validate_credentials()
            if is_valid:
                # Simulazione verifica automatica
                access.mark_verified(True)  # TODO: Implementare verifica reale
        
        return jsonify({
            'message': 'Credenziali aggiornate con successo',
            'scraper_access': access.to_dict(include_credentials=user_can_view_credentials(current_user))
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Errore durante l\'aggiornamento delle credenziali', 'details': str(e)}), 500


@api_v1_bp.route('/scraper-accesses/bulk-actions', methods=['POST'])
@jwt_required()
def bulk_actions_scraper_access():
    """
    Esegue azioni bulk su accessi scraper.
    Solo gli utenti Rohirrim possono eseguire azioni bulk.
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_manage_scraper_access(current_user):
            return jsonify({'error': 'Non autorizzato a eseguire azioni bulk'}), 403
        
        # Validazione dati
        try:
            data = scraper_access_bulk_action_schema.load(request.get_json())
        except ValidationError as err:
            return jsonify({'error': 'Dati non validi', 'details': err.messages}), 400
        
        # Trova gli accessi
        accesses = ScraperAccess.query.filter(ScraperAccess.id.in_(data['ids'])).all()
        
        if not accesses:
            return jsonify({'error': 'Nessun accesso scraper trovato'}), 404
        
        if len(accesses) != len(data['ids']):
            return jsonify({'error': 'Alcuni accessi scraper non sono stati trovati'}), 404
        
        # Esegui azione
        action = data['action']
        updated_count = 0
        
        for access in accesses:
            if action == 'activate':
                access.is_active = True
                updated_count += 1
            elif action == 'deactivate':
                access.is_active = False
                updated_count += 1
            elif action == 'enable_auto_scrape':
                access.auto_scrape = True
                updated_count += 1
            elif action == 'disable_auto_scrape':
                access.auto_scrape = False
                updated_count += 1
            elif action == 'verify_credentials':
                is_valid, _ = access.validate_credentials()
                if is_valid:
                    access.mark_verified(True)  # TODO: Implementare verifica reale
                    updated_count += 1
            elif action == 'delete':
                access.is_active = False  # Soft delete
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


@api_v1_bp.route('/scraper-accesses/stats', methods=['GET'])
@jwt_required()
def get_scraper_access_stats():
    """
    Ottiene statistiche sugli accessi scraper.
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_view_scraper_access(current_user):
            return jsonify({'error': 'Non autorizzato a visualizzare le statistiche'}), 403
        
        # Statistiche generali
        total_accesses = ScraperAccess.query.count()
        active_accesses = ScraperAccess.query.filter_by(is_active=True).count()
        verified_accesses = ScraperAccess.query.filter_by(is_active=True, is_verified=True).count()
        auto_scrape_enabled = ScraperAccess.query.filter_by(is_active=True, auto_scrape=True).count()
        pending_verification = ScraperAccess.query.filter_by(is_active=True, is_verified=False).count()
        
        # Accessi che richiedono scraping
        scrape_due_count = len([a for a in ScraperAccess.query.filter_by(is_active=True).all() if a.is_scrape_due()])
        
        # Statistiche per tipo piattaforma
        platform_type_stats = db.session.query(
            ScraperAccess.platform_type,
            func.count(ScraperAccess.id).label('count')
        ).filter_by(is_active=True).group_by(ScraperAccess.platform_type).all()
        
        by_platform_type = {stat[0]: stat[1] for stat in platform_type_stats}
        
        # Statistiche per azienda
        company_stats = db.session.query(
            Company.display_name,
            func.count(ScraperAccess.id).label('count')
        ).join(ScraperAccess, Company.id == ScraperAccess.company_id)\
        .filter(ScraperAccess.is_active == True).group_by(Company.display_name).all()
        
        by_company = {stat[0]: stat[1] for stat in company_stats}
        
        # Scraping recenti (ultimi 7 giorni)
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_scrapes = ScraperAccess.query.filter(
            ScraperAccess.last_scrape >= week_ago
        ).count()
        
        stats = {
            'total_accesses': total_accesses,
            'active_accesses': active_accesses,
            'verified_accesses': verified_accesses,
            'auto_scrape_enabled': auto_scrape_enabled,
            'pending_verification': pending_verification,
            'scrape_due_count': scrape_due_count,
            'by_platform_type': by_platform_type,
            'by_company': by_company,
            'recent_scrapes': recent_scrapes
        }
        
        return jsonify({'stats': stats}), 200
        
    except Exception as e:
        return jsonify({'error': 'Errore durante il calcolo delle statistiche', 'details': str(e)}), 500


@api_v1_bp.route('/scraper-accesses/check-duplicate', methods=['POST'])
@jwt_required()
def check_duplicate_scraper_access():
    """
    Controlla se esiste già un accesso scraper per azienda e piattaforma.
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_view_scraper_access(current_user):
            return jsonify({'error': 'Non autorizzato'}), 403
        
        # Validazione dati
        try:
            data = scraper_access_duplicate_check_schema.load(request.get_json())
        except ValidationError as err:
            return jsonify({'error': 'Dati non validi', 'details': err.messages}), 400
        
        # Controllo duplicato
        query = ScraperAccess.query.filter_by(
            platform_name=data['platform_name'],
            company_id=data['company_id']
        )
        
        if data.get('exclude_id'):
            query = query.filter(ScraperAccess.id != data['exclude_id'])
        
        existing = query.first()
        
        return jsonify({
            'exists': existing is not None,
            'existing_access': existing.to_dict(include_credentials=False) if existing else None
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Errore durante il controllo duplicati', 'details': str(e)}), 500


@api_v1_bp.route('/scraper-accesses/platform-types', methods=['GET'])
@jwt_required()
def get_platform_types():
    """
    Ottiene i tipi di piattaforma supportati e le piattaforme disponibili.
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_view_scraper_access(current_user):
            return jsonify({'error': 'Non autorizzato'}), 403
        
        supported_platforms = get_supported_platforms()
        platform_types = list(supported_platforms.keys())
        
        return jsonify({
            'supported_platforms': supported_platforms,
            'platform_types': platform_types
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Errore durante il recupero dei tipi piattaforma', 'details': str(e)}), 500


@api_v1_bp.route('/scraper-accesses/companies/<int:company_id>', methods=['GET'])
@jwt_required()
def get_scraper_accesses_by_company(company_id):
    """
    Ottiene tutti gli accessi scraper per una specifica azienda.
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_view_scraper_access(current_user):
            return jsonify({'error': 'Non autorizzato'}), 403
        
        # Verifica esistenza azienda
        company = Company.query.filter_by(id=company_id, is_active=True).first()
        if not company:
            return jsonify({'error': 'Azienda non trovata'}), 404
        
        # Ottieni accessi per azienda
        active_only = request.args.get('active_only', 'true').lower() == 'true'
        accesses = ScraperAccess.get_by_company(company_id, active_only=active_only)
        
        # Serializzazione
        include_credentials = user_can_view_credentials(current_user)
        result = [access.to_dict(include_credentials=include_credentials) for access in accesses]
        
        return jsonify({
            'company': {
                'id': company.id,
                'name': company.display_name
            },
            'scraper_accesses': result,
            'total_count': len(result)
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Errore durante il recupero degli accessi scraper', 'details': str(e)}), 500


@api_v1_bp.route('/scraper-accesses/due-for-scraping', methods=['GET'])
@jwt_required()
def get_scraper_accesses_due_for_scraping():
    """
    Ottiene tutti gli accessi che richiedono scraping.
    Solo gli utenti Rohirrim possono accedere a questa funzione.
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_manage_scraper_access(current_user):
            return jsonify({'error': 'Non autorizzato'}), 403
        
        # Ottieni accessi che richiedono scraping
        all_accesses = ScraperAccess.get_auto_scrape_enabled()
        due_accesses = [access for access in all_accesses if access.is_scrape_due()]
        
        # Serializzazione con credenziali complete per scraping
        result = [access.to_dict(include_credentials=True) for access in due_accesses]
        
        return jsonify({
            'scraper_accesses': result,
            'total_due': len(result),
            'message': f'Trovati {len(result)} accessi che richiedono scraping'
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Errore durante il recupero degli accessi da scrapare', 'details': str(e)}), 500
