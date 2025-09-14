# PropertyPod CRUD API - Sistema Completo

from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_current_user
from sqlalchemy import or_, func, text, and_
from sqlalchemy.exc import IntegrityError
from datetime import date, datetime, timedelta
from ...models.property_pod import PropertyPod
from ...models.property_unit import PropertyUnit
from ...models.pod import POD, PodType
from ...schemas import (
    property_pod_schema, property_pods_schema,
    property_pod_create_schema, property_pod_update_schema,
    property_pod_list_schema, property_pod_stats_schema,
    property_pod_duplicate_check_schema, property_pod_bulk_action_schema,
    property_pod_validation_schema, property_pod_by_property_schema,
    property_pod_by_pod_schema, property_pod_primary_schema
)
from ...extensions import db
from marshmallow import ValidationError
from . import api_v1_bp


def user_can_manage_property_pods(user):
    """Verifica se l'utente può gestire le connessioni PropertyPod (solo Rohirrim e Lord)."""
    return user and user.is_active and user.role and (user.role.is_rohirrim() or user.role.is_lord())


def user_can_view_property_pods(user):
    """Verifica se l'utente può visualizzare le connessioni PropertyPod."""
    if not user or not user.is_active:
        return False
    
    # Rohirrim, Lord e Dunedain possono tutti visualizzare le connessioni
    if user.role and (user.role.is_rohirrim() or user.role.is_lord() or user.role.is_dunedain()):
        return True
    
    return False


