"""
API endpoints per la gestione delle prenotazioni (Booking)
"""

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import and_, or_, func, extract
from sqlalchemy.orm import joinedload
from datetime import datetime, date, timedelta

from ...models.booking import Booking
from ...models.property_unit import PropertyUnit
from ...schemas.booking import (
    BookingCreateSchema, BookingUpdateSchema, BookingResponseSchema,
    BookingListSchema, BookingSearchSchema, BookingStatsSchema,
    BookingBulkActionSchema, BookingDuplicateCheckSchema, BookingValidationSchema,
    BookingByPropertySchema, BookingByDateRangeSchema, BookingSummarySchema,
    BookingStatus
)
from ...schemas import (
    booking_create_schema, booking_update_schema, booking_schema, bookings_schema,
    booking_list_schema, booking_search_schema, booking_stats_schema,
    booking_bulk_action_schema, booking_duplicate_check_schema, booking_validation_schema,
    booking_by_property_schema, booking_by_date_range_schema, booking_summary_schema
)
from ...utils.auth import require_role
from ...extensions import db
from . import api_v1_bp

# Utilizziamo direttamente api_v1_bp per registrare le route


@api_v1_bp.route('/bookings', methods=['GET'])
@jwt_required()
@require_role(['Rohirrim', 'Lord', 'Dunedain'])
def get_bookings():
    """
    Ottieni lista prenotazioni con filtri avanzati
    
    Parametri di query supportati:
    - booking_name: Nome prenotazione (ricerca parziale)
    - crm_reference_id: ID riferimento CRM
    - property_unit_id: ID unità immobiliare
    - booking_status: Stato prenotazione
    - is_active: Prenotazioni attive/disattive
    - arrival_date_from/arrival_date_to: Range data arrivo
    - departure_date_from/departure_date_to: Range data partenza
    - guest_count_min/guest_count_max: Range numero ospiti
    - schedine_not_sent: Prenotazioni senza schedine
    - alloggiati_web_not_sent: Prenotazioni senza alloggiati web
    - page/per_page: Paginazione
    - sort_by/sort_order: Ordinamento
    """
    try:
        # Validazione parametri di ricerca
        search_data = booking_search_schema.load(request.args.to_dict())
        
        # Query base con join ottimizzato
        query = Booking.query.options(
            joinedload(Booking.property_unit).joinedload(PropertyUnit.property_type)
        )
        
        # Applicazione filtri
        if search_data.get('booking_name'):
            query = query.filter(Booking.booking_name.ilike(f"%{search_data['booking_name']}%"))
        
        if search_data.get('crm_reference_id'):
            query = query.filter(Booking.crm_reference_id == search_data['crm_reference_id'])
        
        if search_data.get('property_unit_id'):
            query = query.filter(Booking.property_unit_id == search_data['property_unit_id'])
        
        if search_data.get('booking_status'):
            query = query.filter(Booking.booking_status == search_data['booking_status'].value)
        
        if search_data.get('is_active') is not None:
            query = query.filter(Booking.is_active == search_data['is_active'])
        
        # Filtri per date di arrivo
        if search_data.get('arrival_date_from'):
            query = query.filter(Booking.arrival_date >= search_data['arrival_date_from'])
        
        if search_data.get('arrival_date_to'):
            query = query.filter(Booking.arrival_date <= search_data['arrival_date_to'])
        
        # Filtri per date di partenza
        if search_data.get('departure_date_from'):
            query = query.filter(Booking.departure_date >= search_data['departure_date_from'])
        
        if search_data.get('departure_date_to'):
            query = query.filter(Booking.departure_date <= search_data['departure_date_to'])
        
        # Filtri per numero ospiti
        if search_data.get('guest_count_min'):
            query = query.filter(Booking.guest_count >= search_data['guest_count_min'])
        
        if search_data.get('guest_count_max'):
            query = query.filter(Booking.guest_count <= search_data['guest_count_max'])
        
        # Filtri per documenti
        if search_data.get('schedine_not_sent'):
            query = query.filter(Booking.schedine_sent_count == 0)
        
        if search_data.get('alloggiati_web_not_sent'):
            query = query.filter(Booking.alloggiati_web_sent_date.is_(None))
        
        # Ordinamento
        sort_field = getattr(Booking, search_data.get('sort_by', 'arrival_date'))
        if search_data.get('sort_order', 'desc') == 'desc':
            query = query.order_by(sort_field.desc())
        else:
            query = query.order_by(sort_field.asc())
        
        # Paginazione
        page = search_data.get('page', 1)
        per_page = search_data.get('per_page', 20)
        
        paginated = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        # Serializzazione dati
        bookings_data = booking_list_schema.dump(paginated.items, many=True)
        
        return jsonify({
            'bookings': bookings_data,
            'pagination': {
                'page': paginated.page,
                'pages': paginated.pages,
                'per_page': paginated.per_page,
                'total': paginated.total,
                'has_next': paginated.has_next,
                'has_prev': paginated.has_prev
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Errore nel recupero prenotazioni: {str(e)}")
        return jsonify({'error': 'Errore interno del server'}), 500


@api_v1_bp.route('/bookings', methods=['POST'])
@jwt_required()
@require_role(['Rohirrim', 'Lord'])
def create_booking():
    """
    Crea una nuova prenotazione
    
    Richiede autorizzazione Rohirrim o Lord
    """
    try:
        # Validazione dati input
        booking_data = booking_create_schema.load(request.json)
        
        # Verifica esistenza unità immobiliare
        property_unit = PropertyUnit.query.get(booking_data['property_unit_id'])
        if not property_unit:
            return jsonify({'error': 'Property unit not found'}), 404
        
        # Controllo duplicati (stesso nome o overlapping dates)
        existing_booking = Booking.query.filter(
            and_(
                Booking.booking_name == booking_data['booking_name'],
                Booking.is_active == True
            )
        ).first()
        
        if existing_booking:
            return jsonify({'error': 'Booking with this name already exists'}), 409
        
        # Controllo overlapping per stessa unità immobiliare
        overlapping = Booking.query.filter(
            and_(
                Booking.property_unit_id == booking_data['property_unit_id'],
                Booking.is_active == True,
                Booking.booking_status == 'confirmed',
                or_(
                    and_(
                        Booking.arrival_date <= booking_data['arrival_date'],
                        Booking.departure_date > booking_data['arrival_date']
                    ),
                    and_(
                        Booking.arrival_date < booking_data['departure_date'],
                        Booking.departure_date >= booking_data['departure_date']
                    ),
                    and_(
                        Booking.arrival_date >= booking_data['arrival_date'],
                        Booking.departure_date <= booking_data['departure_date']
                    )
                )
            )
        ).first()
        
        if overlapping:
            return jsonify({
                'error': 'Booking dates overlap with existing booking',
                'conflicting_booking': overlapping.booking_name
            }), 409
        
        # Creazione prenotazione
        booking = Booking(**booking_data)
        
        db.session.add(booking)
        db.session.commit()
        
        # Serializzazione risposta
        result = booking_schema.dump(booking)
        
        current_app.logger.info(f"Prenotazione creata: {booking.booking_name} (ID: {booking.id})")
        
        return jsonify({
            'message': 'Booking created successfully',
            'booking': result
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Errore nella creazione prenotazione: {str(e)}")
        return jsonify({'error': 'Errore interno del server'}), 500


@api_v1_bp.route('/bookings/<int:booking_id>', methods=['GET'])
@jwt_required()
@require_role(['Rohirrim', 'Lord', 'Dunedain'])
def get_booking(booking_id):
    """
    Ottieni dettagli di una prenotazione specifica
    """
    try:
        booking = Booking.query.options(
            joinedload(Booking.property_unit).joinedload(PropertyUnit.property_type)
        ).get(booking_id)
        
        if not booking:
            return jsonify({'error': 'Booking not found'}), 404
        
        result = booking_schema.dump(booking)
        
        return jsonify({'booking': result}), 200
        
    except Exception as e:
        current_app.logger.error(f"Errore nel recupero prenotazione {booking_id}: {str(e)}")
        return jsonify({'error': 'Errore interno del server'}), 500


@api_v1_bp.route('/bookings/<int:booking_id>', methods=['PUT'])
@jwt_required()
@require_role(['Rohirrim', 'Lord'])
def update_booking(booking_id):
    """
    Aggiorna una prenotazione esistente
    
    Richiede autorizzazione Rohirrim o Lord
    """
    try:
        booking = Booking.query.get(booking_id)
        if not booking:
            return jsonify({'error': 'Booking not found'}), 404
        
        # Validazione dati input
        update_data = booking_update_schema.load(request.json)
        
        # Verifica unità immobiliare se cambiata
        if 'property_unit_id' in update_data:
            property_unit = PropertyUnit.query.get(update_data['property_unit_id'])
            if not property_unit:
                return jsonify({'error': 'Property unit not found'}), 404
        
        # Controllo overlapping se cambiano date o unità
        if any(field in update_data for field in ['arrival_date', 'departure_date', 'property_unit_id']):
            arrival = update_data.get('arrival_date', booking.arrival_date)
            departure = update_data.get('departure_date', booking.departure_date)
            unit_id = update_data.get('property_unit_id', booking.property_unit_id)
            
            overlapping = Booking.query.filter(
                and_(
                    Booking.id != booking_id,
                    Booking.property_unit_id == unit_id,
                    Booking.is_active == True,
                    Booking.booking_status == 'confirmed',
                    or_(
                        and_(Booking.arrival_date <= arrival, Booking.departure_date > arrival),
                        and_(Booking.arrival_date < departure, Booking.departure_date >= departure),
                        and_(Booking.arrival_date >= arrival, Booking.departure_date <= departure)
                    )
                )
            ).first()
            
            if overlapping:
                return jsonify({
                    'error': 'Updated dates overlap with existing booking',
                    'conflicting_booking': overlapping.booking_name
                }), 409
        
        # Aggiornamento campi
        for field, value in update_data.items():
            setattr(booking, field, value)
        
        db.session.commit()
        
        # Serializzazione risposta
        result = booking_schema.dump(booking)
        
        current_app.logger.info(f"Prenotazione aggiornata: {booking.booking_name} (ID: {booking.id})")
        
        return jsonify({
            'message': 'Booking updated successfully',
            'booking': result
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Errore nell'aggiornamento prenotazione {booking_id}: {str(e)}")
        return jsonify({'error': 'Errore interno del server'}), 500


@api_v1_bp.route('/bookings/<int:booking_id>', methods=['DELETE'])
@jwt_required()
@require_role(['Rohirrim', 'Lord'])
def delete_booking(booking_id):
    """
    Elimina una prenotazione (soft delete)
    
    Richiede autorizzazione Rohirrim o Lord
    """
    try:
        booking = Booking.query.get(booking_id)
        if not booking:
            return jsonify({'error': 'Booking not found'}), 404
        
        # Soft delete
        booking.is_active = False
        booking.booking_status = 'cancelled'
        
        db.session.commit()
        
        current_app.logger.info(f"Prenotazione eliminata: {booking.booking_name} (ID: {booking.id})")
        
        return jsonify({'message': 'Booking deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Errore nell'eliminazione prenotazione {booking_id}: {str(e)}")
        return jsonify({'error': 'Errore interno del server'}), 500


@api_v1_bp.route('/bookings/stats', methods=['GET'])
@jwt_required()
@require_role(['Rohirrim', 'Lord', 'Dunedain'])
def get_booking_stats():
    """
    Ottieni statistiche delle prenotazioni
    """
    try:
        # Contatori per stato
        total_bookings = Booking.query.filter_by(is_active=True).count()
        confirmed_bookings = Booking.query.filter_by(is_active=True, booking_status='confirmed').count()
        cancelled_bookings = Booking.query.filter_by(booking_status='cancelled').count()
        completed_bookings = Booking.query.filter_by(is_active=True, booking_status='completed').count()
        
        # Contatori per periodo
        today = date.today()
        current_bookings = Booking.query.filter(
            Booking.arrival_date <= today,
            Booking.departure_date >= today,
            Booking.is_active == True,
            Booking.booking_status == 'confirmed'
        ).count()
        
        future_bookings = Booking.query.filter(
            Booking.arrival_date > today,
            Booking.is_active == True,
            Booking.booking_status == 'confirmed'
        ).count()
        
        past_bookings = Booking.query.filter(
            Booking.departure_date < today,
            Booking.is_active == True
        ).count()
        
        # Statistiche documenti
        bookings_with_schedine = Booking.query.filter(
            Booking.schedine_sent_count > 0,
            Booking.is_active == True
        ).count()
        
        bookings_without_schedine = Booking.query.filter(
            Booking.schedine_sent_count == 0,
            Booking.is_active == True
        ).count()
        
        bookings_with_alloggiati_web = Booking.query.filter(
            Booking.alloggiati_web_sent_date.isnot(None),
            Booking.is_active == True
        ).count()
        
        bookings_without_alloggiati_web = Booking.query.filter(
            Booking.alloggiati_web_sent_date.is_(None),
            Booking.is_active == True
        ).count()
        
        # Statistiche ospiti
        guest_stats = db.session.query(
            func.sum(Booking.guest_count).label('total_guests'),
            func.avg(Booking.guest_count).label('avg_guests')
        ).filter(Booking.is_active == True).first()
        
        # Statistiche durata
        duration_stats = db.session.query(
            func.avg(func.julianday(Booking.departure_date) - func.julianday(Booking.arrival_date)).label('avg_duration'),
            func.min(func.julianday(Booking.departure_date) - func.julianday(Booking.arrival_date)).label('min_duration'),
            func.max(func.julianday(Booking.departure_date) - func.julianday(Booking.arrival_date)).label('max_duration')
        ).filter(Booking.is_active == True).first()
        
        # Distribuzione per unità immobiliare
        unit_distribution = db.session.query(
            PropertyUnit.name,
            func.count(Booking.id).label('booking_count')
        ).join(Booking).filter(
            Booking.is_active == True
        ).group_by(PropertyUnit.id, PropertyUnit.name).all()
        
        stats = {
            'total_bookings': total_bookings,
            'confirmed_bookings': confirmed_bookings,
            'cancelled_bookings': cancelled_bookings,
            'completed_bookings': completed_bookings,
            'current_bookings': current_bookings,
            'future_bookings': future_bookings,
            'past_bookings': past_bookings,
            'bookings_with_schedine': bookings_with_schedine,
            'bookings_without_schedine': bookings_without_schedine,
            'bookings_with_alloggiati_web': bookings_with_alloggiati_web,
            'bookings_without_alloggiati_web': bookings_without_alloggiati_web,
            'total_guests': int(guest_stats.total_guests) if guest_stats.total_guests else 0,
            'avg_guests_per_booking': float(guest_stats.avg_guests) if guest_stats.avg_guests else 0.0,
            'avg_stay_duration': float(duration_stats.avg_duration) if duration_stats.avg_duration else 0.0,
            'min_stay_duration': int(duration_stats.min_duration) if duration_stats.min_duration else 0,
            'max_stay_duration': int(duration_stats.max_duration) if duration_stats.max_duration else 0,
            'bookings_by_property_unit': {unit.name: unit.booking_count for unit in unit_distribution}
        }
        
        return jsonify({'stats': stats}), 200
        
    except Exception as e:
        current_app.logger.error(f"Errore nel calcolo statistiche prenotazioni: {str(e)}")
        return jsonify({'error': 'Errore interno del server'}), 500


@api_v1_bp.route('/bookings/bulk-actions', methods=['POST'])
@jwt_required()
@require_role(['Rohirrim', 'Lord'])
def booking_bulk_actions():
    """
    Esegui azioni in bulk su multiple prenotazioni
    
    Azioni supportate:
    - confirm: Conferma prenotazioni
    - cancel: Cancella prenotazioni
    - complete: Completa prenotazioni
    - activate: Attiva prenotazioni
    - deactivate: Disattiva prenotazioni
    - send_schedina: Invia schedina
    - mark_alloggiati_web_sent: Marca alloggiati web come inviato
    - delete: Elimina prenotazioni (soft delete)
    """
    try:
        # Validazione dati
        bulk_data = booking_bulk_action_schema.load(request.json)
        
        booking_ids = bulk_data['booking_ids']
        action = bulk_data['action']
        
        # Recupera prenotazioni
        bookings = Booking.query.filter(Booking.id.in_(booking_ids)).all()
        
        if not bookings:
            return jsonify({'error': 'No bookings found with provided IDs'}), 404
        
        if len(bookings) != len(booking_ids):
            found_ids = [b.id for b in bookings]
            missing_ids = [id for id in booking_ids if id not in found_ids]
            return jsonify({
                'error': 'Some bookings not found',
                'missing_ids': missing_ids
            }), 404
        
        updated_count = 0
        
        # Esecuzione azione
        for booking in bookings:
            if action == 'confirm':
                booking.confirm_booking()
                updated_count += 1
            elif action == 'cancel':
                booking.cancel_booking()
                updated_count += 1
            elif action == 'complete':
                booking.complete_booking()
                updated_count += 1
            elif action == 'activate':
                booking.activate()
                updated_count += 1
            elif action == 'deactivate':
                booking.deactivate()
                updated_count += 1
            elif action == 'send_schedina':
                booking.send_schedina()
                updated_count += 1
            elif action == 'mark_alloggiati_web_sent':
                sent_date = bulk_data.get('alloggiati_web_date', datetime.now())
                booking.mark_alloggiati_web_sent(sent_date)
                updated_count += 1
            elif action == 'delete':
                booking.is_active = False
                booking.booking_status = 'cancelled'
                updated_count += 1
        
        # Aggiornamento note se fornite
        if bulk_data.get('notes'):
            for booking in bookings:
                booking.notes = bulk_data['notes']
        
        db.session.commit()
        
        current_app.logger.info(f"Azione bulk '{action}' eseguita su {updated_count} prenotazioni")
        
        return jsonify({
            'message': f'Bulk action {action} completed successfully',
            'updated_count': updated_count,
            'total_requested': len(booking_ids)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Errore nell'azione bulk prenotazioni: {str(e)}")
        return jsonify({'error': 'Errore interno del server'}), 500


@api_v1_bp.route('/bookings/check-duplicate', methods=['POST'])
@jwt_required()
@require_role(['Rohirrim', 'Lord'])
def check_booking_duplicate():
    """
    Controlla se esistono prenotazioni duplicate o in conflitto
    """
    try:
        # Validazione dati
        check_data = booking_duplicate_check_schema.load(request.json)
        
        duplicates = []
        conflicts = []
        
        # Controllo nome duplicato
        if check_data.get('booking_name'):
            name_query = Booking.query.filter(
                Booking.booking_name == check_data['booking_name'],
                Booking.is_active == True
            )
            
            if check_data.get('exclude_id'):
                name_query = name_query.filter(Booking.id != check_data['exclude_id'])
            
            name_duplicate = name_query.first()
            if name_duplicate:
                duplicates.append({
                    'type': 'name',
                    'booking_id': name_duplicate.id,
                    'booking_name': name_duplicate.booking_name,
                    'message': 'Booking name already exists'
                })
        
        # Controllo CRM reference duplicato
        if check_data.get('crm_reference_id'):
            crm_query = Booking.query.filter(
                Booking.crm_reference_id == check_data['crm_reference_id'],
                Booking.is_active == True
            )
            
            if check_data.get('exclude_id'):
                crm_query = crm_query.filter(Booking.id != check_data['exclude_id'])
            
            crm_duplicate = crm_query.first()
            if crm_duplicate:
                duplicates.append({
                    'type': 'crm_reference',
                    'booking_id': crm_duplicate.id,
                    'booking_name': crm_duplicate.booking_name,
                    'crm_reference_id': crm_duplicate.crm_reference_id,
                    'message': 'CRM reference ID already exists'
                })
        
        # Controllo conflitti di date
        arrival = check_data['arrival_date']
        departure = check_data['departure_date']
        unit_id = check_data['property_unit_id']
        
        conflict_query = Booking.query.filter(
            and_(
                Booking.property_unit_id == unit_id,
                Booking.is_active == True,
                Booking.booking_status == 'confirmed',
                or_(
                    and_(Booking.arrival_date <= arrival, Booking.departure_date > arrival),
                    and_(Booking.arrival_date < departure, Booking.departure_date >= departure),
                    and_(Booking.arrival_date >= arrival, Booking.departure_date <= departure)
                )
            )
        )
        
        if check_data.get('exclude_id'):
            conflict_query = conflict_query.filter(Booking.id != check_data['exclude_id'])
        
        conflicting_bookings = conflict_query.all()
        
        for conflicting in conflicting_bookings:
            conflicts.append({
                'type': 'date_overlap',
                'booking_id': conflicting.id,
                'booking_name': conflicting.booking_name,
                'arrival_date': conflicting.arrival_date.isoformat(),
                'departure_date': conflicting.departure_date.isoformat(),
                'message': 'Date range overlaps with existing booking'
            })
        
        has_issues = len(duplicates) > 0 or len(conflicts) > 0
        
        return jsonify({
            'has_duplicates': len(duplicates) > 0,
            'has_conflicts': len(conflicts) > 0,
            'has_issues': has_issues,
            'duplicates': duplicates,
            'conflicts': conflicts
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Errore nel controllo duplicati prenotazioni: {str(e)}")
        return jsonify({'error': 'Errore interno del server'}), 500


@api_v1_bp.route('/bookings/by-property/<int:property_unit_id>', methods=['GET'])
@jwt_required()
@require_role(['Rohirrim', 'Lord', 'Dunedain'])
def get_bookings_by_property(property_unit_id):
    """
    Ottieni tutte le prenotazioni per un'unità immobiliare specifica
    """
    try:
        # Validazione parametri
        params = request.args.to_dict()
        params['property_unit_id'] = property_unit_id
        filter_data = booking_by_property_schema.load(params)
        
        # Verifica esistenza unità immobiliare
        property_unit = PropertyUnit.query.get(property_unit_id)
        if not property_unit:
            return jsonify({'error': 'Property unit not found'}), 404
        
        # Query base
        query = Booking.query.filter_by(property_unit_id=property_unit_id)
        
        # Filtro inclusione inactive
        if not filter_data.get('include_inactive', False):
            query = query.filter_by(is_active=True)
        
        # Filtro per date
        if filter_data.get('date_from'):
            query = query.filter(Booking.departure_date >= filter_data['date_from'])
        
        if filter_data.get('date_to'):
            query = query.filter(Booking.arrival_date <= filter_data['date_to'])
        
        # Filtro per stato
        if filter_data.get('status_filter'):
            query = query.filter(Booking.booking_status == filter_data['status_filter'].value)
        
        # Ordinamento per data arrivo
        bookings = query.order_by(Booking.arrival_date.desc()).all()
        
        # Serializzazione
        bookings_data = booking_list_schema.dump(bookings, many=True)
        
        return jsonify({
            'property_unit': {
                'id': property_unit.id,
                'name': property_unit.name,
                'type': property_unit.property_type.name if property_unit.property_type else None
            },
            'bookings_count': len(bookings),
            'bookings': bookings_data
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Errore nel recupero prenotazioni per unità {property_unit_id}: {str(e)}")
        return jsonify({'error': 'Errore interno del server'}), 500


@api_v1_bp.route('/bookings/by-date-range', methods=['GET'])
@jwt_required()
@require_role(['Rohirrim', 'Lord', 'Dunedain'])
def get_bookings_by_date_range():
    """
    Ottieni prenotazioni per un range di date specifico
    """
    try:
        # Validazione parametri
        filter_data = booking_by_date_range_schema.load(request.args.to_dict())
        
        start_date = filter_data['start_date']
        end_date = filter_data['end_date']
        
        # Query base per prenotazioni che si sovrappongono al range
        query = Booking.query.filter(
            and_(
                Booking.arrival_date <= end_date,
                Booking.departure_date >= start_date
            )
        )
        
        # Filtro per unità immobiliare specifica
        if filter_data.get('property_unit_id'):
            query = query.filter_by(property_unit_id=filter_data['property_unit_id'])
        
        # Filtro inclusione inactive
        if not filter_data.get('include_inactive', False):
            query = query.filter_by(is_active=True)
        
        # Filtro per stato
        if filter_data.get('status_filter'):
            query = query.filter(Booking.booking_status == filter_data['status_filter'].value)
        
        # Ordinamento per data arrivo
        bookings = query.order_by(Booking.arrival_date.asc()).all()
        
        # Serializzazione con join ottimizzato
        bookings = Booking.query.filter(query.whereclause).options(
            joinedload(Booking.property_unit).joinedload(PropertyUnit.property_type)
        ).order_by(Booking.arrival_date.asc()).all()
        
        bookings_data = booking_list_schema.dump(bookings, many=True)
        
        return jsonify({
            'date_range': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'days': (end_date - start_date).days + 1
            },
            'bookings_count': len(bookings),
            'bookings': bookings_data
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Errore nel recupero prenotazioni per range date: {str(e)}")
        return jsonify({'error': 'Errore interno del server'}), 500


@api_v1_bp.route('/bookings/<int:booking_id>/summary', methods=['GET'])
@jwt_required()
@require_role(['Rohirrim', 'Lord', 'Dunedain'])
def get_booking_summary(booking_id):
    """
    Ottieni riassunto completo di una prenotazione con POD, validazione e dettagli
    """
    try:
        # Validazione parametri
        params = request.args.to_dict()
        params['booking_id'] = booking_id
        summary_data = booking_summary_schema.load(params)
        
        # Recupera prenotazione con relazioni
        booking = Booking.query.options(
            joinedload(Booking.property_unit).joinedload(PropertyUnit.property_type)
        ).get(booking_id)
        
        if not booking:
            return jsonify({'error': 'Booking not found'}), 404
        
        # Riassunto base
        summary = booking.get_booking_summary()
        
        # Aggiunta informazioni POD se richiesto
        if summary_data.get('include_pod_info', True):
            pod_info = booking.get_pod_info()
            summary['pod_info'] = pod_info
        
        # Aggiunta validazione se richiesta
        if summary_data.get('include_validation_errors', True):
            validation_errors = booking.validate_booking()
            summary['validation'] = {
                'is_valid': len(validation_errors) == 0,
                'errors': validation_errors
            }
        
        # Aggiunta dettagli proprietà se richiesti
        if summary_data.get('include_property_details', True) and booking.property_unit:
            summary['property_details'] = {
                'address': booking.property_unit.get_full_address(),
                'coordinates': {
                    'latitude': float(booking.property_unit.latitude) if booking.property_unit.latitude else None,
                    'longitude': float(booking.property_unit.longitude) if booking.property_unit.longitude else None
                },
                'facilities': booking.property_unit.facilities,
                'description': booking.property_unit.description
            }
        
        # Aggiunta stato documenti se richiesto
        if summary_data.get('include_documents_status', True):
            summary['documents_detailed'] = {
                'schedine': {
                    'sent_count': booking.schedine_sent_count,
                    'is_sent': booking.schedine_sent_count > 0,
                    'needs_sending': booking.schedine_sent_count == 0 and booking.is_current()
                },
                'alloggiati_web': {
                    'is_sent': booking.is_alloggiati_web_sent(),
                    'sent_date': booking.alloggiati_web_sent_date,
                    'needs_sending': not booking.is_alloggiati_web_sent() and booking.is_current()
                }
            }
        
        return jsonify({'summary': summary}), 200
        
    except Exception as e:
        current_app.logger.error(f"Errore nel riassunto prenotazione {booking_id}: {str(e)}")
        return jsonify({'error': 'Errore interno del server'}), 500
