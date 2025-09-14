"""
Schemi Marshmallow per il modello Booking
"""

from marshmallow import Schema, fields, validates, ValidationError, post_load, validate
from marshmallow_enum import EnumField
from datetime import date, datetime, timedelta
from enum import Enum


class BookingStatus(Enum):
    """Stati possibili per una prenotazione"""
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    PENDING = "pending"


class BookingBaseSchema(Schema):
    """Schema base per Booking con campi comuni"""
    
    # Campi principali
    crm_reference_id = fields.Str(required=False, allow_none=True)
    booking_name = fields.Str(required=True, validate=validate.Length(min=1, max=255))
    
    # Date soggiorno
    arrival_date = fields.Date(required=True)
    departure_date = fields.Date(required=True)
    
    # Ospiti
    guest_count = fields.Int(required=True, validate=validate.Range(min=1))
    guest_names = fields.Str(required=False, allow_none=True)
    
    # Note e status
    notes = fields.Str(required=False, allow_none=True)
    booking_status = EnumField(BookingStatus, by_value=True, missing=BookingStatus.CONFIRMED)
    
    # Relazioni
    property_unit_id = fields.Int(required=True)
    
    # Stato
    is_active = fields.Bool(missing=True)
    
    @validates('arrival_date')
    def validate_arrival_date(self, value):
        """Valida la data di arrivo"""
        if not value:
            raise ValidationError("Arrival date is required")
    
    @validates('departure_date')
    def validate_departure_date(self, value):
        """Valida la data di partenza"""
        if not value:
            raise ValidationError("Departure date is required")
    
    @post_load
    def validate_date_range(self, data, **kwargs):
        """Valida che la data di partenza sia dopo quella di arrivo"""
        arrival = data.get('arrival_date')
        departure = data.get('departure_date')
        
        if arrival and departure and departure <= arrival:
            raise ValidationError("Departure date must be after arrival date")
        
        return data


class BookingCreateSchema(BookingBaseSchema):
    """Schema per creazione di una nuova prenotazione"""
    
    # Gestione documenti (inizializzati a 0/False)
    schedine_sent_count = fields.Int(missing=0, dump_only=True)
    alloggiati_web_sent_date = fields.DateTime(dump_only=True, allow_none=True)


class BookingUpdateSchema(BookingBaseSchema):
    """Schema per aggiornamento di una prenotazione esistente"""
    
    # Tutti i campi opzionali per l'update
    crm_reference_id = fields.Str(required=False, allow_none=True)
    booking_name = fields.Str(required=False, validate=validate.Length(min=1, max=255))
    arrival_date = fields.Date(required=False)
    departure_date = fields.Date(required=False)
    guest_count = fields.Int(required=False, validate=validate.Range(min=1))
    property_unit_id = fields.Int(required=False)
    
    # Gestione documenti e comunicazioni
    schedine_sent_count = fields.Int(required=False, validate=validate.Range(min=0))
    alloggiati_web_sent_date = fields.DateTime(required=False, allow_none=True)