@api_v1_bp.route('/property-pods', methods=['GET'])
@jwt_required()
def get_property_pods():
    """
    Ottiene la lista delle connessioni PropertyPod con filtri.
    Tutti i ruoli possono visualizzare le connessioni.
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_view_property_pods(current_user):
            return jsonify({'error': 'Non autorizzato a visualizzare le connessioni PropertyPod'}), 403
        
        # Parametri di paginazione e filtri
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        
        # Filtri
        property_unit_id = request.args.get('property_unit_id', type=int)
        pod_id = request.args.get('pod_id', type=int)
        pod_type = request.args.get('pod_type', '').strip()
        is_primary = request.args.get('is_primary', '').strip()
        is_active = request.args.get('is_active', '').strip()
        search = request.args.get('search', '').strip()
        
        # Ordinamento
        sort_by = request.args.get('sort_by', 'created_at')
        sort_order = request.args.get('sort_order', 'desc')
        
        # Query base con join per ottimizzare
        query = PropertyPod.query.join(PropertyUnit).join(POD)
        
        # Applicazione filtri
        if property_unit_id:
            query = query.filter(PropertyPod.property_unit_id == property_unit_id)
            
        if pod_id:
            query = query.filter(PropertyPod.pod_id == pod_id)
            
        if pod_type:
            try:
                pod_type_enum = PodType(pod_type.upper())
                query = query.filter(POD.pod_type == pod_type_enum)
            except ValueError:
                return jsonify({'error': f'Tipo POD non valido: {pod_type}'}), 400
            
        if is_primary.lower() in ['true', 'false']:
            query = query.filter(PropertyPod.is_primary == (is_primary.lower() == 'true'))
            
        if is_active.lower() in ['true', 'false']:
            query = query.filter(PropertyPod.is_active == (is_active.lower() == 'true'))
            
        # Ricerca testuale
        if search:
            search_term = f'%{search}%'
            query = query.filter(or_(
                PropertyUnit.name.ilike(search_term),
                PropertyUnit.code.ilike(search_term),
                PropertyUnit.address.ilike(search_term),
                POD.pod_code.ilike(search_term),
                POD.supplier.ilike(search_term),
                PropertyPod.notes.ilike(search_term)
            ))
        
        # Ordinamento
        if hasattr(PropertyPod, sort_by):
            sort_field = getattr(PropertyPod, sort_by)
            if sort_order.lower() == 'desc':
                sort_field = sort_field.desc()
            query = query.order_by(sort_field)
        else:
            query = query.order_by(PropertyPod.created_at.desc())
        
        # Paginazione
        pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        property_pods = pagination.items
        
        # Aggiungi info aggiuntive per ogni connessione
        pod_data = []
        for pp in property_pods:
            pp_dict = property_pod_schema.dump(pp)
            pod_data.append(pp_dict)
        
        result = {
            'property_pods': pod_data,
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
            'message': 'Lista connessioni PropertyPod recuperata con successo',
            'data': result
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Errore nel recupero connessioni: {str(e)}'}), 500


@api_v1_bp.route('/property-pods', methods=['POST'])
@jwt_required()
def create_property_pod():
    """
    Crea una nuova connessione PropertyPod.
    Solo Rohirrim e Lord possono creare connessioni.
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_manage_property_pods(current_user):
            return jsonify({'error': 'Non autorizzato a creare connessioni PropertyPod'}), 403
        
        # Validazione dati
        try:
            data = property_pod_create_schema.load(request.get_json())
        except ValidationError as err:
            return jsonify({'error': 'Dati non validi', 'details': err.messages}), 400
        
        # Verifica che PropertyUnit esista
        property_unit = PropertyUnit.query.filter_by(id=data['property_unit_id']).first()
        if not property_unit:
            return jsonify({'error': f'PropertyUnit con ID {data["property_unit_id"]} non trovata'}), 404
        
        # Verifica che POD esista
        pod = POD.query.filter_by(id=data['pod_id']).first()
        if not pod:
            return jsonify({'error': f'POD con ID {data["pod_id"]} non trovato'}), 404
        
        # Controllo duplicati: stessa property e stesso POD
        existing_connection = PropertyPod.query.filter_by(
            property_unit_id=data['property_unit_id'],
            pod_id=data['pod_id']
        ).first()
        
        if existing_connection:
            return jsonify({
                'error': f'Connessione già esistente tra PropertyUnit {data["property_unit_id"]} e POD {data["pod_id"]}'
            }), 400
        
        # Se è una connessione primaria, disattiva altre connessioni primarie dello stesso tipo
        if data.get('is_primary', False):
            existing_primary = PropertyPod.query.join(POD).filter(
                PropertyPod.property_unit_id == data['property_unit_id'],
                PropertyPod.is_primary == True,
                PropertyPod.is_active == True,
                POD.pod_type == pod.pod_type
            ).first()
            
            if existing_primary:
                existing_primary.is_primary = False
        
        # Creazione della connessione
        property_pod = PropertyPod(**data)
        db.session.add(property_pod)
        db.session.commit()
        
        # Ricarica con relazioni
        property_pod = PropertyPod.query.options(
            db.joinedload(PropertyPod.property_unit),
            db.joinedload(PropertyPod.pod)
        ).filter_by(id=property_pod.id).first()
        
        # Preparazione risposta
        pp_dict = property_pod_schema.dump(property_pod)
        
        return jsonify({
            'success': True,
            'message': 'Connessione PropertyPod creata con successo',
            'data': pp_dict
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Errore nella creazione connessione: {str(e)}'}), 500


@api_v1_bp.route('/property-pods/<int:property_pod_id>', methods=['GET'])
@jwt_required()
def get_property_pod(property_pod_id):
    """
    Ottiene i dettagli di una connessione PropertyPod specifica.
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_view_property_pods(current_user):
            return jsonify({'error': 'Non autorizzato a visualizzare le connessioni PropertyPod'}), 403
        
        property_pod = PropertyPod.query.options(
            db.joinedload(PropertyPod.property_unit),
            db.joinedload(PropertyPod.pod)
        ).filter_by(id=property_pod_id).first()
        
        if not property_pod:
            return jsonify({'error': f'Connessione PropertyPod con ID {property_pod_id} non trovata'}), 404
        
        # Preparazione risposta
        pp_dict = property_pod_schema.dump(property_pod)
        
        return jsonify({
            'success': True,
            'message': 'Dettagli connessione PropertyPod recuperati con successo',
            'data': pp_dict
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Errore nel recupero connessione: {str(e)}'}), 500


@api_v1_bp.route('/property-pods/<int:property_pod_id>', methods=['PUT'])
@jwt_required()
def update_property_pod(property_pod_id):
    """
    Aggiorna una connessione PropertyPod esistente.
    Solo Rohirrim e Lord possono aggiornare connessioni.
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_manage_property_pods(current_user):
            return jsonify({'error': 'Non autorizzato a modificare connessioni PropertyPod'}), 403
        
        property_pod = PropertyPod.query.filter_by(id=property_pod_id).first()
        if not property_pod:
            return jsonify({'error': f'Connessione PropertyPod con ID {property_pod_id} non trovata'}), 404
        
        # Validazione dati
        try:
            data = property_pod_update_schema.load(request.get_json())
        except ValidationError as err:
            return jsonify({'error': 'Dati non validi', 'details': err.messages}), 400
        
        # Verifica esistenza entità se cambiate
        if 'property_unit_id' in data:
            property_unit = PropertyUnit.query.filter_by(id=data['property_unit_id']).first()
            if not property_unit:
                return jsonify({'error': f'PropertyUnit con ID {data["property_unit_id"]} non trovata'}), 404
        
        if 'pod_id' in data:
            pod = POD.query.filter_by(id=data['pod_id']).first()
            if not pod:
                return jsonify({'error': f'POD con ID {data["pod_id"]} non trovato'}), 404
        
        # Controllo duplicati se si cambiano property_unit_id o pod_id
        if 'property_unit_id' in data or 'pod_id' in data:
            new_property_id = data.get('property_unit_id', property_pod.property_unit_id)
            new_pod_id = data.get('pod_id', property_pod.pod_id)
            
            existing_connection = PropertyPod.query.filter(
                PropertyPod.property_unit_id == new_property_id,
                PropertyPod.pod_id == new_pod_id,
                PropertyPod.id != property_pod_id
            ).first()
            
            if existing_connection:
                return jsonify({
                    'error': f'Connessione già esistente tra PropertyUnit {new_property_id} e POD {new_pod_id}'
                }), 400
        
        # Se si imposta come primaria, disattiva altre connessioni primarie dello stesso tipo
        if data.get('is_primary', False) and not property_pod.is_primary:
            pod_for_check = property_pod.pod
            if 'pod_id' in data:
                pod_for_check = POD.query.filter_by(id=data['pod_id']).first()
            
            if pod_for_check:
                property_id_for_check = data.get('property_unit_id', property_pod.property_unit_id)
                existing_primary = PropertyPod.query.join(POD).filter(
                    PropertyPod.property_unit_id == property_id_for_check,
                    PropertyPod.is_primary == True,
                    PropertyPod.is_active == True,
                    PropertyPod.id != property_pod_id,
                    POD.pod_type == pod_for_check.pod_type
                ).first()
                
                if existing_primary:
                    existing_primary.is_primary = False
        
        # Aggiornamento campi
        for field, value in data.items():
            if hasattr(property_pod, field):
                setattr(property_pod, field, value)
        
        db.session.commit()
        
        # Ricarica con relazioni
        property_pod = PropertyPod.query.options(
            db.joinedload(PropertyPod.property_unit),
            db.joinedload(PropertyPod.pod)
        ).filter_by(id=property_pod_id).first()
        
        # Preparazione risposta
        pp_dict = property_pod_schema.dump(property_pod)
        
        return jsonify({
            'success': True,
            'message': 'Connessione PropertyPod aggiornata con successo',
            'data': pp_dict
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Errore nell\'aggiornamento connessione: {str(e)}'}), 500


@api_v1_bp.route('/property-pods/<int:property_pod_id>', methods=['DELETE'])
@jwt_required()
def delete_property_pod(property_pod_id):
    """
    Elimina una connessione PropertyPod.
    Solo Rohirrim e Lord possono eliminare connessioni.
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_manage_property_pods(current_user):
            return jsonify({'error': 'Non autorizzato a eliminare connessioni PropertyPod'}), 403
        
        property_pod = PropertyPod.query.filter_by(id=property_pod_id).first()
        if not property_pod:
            return jsonify({'error': f'Connessione PropertyPod con ID {property_pod_id} non trovata'}), 404
        
        # Eliminazione fisica (non soft delete per le relazioni)
        db.session.delete(property_pod)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Connessione PropertyPod eliminata con successo',
            'data': {}
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Errore nell\'eliminazione connessione: {str(e)}'}), 500


@api_v1_bp.route('/property-pods/stats', methods=['GET'])
@jwt_required()
def get_property_pod_stats():
    """
    Ottiene statistiche dettagliate sulle connessioni PropertyPod.
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_view_property_pods(current_user):
            return jsonify({'error': 'Non autorizzato a visualizzare statistiche connessioni'}), 403
        
        # Statistiche base
        total_connections = PropertyPod.query.count()
        active_connections = PropertyPod.query.filter_by(is_active=True).count()
        inactive_connections = total_connections - active_connections
        primary_connections = PropertyPod.query.filter_by(is_primary=True, is_active=True).count()
        
        # Statistiche per tipo POD
        connections_by_type = db.session.query(
            POD.pod_type,
            func.count(PropertyPod.id).label('count')
        ).join(PropertyPod).filter(
            PropertyPod.is_active == True
        ).group_by(POD.pod_type).all()
        
        connections_by_pod_type = {
            stat.pod_type.value: stat.count 
            for stat in connections_by_type
        }
        
        # Statistiche PropertyUnit
        properties_with_pods = db.session.query(
            func.count(func.distinct(PropertyPod.property_unit_id))
        ).filter(PropertyPod.is_active == True).scalar() or 0
        
        total_properties = PropertyUnit.query.filter_by(is_active=True).count()
        properties_without_pods = max(0, total_properties - properties_with_pods)
        
        # Media POD per property
        if properties_with_pods > 0:
            avg_pods_per_property = round(active_connections / properties_with_pods, 2)
        else:
            avg_pods_per_property = 0.0
        
        # Statistiche POD
        pods_with_properties = db.session.query(
            func.count(func.distinct(PropertyPod.pod_id))
        ).filter(PropertyPod.is_active == True).scalar() or 0
        
        total_pods = POD.query.filter_by(is_active=True).count()
        pods_without_properties = max(0, total_pods - pods_with_properties)
        
        # Media properties per POD
        if pods_with_properties > 0:
            avg_properties_per_pod = round(active_connections / pods_with_properties, 2)
        else:
            avg_properties_per_pod = 0.0
        
        # Top properties per numero di POD
        top_properties = db.session.query(
            PropertyUnit.id,
            PropertyUnit.name,
            PropertyUnit.code,
            func.count(PropertyPod.id).label('pod_count')
        ).join(PropertyPod).filter(
            PropertyPod.is_active == True
        ).group_by(
            PropertyUnit.id, PropertyUnit.name, PropertyUnit.code
        ).order_by(func.count(PropertyPod.id).desc()).limit(5).all()
        
        top_properties_by_pods = [
            {
                'property_id': prop.id,
                'property_name': prop.name,
                'property_code': prop.code,
                'pod_count': prop.pod_count
            }
            for prop in top_properties
        ]
        
        # Top POD per numero di properties
        top_pods = db.session.query(
            POD.id,
            POD.pod_code,
            POD.pod_type,
            func.count(PropertyPod.id).label('property_count')
        ).join(PropertyPod).filter(
            PropertyPod.is_active == True
        ).group_by(
            POD.id, POD.pod_code, POD.pod_type
        ).order_by(func.count(PropertyPod.id).desc()).limit(5).all()
        
        top_pods_by_properties = [
            {
                'pod_id': pod.id,
                'pod_code': pod.pod_code,
                'pod_type': pod.pod_type.value,
                'property_count': pod.property_count
            }
            for pod in top_pods
        ]
        
        stats = {
            'total_connections': total_connections,
            'active_connections': active_connections,
            'inactive_connections': inactive_connections,
            'primary_connections': primary_connections,
            'connections_by_pod_type': connections_by_pod_type,
            'properties_with_pods': properties_with_pods,
            'properties_without_pods': properties_without_pods,
            'avg_pods_per_property': avg_pods_per_property,
            'pods_with_properties': pods_with_properties,
            'pods_without_properties': pods_without_properties,
            'avg_properties_per_pod': avg_properties_per_pod,
            'top_properties_by_pods': top_properties_by_pods,
            'top_pods_by_properties': top_pods_by_properties
        }
        
        return jsonify({
            'success': True,
            'message': 'Statistiche connessioni PropertyPod recuperate con successo',
            'data': stats
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Errore nel recupero statistiche: {str(e)}'}), 500


@api_v1_bp.route('/property-pods/bulk-actions', methods=['POST'])
@jwt_required()
def property_pod_bulk_actions():
    """
    Esegue azioni in massa sulle connessioni PropertyPod.
    Solo Rohirrim e Lord possono eseguire azioni bulk.
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_manage_property_pods(current_user):
            return jsonify({'error': 'Non autorizzato a eseguire azioni bulk sulle connessioni'}), 403
        
        # Validazione dati
        try:
            data = property_pod_bulk_action_schema.load(request.get_json())
        except ValidationError as err:
            return jsonify({'error': 'Dati non validi', 'details': err.messages}), 400
        
        action = data['action']
        property_pod_ids = data['property_pod_ids']
        
        # Recupera le connessioni
        property_pods = PropertyPod.query.filter(PropertyPod.id.in_(property_pod_ids)).all()
        if len(property_pods) != len(property_pod_ids):
            found_ids = {pp.id for pp in property_pods}
            missing_ids = set(property_pod_ids) - found_ids
            return jsonify({'error': f'Connessioni non trovate: {list(missing_ids)}'}), 404
        
        results = []
        
        if action == 'activate':
            for pp in property_pods:
                pp.is_active = True
                results.append({'id': pp.id, 'status': 'activated'})
                
        elif action == 'deactivate':
            for pp in property_pods:
                pp.is_active = False
                pp.is_primary = False  # Disattiva anche primary se si disattiva
                results.append({'id': pp.id, 'status': 'deactivated'})
                
        elif action == 'delete':
            for pp in property_pods:
                results.append({'id': pp.id, 'status': 'deleted'})
                db.session.delete(pp)
                
        elif action == 'set_primary':
            # Raggruppa per property_unit_id e pod_type per gestire i primary
            property_pod_groups = {}
            for pp in property_pods:
                if pp.pod and pp.property_unit_id:
                    key = (pp.property_unit_id, pp.pod.pod_type.value)
                    if key not in property_pod_groups:
                        property_pod_groups[key] = []
                    property_pod_groups[key].append(pp)
            
            for (property_id, pod_type), group_pods in property_pod_groups.items():
                # Disattiva tutti i primary esistenti per questa property e tipo POD
                existing_primaries = PropertyPod.query.join(POD).filter(
                    PropertyPod.property_unit_id == property_id,
                    PropertyPod.is_primary == True,
                    PropertyPod.is_active == True,
                    POD.pod_type == PodType(pod_type),
                    PropertyPod.id.notin_([pp.id for pp in group_pods])
                ).all()
                
                for existing in existing_primaries:
                    existing.is_primary = False
                
                # Imposta come primary solo il primo del gruppo
                if group_pods:
                    group_pods[0].is_primary = True
                    group_pods[0].is_active = True
                    results.append({'id': group_pods[0].id, 'status': 'set_as_primary'})
                    
                    # Gli altri del gruppo vengono attivati ma non primary
                    for pp in group_pods[1:]:
                        pp.is_primary = False
                        pp.is_active = True
                        results.append({'id': pp.id, 'status': 'activated_not_primary'})
                        
        elif action == 'unset_primary':
            for pp in property_pods:
                pp.is_primary = False
                results.append({'id': pp.id, 'status': 'unset_primary'})
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Azione "{action}" eseguita su {len(results)} connessioni',
            'data': {
                'action': action,
                'processed_count': len(results),
                'results': results
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Errore nell\'esecuzione azione bulk: {str(e)}'}), 500


@api_v1_bp.route('/property-pods/check-duplicate', methods=['POST'])
@jwt_required()
def check_property_pod_duplicate():
    """
    Controlla se una connessione PropertyPod è già esistente.
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_manage_property_pods(current_user):
            return jsonify({'error': 'Non autorizzato a verificare duplicati connessioni'}), 403
        
        # Validazione dati
        try:
            data = property_pod_duplicate_check_schema.load(request.get_json())
        except ValidationError as err:
            return jsonify({'error': 'Dati non validi', 'details': err.messages}), 400
        
        property_unit_id = data['property_unit_id']
        pod_id = data['pod_id']
        exclude_id = data.get('exclude_id')
        
        query = PropertyPod.query.filter_by(
            property_unit_id=property_unit_id,
            pod_id=pod_id
        )
        
        if exclude_id:
            query = query.filter(PropertyPod.id != exclude_id)
        
        duplicate = query.first()
        
        result = {
            'is_duplicate': duplicate is not None,
            'existing_connection': None
        }
        
        if duplicate:
            result['existing_connection'] = {
                'id': duplicate.id,
                'property_unit_id': duplicate.property_unit_id,
                'pod_id': duplicate.pod_id,
                'is_primary': duplicate.is_primary,
                'is_active': duplicate.is_active,
                'created_at': duplicate.created_at.strftime('%Y-%m-%d %H:%M:%S') if duplicate.created_at else None
            }
        
        return jsonify({
            'success': True,
            'message': 'Controllo duplicati completato',
            'data': result
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Errore nel controllo duplicati: {str(e)}'}), 500


@api_v1_bp.route('/property-pods/by-property/<int:property_unit_id>', methods=['GET'])
@jwt_required()
def get_connections_by_property(property_unit_id):
    """
    Ottiene tutte le connessioni POD per una PropertyUnit specifica.
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_view_property_pods(current_user):
            return jsonify({'error': 'Non autorizzato a visualizzare connessioni'}), 403
        
        # Verifica che PropertyUnit esista
        property_unit = PropertyUnit.query.filter_by(id=property_unit_id).first()
        if not property_unit:
            return jsonify({'error': f'PropertyUnit con ID {property_unit_id} non trovata'}), 404
        
        include_inactive = request.args.get('include_inactive', 'false').lower() == 'true'
        
        # Query connessioni
        query = PropertyPod.query.options(
            db.joinedload(PropertyPod.pod)
        ).filter_by(property_unit_id=property_unit_id)
        
        if not include_inactive:
            query = query.filter_by(is_active=True)
        
        query = query.order_by(PropertyPod.is_primary.desc(), PropertyPod.created_at.desc())
        
        property_pods = query.all()
        
        # Serializzazione
        connections_data = []
        for pp in property_pods:
            pp_dict = property_pod_schema.dump(pp)
            connections_data.append(pp_dict)
        
        return jsonify({
            'success': True,
            'message': f'Connessioni POD per PropertyUnit {property_unit_id} recuperate con successo',
            'data': {
                'property_unit_id': property_unit_id,
                'property_unit_name': property_unit.name,
                'property_unit_code': property_unit.code,
                'connections': connections_data,
                'total_connections': len(connections_data),
                'active_connections': len([c for c in connections_data if c.get('is_active', False)]),
                'primary_connections': len([c for c in connections_data if c.get('is_primary', False)])
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Errore nel recupero connessioni per property: {str(e)}'}), 500


@api_v1_bp.route('/property-pods/by-pod/<int:pod_id>', methods=['GET'])
@jwt_required()
def get_connections_by_pod(pod_id):
    """
    Ottiene tutte le connessioni PropertyUnit per un POD specifico.
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_view_property_pods(current_user):
            return jsonify({'error': 'Non autorizzato a visualizzare connessioni'}), 403
        
        # Verifica che POD esista
        pod = POD.query.filter_by(id=pod_id).first()
        if not pod:
            return jsonify({'error': f'POD con ID {pod_id} non trovato'}), 404
        
        include_inactive = request.args.get('include_inactive', 'false').lower() == 'true'
        
        # Query connessioni
        query = PropertyPod.query.options(
            db.joinedload(PropertyPod.property_unit)
        ).filter_by(pod_id=pod_id)
        
        if not include_inactive:
            query = query.filter_by(is_active=True)
        
        query = query.order_by(PropertyPod.is_primary.desc(), PropertyPod.created_at.desc())
        
        property_pods = query.all()
        
        # Serializzazione
        connections_data = []
        for pp in property_pods:
            pp_dict = property_pod_schema.dump(pp)
            connections_data.append(pp_dict)
        
        return jsonify({
            'success': True,
            'message': f'Connessioni PropertyUnit per POD {pod_id} recuperate con successo',
            'data': {
                'pod_id': pod_id,
                'pod_code': pod.pod_code,
                'pod_type': pod.pod_type.value,
                'connections': connections_data,
                'total_connections': len(connections_data),
                'active_connections': len([c for c in connections_data if c.get('is_active', False)]),
                'primary_connections': len([c for c in connections_data if c.get('is_primary', False)])
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Errore nel recupero connessioni per POD: {str(e)}'}), 500


@api_v1_bp.route('/property-pods/<int:property_pod_id>/primary', methods=['PATCH'])
@jwt_required()
def set_primary_connection(property_pod_id):
    """
    Imposta o rimuove una connessione come primaria per il suo tipo POD.
    Solo Rohirrim e Lord possono modificare connessioni primarie.
    """
    try:
        current_user = get_current_user()
        
        # Verifica autorizzazioni
        if not user_can_manage_property_pods(current_user):
            return jsonify({'error': 'Non autorizzato a modificare connessioni primarie'}), 403
        
        property_pod = PropertyPod.query.options(
            db.joinedload(PropertyPod.pod)
        ).filter_by(id=property_pod_id).first()
        
        if not property_pod:
            return jsonify({'error': f'Connessione PropertyPod con ID {property_pod_id} non trovata'}), 404
        
        # Validazione dati
        try:
            data = property_pod_primary_schema.load(request.get_json())
        except ValidationError as err:
            return jsonify({'error': 'Dati non validi', 'details': err.messages}), 400
        
        is_primary = data['is_primary']
        
        if is_primary:
            # Se si imposta come primaria, disattiva altre connessioni primarie dello stesso tipo
            if property_pod.pod:
                existing_primaries = PropertyPod.query.join(POD).filter(
                    PropertyPod.property_unit_id == property_pod.property_unit_id,
                    PropertyPod.is_primary == True,
                    PropertyPod.is_active == True,
                    PropertyPod.id != property_pod_id,
                    POD.pod_type == property_pod.pod.pod_type
                ).all()
                
                for existing in existing_primaries:
                    existing.is_primary = False
            
            # Attiva automaticamente la connessione se si imposta come primaria
            property_pod.is_primary = True
            property_pod.is_active = True
            message = 'Connessione impostata come primaria con successo'
        else:
            property_pod.is_primary = False
            message = 'Connessione rimossa da primaria con successo'
        
        db.session.commit()
        
        # Ricarica con relazioni
        property_pod = PropertyPod.query.options(
            db.joinedload(PropertyPod.property_unit),
            db.joinedload(PropertyPod.pod)
        ).filter_by(id=property_pod_id).first()
        
        # Preparazione risposta
        pp_dict = property_pod_schema.dump(property_pod)
        
        return jsonify({
            'success': True,
            'message': message,
            'data': pp_dict
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Errore nella modifica connessione primaria: {str(e)}'}), 500
