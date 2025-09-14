# POD CRUD API - Sistema Completo

from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_current_user
from sqlalchemy import or_, func, text
from sqlalchemy.exc import IntegrityError
from datetime import date, datetime, timedelta
from ...models.pod import POD, PodType
from ...models.property_pod import PropertyPod
from ...schemas import (
    pod_schema, pods_schema,
    pod_create_schema, pod_update_schema,
    pod_list_schema, pod_stats_schema,
    pod_duplicate_check_schema, pod_bulk_action_schema,
    pod_validation_schema, pod_types_schema
)
from ...extensions import db
from marshmallow import ValidationError
from . import api_v1_bp


def user_can_manage_pods(user):
    """Verifica se l'utente può gestire i POD (solo Rohirrim e Lord)."""
    return user and user.is_active and user.role and (user.role.is_rohirrim() or user.role.is_lord())


def user_can_view_pods(user):
    """Verifica se l'utente può visualizzare i POD."""
    if not user or not user.is_active:
        return False
    
    # Rohirrim, Lord e Dunedain possono tutti visualizzare i POD
    if user.role and (user.role.is_rohirrim() or user.role.is_lord() or user.role.is_dunedain()):
        return True
    
    return False


@api_v1_bp.route('/pods', methods=['GET'])
@jwt_required()
def get_pods():
    """
    Ottiene la lista dei POD con filtri.
    Tutti i ruoli possono visualizzare i POD.
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_view_pods(current_user):
            return jsonify({'error': 'Non autorizzato a visualizzare i POD'}), 403
        
        # Parametri di paginazione e filtri
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        
        # Filtri
        pod_code = request.args.get('pod_code', '').strip()
        pod_type = request.args.get('pod_type', '').strip()
        supplier = request.args.get('supplier', '').strip()
        is_active = request.args.get('is_active', '').strip()
        search = request.args.get('search', '').strip()
        
        # Ordinamento
        sort_by = request.args.get('sort_by', 'pod_code')
        sort_order = request.args.get('sort_order', 'asc')
        
        # Query base
        query = POD.query
        
        # Applicazione filtri
        if pod_code:
            query = query.filter(POD.pod_code.ilike(f'%{pod_code}%'))
            
        if pod_type:
            try:
                pod_type_enum = PodType(pod_type.upper())
                query = query.filter(POD.pod_type == pod_type_enum)
            except ValueError:
                return jsonify({'error': f'Tipo POD non valido: {pod_type}'}), 400
            
        if supplier:
            query = query.filter(POD.supplier.ilike(f'%{supplier}%'))
            
        if is_active.lower() in ['true', 'false']:
            query = query.filter(POD.is_active == (is_active.lower() == 'true'))
            
        # Ricerca testuale
        if search:
            search_term = f'%{search}%'
            query = query.filter(or_(
                POD.pod_code.ilike(search_term),
                POD.supplier.ilike(search_term),
                POD.description.ilike(search_term)
            ))
        
        # Ordinamento
        if hasattr(POD, sort_by):
            sort_field = getattr(POD, sort_by)
            if sort_order.lower() == 'desc':
                sort_field = sort_field.desc()
            query = query.order_by(sort_field)
        else:
            query = query.order_by(POD.pod_code)
        
        # Paginazione
        pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        pods = pagination.items
        
        # Aggiungi info aggiuntive per ogni POD
        pod_data = []
        for pod in pods:
            pod_dict = pod_schema.dump(pod)
            pod_dict['connected_properties_count'] = pod.get_connected_properties_count()
            pod_dict['is_electricity'] = pod.pod_type == PodType.ELECTRICITY
            pod_dict['is_gas'] = pod.pod_type == PodType.GAS
            pod_data.append(pod_dict)
        
        result = {
            'pods': pod_data,
            'pagination': {
                'page': pagination.page,
                'per_page': pagination.per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            }
        }
        
        return jsonify({
            'success': True,
            'message': 'Lista POD recuperata con successo',
            'data': result
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Errore nel recupero POD: {str(e)}'}), 500


@api_v1_bp.route('/pods', methods=['POST'])
@jwt_required()
def create_pod():
    """
    Crea un nuovo POD.
    Solo Rohirrim e Lord possono creare POD.
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_manage_pods(current_user):
            return jsonify({'error': 'Non autorizzato a creare POD'}), 403
        
        # Validazione dati
        try:
            data = pod_create_schema.load(request.get_json())
        except ValidationError as err:
            return jsonify({'error': 'Dati non validi', 'details': err.messages}), 400
        
        # Controllo duplicati codice POD
        existing_pod = POD.query.filter_by(pod_code=data['pod_code']).first()
        if existing_pod:
            return jsonify({'error': f'POD con codice "{data["pod_code"]}" già esistente'}), 400
        
        # Creazione del POD
        pod = POD(**data)
        db.session.add(pod)
        db.session.commit()
        
        # Preparazione risposta
        pod_dict = pod_schema.dump(pod)
        pod_dict['connected_properties_count'] = 0
        pod_dict['is_electricity'] = pod.pod_type == PodType.ELECTRICITY
        pod_dict['is_gas'] = pod.pod_type == PodType.GAS
        
        return jsonify({
            'success': True,
            'message': 'POD creato con successo',
            'data': pod_dict
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Errore nella creazione POD: {str(e)}'}), 500


@api_v1_bp.route('/pods/<int:pod_id>', methods=['GET'])
@jwt_required()
def get_pod(pod_id):
    """
    Ottiene i dettagli di un POD specifico.
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_view_pods(current_user):
            return jsonify({'error': 'Non autorizzato a visualizzare i POD'}), 403
        
        pod = POD.query.filter_by(id=pod_id).first()
        if not pod:
            return jsonify({'error': f'POD con ID {pod_id} non trovato'}), 404
        
        # Preparazione risposta
        pod_dict = pod_schema.dump(pod)
        pod_dict['connected_properties_count'] = pod.get_connected_properties_count()
        pod_dict['is_electricity'] = pod.pod_type == PodType.ELECTRICITY
        pod_dict['is_gas'] = pod.pod_type == PodType.GAS
        
        return jsonify({
            'success': True,
            'message': 'Dettagli POD recuperati con successo',
            'data': pod_dict
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Errore nel recupero POD: {str(e)}'}), 500


@api_v1_bp.route('/pods/<int:pod_id>', methods=['PUT'])
@jwt_required()
def update_pod(pod_id):
    """
    Aggiorna un POD esistente.
    Solo Rohirrim e Lord possono aggiornare POD.
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_manage_pods(current_user):
            return jsonify({'error': 'Non autorizzato a modificare POD'}), 403
        
        pod = POD.query.filter_by(id=pod_id).first()
        if not pod:
            return jsonify({'error': f'POD con ID {pod_id} non trovato'}), 404
        
        # Validazione dati
        try:
            data = pod_update_schema.load(request.get_json())
        except ValidationError as err:
            return jsonify({'error': 'Dati non validi', 'details': err.messages}), 400
        
        # Controllo duplicati se si aggiorna il codice
        if 'pod_code' in data and data['pod_code'] != pod.pod_code:
            existing_pod = POD.query.filter_by(pod_code=data['pod_code']).first()
            if existing_pod:
                return jsonify({'error': f'POD con codice "{data["pod_code"]}" già esistente'}), 400
        
        # Aggiornamento campi
        for field, value in data.items():
            if hasattr(pod, field):
                setattr(pod, field, value)
        
        db.session.commit()
        
        # Preparazione risposta
        pod_dict = pod_schema.dump(pod)
        pod_dict['connected_properties_count'] = pod.get_connected_properties_count()
        pod_dict['is_electricity'] = pod.pod_type == PodType.ELECTRICITY
        pod_dict['is_gas'] = pod.pod_type == PodType.GAS
        
        return jsonify({
            'success': True,
            'message': 'POD aggiornato con successo',
            'data': pod_dict
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Errore nell\'aggiornamento POD: {str(e)}'}), 500


@api_v1_bp.route('/pods/<int:pod_id>', methods=['DELETE'])
@jwt_required()
def delete_pod(pod_id):
    """
    Elimina un POD (soft delete).
    Solo Rohirrim e Lord possono eliminare POD.
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_manage_pods(current_user):
            return jsonify({'error': 'Non autorizzato a eliminare POD'}), 403
        
        pod = POD.query.filter_by(id=pod_id).first()
        if not pod:
            return jsonify({'error': f'POD con ID {pod_id} non trovato'}), 404
        
        # Controllo se ha proprietà connesse attive
        active_connections = PropertyPod.query.filter_by(
            pod_id=pod_id, 
            is_active=True
        ).count()
        
        if active_connections > 0:
            return jsonify({
                'error': f'Impossibile eliminare POD: ha {active_connections} proprietà connesse attive'
            }), 400
        
        # Soft delete
        pod.is_active = False
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'POD eliminato con successo',
            'data': {}
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Errore nell\'eliminazione POD: {str(e)}'}), 500


@api_v1_bp.route('/pods/<int:pod_id>/properties', methods=['GET'])
@jwt_required()
def get_pod_properties(pod_id):
    """
    Ottiene le proprietà connesse a un POD.
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_view_pods(current_user):
            return jsonify({'error': 'Non autorizzato a visualizzare i POD'}), 403
        
        pod = POD.query.filter_by(id=pod_id).first()
        if not pod:
            return jsonify({'error': f'POD con ID {pod_id} non trovato'}), 404
        
        # Recupera le connessioni attive
        property_pods = PropertyPod.query.filter_by(
            pod_id=pod_id,
            is_active=True
        ).all()
        
        # Estrai le unità immobiliari
        properties = []
        for pp in property_pods:
            if pp.property_unit:
                prop_dict = {
                    'id': pp.property_unit.id,
                    'name': pp.property_unit.name,
                    'code': pp.property_unit.code,
                    'address': pp.property_unit.address,
                    'is_primary': pp.is_primary,
                    'notes': pp.notes,
                    'connected_at': pp.created_at.strftime('%Y-%m-%d %H:%M:%S') if pp.created_at else None
                }
                properties.append(prop_dict)
        
        return jsonify({
            'success': True,
            'message': 'Proprietà POD recuperate con successo',
            'data': {
                'pod_id': pod_id,
                'pod_code': pod.pod_code,
                'properties': properties,
                'total_properties': len(properties)
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Errore nel recupero proprietà POD: {str(e)}'}), 500


@api_v1_bp.route('/pods/stats', methods=['GET'])
@jwt_required()
def get_pod_stats():
    """
    Ottiene statistiche dettagliate sui POD.
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_view_pods(current_user):
            return jsonify({'error': 'Non autorizzato a visualizzare statistiche POD'}), 403
        
        # Statistiche base
        total_pods = POD.query.count()
        active_pods = POD.query.filter_by(is_active=True).count()
        inactive_pods = total_pods - active_pods
        
        # Statistiche per tipo
        electricity_pods = POD.query.filter_by(pod_type=PodType.ELECTRICITY, is_active=True).count()
        gas_pods = POD.query.filter_by(pod_type=PodType.GAS, is_active=True).count()
        water_pods = POD.query.filter_by(pod_type=PodType.WATER, is_active=True).count()
        heating_pods = POD.query.filter_by(pod_type=PodType.HEATING, is_active=True).count()
        
        # Top fornitori
        supplier_stats = db.session.query(
            POD.supplier,
            func.count(POD.id).label('count')
        ).filter(
            POD.is_active == True,
            POD.supplier.isnot(None)
        ).group_by(POD.supplier).order_by(func.count(POD.id).desc()).limit(10).all()
        
        top_suppliers = [
            {'supplier': stat.supplier, 'count': stat.count} 
            for stat in supplier_stats
        ]
        
        # Statistiche connessioni
        pods_with_properties = db.session.query(func.count(func.distinct(PropertyPod.pod_id))).filter(
            PropertyPod.is_active == True
        ).scalar() or 0
        
        pods_without_properties = active_pods - pods_with_properties
        
        # Media proprietà per POD
        total_connections = PropertyPod.query.filter_by(is_active=True).count()
        avg_properties_per_pod = round(total_connections / max(active_pods, 1), 2)
        
        stats = {
            'total_pods': total_pods,
            'active_pods': active_pods,
            'inactive_pods': inactive_pods,
            'electricity_pods': electricity_pods,
            'gas_pods': gas_pods,
            'water_pods': water_pods,
            'heating_pods': heating_pods,
            'top_suppliers': top_suppliers,
            'pods_with_properties': pods_with_properties,
            'pods_without_properties': pods_without_properties,
            'avg_properties_per_pod': avg_properties_per_pod
        }
        
        return jsonify({
            'success': True,
            'message': 'Statistiche POD recuperate con successo',
            'data': stats
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Errore nel recupero statistiche POD: {str(e)}'}), 500


@api_v1_bp.route('/pods/bulk-actions', methods=['POST'])
@jwt_required()
def bulk_actions():
    """
    Esegue azioni in massa sui POD.
    Solo Rohirrim e Lord possono eseguire azioni bulk.
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_manage_pods(current_user):
            return jsonify({'error': 'Non autorizzato a eseguire azioni bulk sui POD'}), 403
        
        # Validazione dati
        try:
            data = pod_bulk_action_schema.load(request.get_json())
        except ValidationError as err:
            return jsonify({'error': 'Dati non validi', 'details': err.messages}), 400
        
        action = data['action']
        pod_ids = data['pod_ids']
        
        # Recupera i POD
        pods = POD.query.filter(POD.id.in_(pod_ids)).all()
        if len(pods) != len(pod_ids):
            found_ids = {pod.id for pod in pods}
            missing_ids = set(pod_ids) - found_ids
            return jsonify({'error': f'POD non trovati: {list(missing_ids)}'}), 404
        
        results = []
        
        if action == 'activate':
            for pod in pods:
                pod.activate()
                results.append({'id': pod.id, 'pod_code': pod.pod_code, 'status': 'activated'})
                
        elif action == 'deactivate':
            for pod in pods:
                pod.deactivate()
                results.append({'id': pod.id, 'pod_code': pod.pod_code, 'status': 'deactivated'})
                
        elif action == 'delete':
            # Controllo connessioni attive per tutti i POD
            pods_with_connections = []
            for pod in pods:
                active_connections = PropertyPod.query.filter_by(
                    pod_id=pod.id, 
                    is_active=True
                ).count()
                if active_connections > 0:
                    pods_with_connections.append(f"{pod.pod_code} ({active_connections} connessioni)")
            
            if pods_with_connections:
                return jsonify({
                    'error': f'Impossibile eliminare POD con connessioni attive: {", ".join(pods_with_connections)}'
                }), 400
            
            for pod in pods:
                pod.is_active = False
                results.append({'id': pod.id, 'pod_code': pod.pod_code, 'status': 'deleted'})
                
        elif action == 'update_supplier':
            supplier = data.get('supplier')
            if not supplier:
                return jsonify({'error': 'Fornitore richiesto per l\'azione update_supplier'}), 400
            
            for pod in pods:
                pod.supplier = supplier
                results.append({'id': pod.id, 'pod_code': pod.pod_code, 'status': 'supplier_updated'})
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Azione "{action}" eseguita su {len(results)} POD',
            'data': {
                'action': action,
                'processed_count': len(results),
                'results': results
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Errore nell\'esecuzione azione bulk: {str(e)}'}), 500


@api_v1_bp.route('/pods/check-duplicate', methods=['POST'])
@jwt_required()
def check_duplicate():
    """
    Controlla se un codice POD è già in uso.
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_manage_pods(current_user):
            return jsonify({'error': 'Non autorizzato a verificare duplicati POD'}), 403
        
        # Validazione dati
        try:
            data = pod_duplicate_check_schema.load(request.get_json())
        except ValidationError as err:
            return jsonify({'error': 'Dati non validi', 'details': err.messages}), 400
        
        pod_code = data['pod_code']
        exclude_id = data.get('exclude_id')
        
        query = POD.query.filter_by(pod_code=pod_code)
        if exclude_id:
            query = query.filter(POD.id != exclude_id)
        
        duplicate = query.first()
        
        result = {
            'is_duplicate': duplicate is not None,
            'existing_pod': None
        }
        
        if duplicate:
            result['existing_pod'] = {
                'id': duplicate.id,
                'pod_code': duplicate.pod_code,
                'pod_type': duplicate.pod_type.value,
                'supplier': duplicate.supplier
            }
        
        return jsonify({
            'success': True,
            'message': 'Controllo duplicati completato',
            'data': result
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Errore nel controllo duplicati: {str(e)}'}), 500


@api_v1_bp.route('/pods/validate', methods=['POST'])
@jwt_required()
def validate_pod_data():
    """
    Valida i dati di un POD senza salvare.
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_manage_pods(current_user):
            return jsonify({'error': 'Non autorizzato a validare dati POD'}), 403
        
        # Validazione dati
        try:
            data = pod_validation_schema.load(request.get_json())
        except ValidationError as err:
            return jsonify({'error': 'Dati non validi', 'details': err.messages}), 400
        
        validations = []
        
        # Controllo formato codice POD
        pod_code = data['pod_code']
        pod_type = data['pod_type']
        
        # Validazione formato elettrico
        if pod_type == PodType.ELECTRICITY.value:
            if not (pod_code.startswith('IT001E') and len(pod_code) == 14 and pod_code[6:].isdigit()):
                validations.append({
                    'field': 'pod_code',
                    'status': 'warning',
                    'message': 'Formato POD elettrico non standard (dovrebbe essere IT001E + 8 cifre)'
                })
            else:
                validations.append({
                    'field': 'pod_code',
                    'status': 'valid',
                    'message': 'Formato POD elettrico valido'
                })
        
        # Validazione formato gas
        elif pod_type == PodType.GAS.value:
            if not (pod_code.startswith('IT') and len(pod_code) >= 12):
                validations.append({
                    'field': 'pod_code',
                    'status': 'warning',
                    'message': 'Formato POD gas non standard (dovrebbe iniziare con IT e avere almeno 12 caratteri)'
                })
            else:
                validations.append({
                    'field': 'pod_code',
                    'status': 'valid',
                    'message': 'Formato POD gas valido'
                })
        
        # Controllo duplicati
        existing = POD.query.filter_by(pod_code=pod_code).first()
        if existing:
            validations.append({
                'field': 'pod_code',
                'status': 'error',
                'message': f'Codice POD già esistente (ID: {existing.id})'
            })
        else:
            validations.append({
                'field': 'pod_code',
                'status': 'valid',
                'message': 'Codice POD disponibile'
            })
        
        # Controllo fornitore suggerito
        supplier = data.get('supplier')
        if supplier:
            # Suggerimenti basati su pattern comuni
            supplier_lower = supplier.lower()
            suggestions = []
            
            if 'enel' in supplier_lower and pod_type == PodType.ELECTRICITY.value:
                suggestions.append('Fornitore coerente con tipo POD elettrico')
            elif 'eni' in supplier_lower and pod_type == PodType.GAS.value:
                suggestions.append('Fornitore coerente con tipo POD gas')
            elif pod_type == PodType.ELECTRICITY.value and 'gas' in supplier_lower:
                suggestions.append('Attenzione: fornitore sembra gas ma POD è elettrico')
            elif pod_type == PodType.GAS.value and 'enel' in supplier_lower:
                suggestions.append('Attenzione: fornitore sembra elettrico ma POD è gas')
            
            if suggestions:
                validations.append({
                    'field': 'supplier',
                    'status': 'info',
                    'message': '; '.join(suggestions)
                })
        
        is_valid = all(v['status'] != 'error' for v in validations)
        
        return jsonify({
            'success': True,
            'message': 'Validazione completata',
            'data': {
                'is_valid': is_valid,
                'validations': validations
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Errore nella validazione: {str(e)}'}), 500


@api_v1_bp.route('/pods/types', methods=['GET'])
@jwt_required()
def get_pod_types():
    """
    Ottiene i tipi di POD disponibili.
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_view_pods(current_user):
            return jsonify({'error': 'Non autorizzato a visualizzare tipi POD'}), 403
        
        types = [
            {
                'value': pod_type.value,
                'label': pod_type.value.title(),
                'description': {
                    'ELECTRICITY': 'POD per energia elettrica (ENEL)',
                    'GAS': 'POD per gas naturale',
                    'WATER': 'POD per acqua (futuro)',
                    'HEATING': 'POD per riscaldamento (futuro)'
                }.get(pod_type.value, 'Tipo POD')
            }
            for pod_type in PodType
        ]
        
        return jsonify({
            'success': True,
            'message': 'Tipi POD recuperati con successo',
            'data': {
                'types': types,
                'total_types': len(types)
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Errore nel recupero tipi POD: {str(e)}'}), 500