class BookingResponseSchema(BookingBaseSchema):
    """Schema per la risposta completa di una prenotazione"""
    
    # Campi di sistema
    id = fields.Int(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    
    # Gestione documenti
    schedine_sent_count = fields.Int(dump_only=True)
    alloggiati_web_sent_date = fields.DateTime(dump_only=True, allow_none=True)
    
    # Campi calcolati
    stay_duration = fields.Method("calculate_stay_duration")
    is_current = fields.Method("calculate_is_current")
    is_future = fields.Method("calculate_is_future")
    is_past = fields.Method("calculate_is_past")
    
    # Informazioni unità immobiliare (nested)
    property_unit = fields.Nested('PropertyUnitResponseSchema', dump_only=True, exclude=['bookings'])
    
    def calculate_stay_duration(self, obj):
        """Calcola la durata del soggiorno"""
        if obj.arrival_date and obj.departure_date:
            return (obj.departure_date - obj.arrival_date).days
        return 0
    
    def calculate_is_current(self, obj):
        """Controlla se la prenotazione è corrente"""
        return obj.is_current() if hasattr(obj, 'is_current') else False
    
    def calculate_is_future(self, obj):
        """Controlla se la prenotazione è futura"""
        return obj.is_future() if hasattr(obj, 'is_future') else False
    
    def calculate_is_past(self, obj):
        """Controlla se la prenotazione è passata"""
        return obj.is_past() if hasattr(obj, 'is_past') else False


class BookingListSchema(Schema):
    """Schema semplificato per liste di prenotazioni"""
    
    id = fields.Int(dump_only=True)
    crm_reference_id = fields.Str()
    booking_name = fields.Str()
    arrival_date = fields.Date()
    departure_date = fields.Date()
    guest_count = fields.Int()
    booking_status = EnumField(BookingStatus, by_value=True)
    is_active = fields.Bool()
    stay_duration = fields.Method("calculate_stay_duration")
    
    # Informazioni unità immobiliare essenziali
    property_unit_name = fields.Method("get_property_unit_name")
    property_unit_type = fields.Method("get_property_unit_type")
    
    def calculate_stay_duration(self, obj):
        """Calcola la durata del soggiorno"""
        if obj.arrival_date and obj.departure_date:
            return (obj.departure_date - obj.arrival_date).days
        return 0
    
    def get_property_unit_name(self, obj):
        """Ottiene il nome dell'unità immobiliare"""
        return obj.property_unit.name if obj.property_unit else None
    
    def get_property_unit_type(self, obj):
        """Ottiene il tipo dell'unità immobiliare"""
        return obj.property_unit.property_type.name if obj.property_unit and obj.property_unit.property_type else None


class BookingSearchSchema(Schema):
    """Schema per ricerca prenotazioni con filtri"""
    
    # Filtri di ricerca
    booking_name = fields.Str(required=False)
    crm_reference_id = fields.Str(required=False)
    property_unit_id = fields.Int(required=False)
    booking_status = EnumField(BookingStatus, by_value=True, required=False)
    is_active = fields.Bool(required=False)
    
    # Filtri per date
    arrival_date_from = fields.Date(required=False)
    arrival_date_to = fields.Date(required=False)
    departure_date_from = fields.Date(required=False)
    departure_date_to = fields.Date(required=False)
    
    # Filtri per ospiti
    guest_count_min = fields.Int(required=False, validate=validate.Range(min=1))
    guest_count_max = fields.Int(required=False, validate=validate.Range(min=1))
    
    # Filtri per documenti
    schedine_not_sent = fields.Bool(required=False)  # schedine_sent_count = 0
    alloggiati_web_not_sent = fields.Bool(required=False)  # alloggiati_web_sent_date is null
    
    # Paginazione
    page = fields.Int(required=False, validate=validate.Range(min=1), missing=1)
    per_page = fields.Int(required=False, validate=validate.Range(min=1, max=100), missing=20)
    
    # Ordinamento
    sort_by = fields.Str(required=False, validate=validate.OneOf([
        'arrival_date', 'departure_date', 'booking_name', 'created_at', 'guest_count'
    ]), missing='arrival_date')
    sort_order = fields.Str(required=False, validate=validate.OneOf(['asc', 'desc']), missing='desc')


class BookingStatsSchema(Schema):
    """Schema per statistiche delle prenotazioni"""
    
    # Contatori per stato
    total_bookings = fields.Int(dump_only=True)
    confirmed_bookings = fields.Int(dump_only=True)
    cancelled_bookings = fields.Int(dump_only=True)
    completed_bookings = fields.Int(dump_only=True)
    
    # Contatori per periodo
    current_bookings = fields.Int(dump_only=True)
    future_bookings = fields.Int(dump_only=True)
    past_bookings = fields.Int(dump_only=True)
    
    # Statistiche documenti
    bookings_with_schedine = fields.Int(dump_only=True)
    bookings_without_schedine = fields.Int(dump_only=True)
    bookings_with_alloggiati_web = fields.Int(dump_only=True)
    bookings_without_alloggiati_web = fields.Int(dump_only=True)
    
    # Statistiche ospiti
    total_guests = fields.Int(dump_only=True)
    avg_guests_per_booking = fields.Float(dump_only=True)
    
    # Statistiche durata
    avg_stay_duration = fields.Float(dump_only=True)
    min_stay_duration = fields.Int(dump_only=True)
    max_stay_duration = fields.Int(dump_only=True)
    
    # Distribuzione per unità immobiliare
    bookings_by_property_unit = fields.Dict(dump_only=True)


class BookingBulkActionSchema(Schema):
    """Schema per azioni bulk sulle prenotazioni"""
    
    booking_ids = fields.List(fields.Int(), required=True, validate=validate.Length(min=1))
    action = fields.Str(required=True, validate=validate.OneOf([
        'confirm', 'cancel', 'complete', 'activate', 'deactivate',
        'send_schedina', 'mark_alloggiati_web_sent', 'delete'
    ]))
    
    # Parametri opzionali per azioni specifiche
    notes = fields.Str(required=False)  # Per aggiornamento note
    alloggiati_web_date = fields.DateTime(required=False)  # Per mark_alloggiati_web_sent


class BookingDuplicateCheckSchema(Schema):
    """Schema per controllo duplicati prenotazioni"""
    
    booking_name = fields.Str(required=False)
    crm_reference_id = fields.Str(required=False)
    property_unit_id = fields.Int(required=True)
    arrival_date = fields.Date(required=True)
    departure_date = fields.Date(required=True)
    exclude_id = fields.Int(required=False)  # Per escludere un ID specifico (update)


class BookingValidationSchema(Schema):
    """Schema per validazione avanzata prenotazioni"""
    
    booking_id = fields.Int(required=True)
    validate_dates = fields.Bool(missing=True)
    validate_property = fields.Bool(missing=True)
    validate_guests = fields.Bool(missing=True)
    validate_documents = fields.Bool(missing=True)
    validate_conflicts = fields.Bool(missing=True)  # Conflitti con altre prenotazioni


class BookingByPropertySchema(Schema):
    """Schema per prenotazioni per unità immobiliare"""
    
    property_unit_id = fields.Int(required=True)
    include_inactive = fields.Bool(missing=False)
    date_from = fields.Date(required=False)
    date_to = fields.Date(required=False)
    status_filter = EnumField(BookingStatus, by_value=True, required=False)


class BookingByDateRangeSchema(Schema):
    """Schema per prenotazioni per range di date"""
    
    start_date = fields.Date(required=True)
    end_date = fields.Date(required=True)
    property_unit_id = fields.Int(required=False)
    include_inactive = fields.Bool(missing=False)
    status_filter = EnumField(BookingStatus, by_value=True, required=False)
    
    @post_load
    def validate_date_range(self, data, **kwargs):
        """Valida il range di date"""
        start = data.get('start_date')
        end = data.get('end_date')
        
        if start and end and end < start:
            raise ValidationError("End date must be after start date")
        
        # Limite massimo range
        if start and end and (end - start).days > 365:
            raise ValidationError("Date range cannot exceed 365 days")
        
        return data


class BookingSummarySchema(Schema):
    """Schema per riassunto completo prenotazione"""
    
    booking_id = fields.Int(required=True)
    include_pod_info = fields.Bool(missing=True)
    include_property_details = fields.Bool(missing=True)
    include_documents_status = fields.Bool(missing=True)
    include_validation_errors = fields.Bool(missing=True)


# Istanze degli schemi per l'uso nell'applicazione
booking_schema = BookingResponseSchema()
bookings_schema = BookingResponseSchema(many=True)
booking_create_schema = BookingCreateSchema()
booking_update_schema = BookingUpdateSchema()
booking_list_schema = BookingListSchema()
booking_search_schema = BookingSearchSchema()
booking_stats_schema = BookingStatsSchema()
booking_bulk_action_schema = BookingBulkActionSchema()
booking_duplicate_check_schema = BookingDuplicateCheckSchema()
booking_validation_schema = BookingValidationSchema()
booking_by_property_schema = BookingByPropertySchema()
booking_by_date_range_schema = BookingByDateRangeSchema()
booking_summary_schema = BookingSummarySchema()
