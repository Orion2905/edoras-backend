# Property Unit Schemas - Sistema Validazione Completo

from marshmallow import Schema, fields, validates, ValidationError, validate, pre_load
from datetime import datetime
from decimal import Decimal


class PropertyUnitSchema(Schema):
    """Schema per serializzazione completa di un'unità immobiliare."""
    
    id = fields.Integer(dump_only=True)
    name = fields.String(required=True, validate=validate.Length(min=1, max=100))
    description = fields.String(allow_none=True)
    square_meters = fields.Decimal(required=True, validate=validate.Range(min=0.01))
    rooms = fields.Integer(allow_none=True, validate=validate.Range(min=0))
    bathrooms = fields.Integer(allow_none=True, validate=validate.Range(min=0))
    floor = fields.String(allow_none=True, validate=validate.Length(max=10))
    address = fields.String(allow_none=True, validate=validate.Length(max=255))
    city = fields.String(allow_none=True, validate=validate.Length(max=100))
    postal_code = fields.String(allow_none=True, validate=validate.Length(max=10))
    province = fields.String(allow_none=True, validate=validate.Length(max=5))
    property_type_id = fields.Integer(required=True)
    company_id = fields.Integer(allow_none=True)
    is_active = fields.Boolean(dump_only=True)
    is_occupied = fields.Boolean(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    
    # Campi relazionali
    property_type_name = fields.String(dump_only=True)
    company_name = fields.String(dump_only=True)
    full_address = fields.String(dump_only=True)
    connected_pods_count = fields.Integer(dump_only=True)
    
    # Relationships (quando necessario)
    property_type = fields.Nested('PropertyTypeSchema', exclude=['property_units'], dump_only=True)
    property_pods = fields.List(fields.Nested('PropertyPodSchema', exclude=['property_unit']), dump_only=True)


class PropertyUnitCreateSchema(Schema):
    """Schema per creazione nuova unità immobiliare."""
    
    name = fields.String(
        required=True, 
        validate=validate.Length(min=1, max=100),
        error_messages={'required': 'Il nome dell\'unità immobiliare è obbligatorio'}
    )
    description = fields.String(
        allow_none=True,
        missing=None
    )
    square_meters = fields.Decimal(
        required=True,
        validate=validate.Range(min=0.01, max=99999.99),
        error_messages={'required': 'La metratura è obbligatoria'}
    )
    rooms = fields.Integer(
        allow_none=True,
        validate=validate.Range(min=0, max=100),
        missing=None
    )
    bathrooms = fields.Integer(
        allow_none=True,
        validate=validate.Range(min=0, max=20),
        missing=None
    )
    floor = fields.String(
        allow_none=True,
        validate=validate.Length(max=10),
        missing=None
    )
    address = fields.String(
        allow_none=True,
        validate=validate.Length(max=255),
        missing=None
    )
    city = fields.String(
        allow_none=True,
        validate=validate.Length(max=100),
        missing=None
    )
    postal_code = fields.String(
        allow_none=True,
        validate=validate.Length(max=10),
        missing=None
    )
    province = fields.String(
        allow_none=True,
        validate=validate.Length(max=5),
        missing=None
    )
    property_type_id = fields.Integer(
        required=True,
        validate=validate.Range(min=1),
        error_messages={'required': 'Il tipo di proprietà è obbligatorio'}
    )
    company_id = fields.Integer(
        allow_none=True,
        validate=validate.Range(min=1),
        missing=None
    )
    
    @validates('name')
    def validate_name(self, value):
        """Validazione personalizzata per il nome."""
        if not value or not value.strip():
            raise ValidationError('Il nome dell\'unità immobiliare non può essere vuoto')
        
        # Controllo caratteri speciali
        if any(char in value for char in ['<', '>', '&', '"', "'"]):
            raise ValidationError('Il nome dell\'unità contiene caratteri non validi')
    
    @validates('square_meters')
    def validate_square_meters(self, value):
        """Validazione personalizzata per la metratura."""
        if value is not None and value <= 0:
            raise ValidationError('La metratura deve essere maggiore di zero')
        
        if value is not None and value > 99999.99:
            raise ValidationError('La metratura non può essere superiore a 99999.99 mq')
    
    @validates('postal_code')
    def validate_postal_code(self, value):
        """Validazione CAP italiano."""
        if value and value.strip():
            import re
            if not re.match(r'^\d{5}$', value.strip()):
                raise ValidationError('Il CAP deve essere composto da 5 cifre')
    
    @validates('province')
    def validate_province(self, value):
        """Validazione provincia italiana."""
        if value and value.strip():
            if len(value.strip()) != 2:
                raise ValidationError('La provincia deve essere di 2 caratteri (es. MI, RM)')
            if not value.strip().isalpha():
                raise ValidationError('La provincia deve contenere solo lettere')


class PropertyUnitUpdateSchema(Schema):
    """Schema per aggiornamento unità immobiliare."""
    
    name = fields.String(
        validate=validate.Length(min=1, max=100),
        allow_none=True
    )
    description = fields.String(allow_none=True)
    square_meters = fields.Decimal(
        validate=validate.Range(min=0.01, max=99999.99),
        allow_none=True
    )
    rooms = fields.Integer(
        validate=validate.Range(min=0, max=100),
        allow_none=True
    )
    bathrooms = fields.Integer(
        validate=validate.Range(min=0, max=20),
        allow_none=True
    )
    floor = fields.String(
        validate=validate.Length(max=10),
        allow_none=True
    )
    address = fields.String(
        validate=validate.Length(max=255),
        allow_none=True
    )
    city = fields.String(
        validate=validate.Length(max=100),
        allow_none=True
    )
    postal_code = fields.String(
        validate=validate.Length(max=10),
        allow_none=True
    )
    province = fields.String(
        validate=validate.Length(max=5),
        allow_none=True
    )
    property_type_id = fields.Integer(
        validate=validate.Range(min=1),
        allow_none=True
    )
    company_id = fields.Integer(
        validate=validate.Range(min=1),
        allow_none=True
    )
    is_active = fields.Boolean(allow_none=True)
    is_occupied = fields.Boolean(allow_none=True)
    
    @validates('name')
    def validate_name(self, value):
        """Validazione personalizzata per il nome."""
        if value is not None:
            if not value or not value.strip():
                raise ValidationError('Il nome dell\'unità immobiliare non può essere vuoto')
            
            # Controllo caratteri speciali
            if any(char in value for char in ['<', '>', '&', '"', "'"]):
                raise ValidationError('Il nome dell\'unità contiene caratteri non validi')
    
    @validates('square_meters')
    def validate_square_meters(self, value):
        """Validazione personalizzata per la metratura."""
        if value is not None and value <= 0:
            raise ValidationError('La metratura deve essere maggiore di zero')
        
        if value is not None and value > 99999.99:
            raise ValidationError('La metratura non può essere superiore a 99999.99 mq')
    
    @validates('postal_code')
    def validate_postal_code(self, value):
        """Validazione CAP italiano."""
        if value is not None and value and value.strip():
            import re
            if not re.match(r'^\d{5}$', value.strip()):
                raise ValidationError('Il CAP deve essere composto da 5 cifre')
    
    @validates('province')
    def validate_province(self, value):
        """Validazione provincia italiana."""
        if value is not None and value and value.strip():
            if len(value.strip()) != 2:
                raise ValidationError('La provincia deve essere di 2 caratteri (es. MI, RM)')
            if not value.strip().isalpha():
                raise ValidationError('La provincia deve contenere solo lettere')


class PropertyUnitListSchema(Schema):
    """Schema per lista unità immobiliari con filtri."""
    
    page = fields.Integer(validate=validate.Range(min=1), missing=1)
    per_page = fields.Integer(validate=validate.Range(min=1, max=100), missing=20)
    property_type_id = fields.Integer(allow_none=True)
    company_id = fields.Integer(allow_none=True)
    city = fields.String(allow_none=True, validate=validate.Length(max=100))
    province = fields.String(allow_none=True, validate=validate.Length(max=5))
    is_active = fields.Boolean(allow_none=True, missing=True)
    is_occupied = fields.Boolean(allow_none=True)
    min_square_meters = fields.Decimal(allow_none=True, validate=validate.Range(min=0))
    max_square_meters = fields.Decimal(allow_none=True, validate=validate.Range(min=0))
    min_rooms = fields.Integer(allow_none=True, validate=validate.Range(min=0))
    max_rooms = fields.Integer(allow_none=True, validate=validate.Range(min=0))
    search = fields.String(allow_none=True, validate=validate.Length(max=100))
    sort_by = fields.String(
        validate=validate.OneOf(['name', 'square_meters', 'rooms', 'city', 'property_type_name', 'created_at']),
        missing='name'
    )
    sort_order = fields.String(
        validate=validate.OneOf(['asc', 'desc']),
        missing='asc'
    )


class PropertyUnitStatsSchema(Schema):
    """Schema per statistiche unità immobiliari."""
    
    total_units = fields.Integer(dump_only=True)
    active_units = fields.Integer(dump_only=True)
    occupied_units = fields.Integer(dump_only=True)
    available_units = fields.Integer(dump_only=True)
    total_square_meters = fields.Decimal(dump_only=True)
    average_square_meters = fields.Decimal(dump_only=True)
    by_property_type = fields.Dict(dump_only=True)
    by_city = fields.Dict(dump_only=True)
    by_company = fields.Dict(dump_only=True)
    occupancy_rate = fields.Decimal(dump_only=True)


class PropertyUnitDuplicateCheckSchema(Schema):
    """Schema per controllo duplicati unità immobiliari."""
    
    name = fields.String(required=True)
    company_id = fields.Integer(allow_none=True)
    exclude_id = fields.Integer(allow_none=True, missing=None)


class PropertyUnitBulkActionSchema(Schema):
    """Schema per azioni bulk su unità immobiliari."""
    
    ids = fields.List(
        fields.Integer(validate=validate.Range(min=1)),
        required=True,
        validate=validate.Length(min=1, max=100),
        error_messages={'required': 'Lista di ID è obbligatoria'}
    )
    action = fields.String(
        required=True,
        validate=validate.OneOf(['activate', 'deactivate', 'occupy', 'vacate', 'change_company', 'change_type', 'delete']),
        error_messages={'required': 'Azione da eseguire è obbligatoria'}
    )
    # Parametri aggiuntivi per azioni specifiche
    target_company_id = fields.Integer(allow_none=True, validate=validate.Range(min=1))
    target_property_type_id = fields.Integer(allow_none=True, validate=validate.Range(min=1))


class PropertyUnitByTypeSchema(Schema):
    """Schema per ottenere unità per tipo di proprietà."""
    
    property_type_id = fields.Integer(required=True, validate=validate.Range(min=1))
    include_inactive = fields.Boolean(missing=False)


class PropertyUnitByCompanySchema(Schema):
    """Schema per ottenere unità per azienda."""
    
    company_id = fields.Integer(required=True, validate=validate.Range(min=1))
    include_inactive = fields.Boolean(missing=False)


class PropertyUnitOccupancySchema(Schema):
    """Schema per gestione occupazione unità."""
    
    is_occupied = fields.Boolean(required=True)
    notes = fields.String(allow_none=True, validate=validate.Length(max=500))


class PropertyUnitAddressSearchSchema(Schema):
    """Schema per ricerca per indirizzo."""
    
    address_query = fields.String(
        required=True,
        validate=validate.Length(min=3, max=100),
        error_messages={'required': 'Query di ricerca per indirizzo obbligatoria'}
    )
    exact_match = fields.Boolean(missing=False)


# Inizializzazione schemi
property_unit_schema = PropertyUnitSchema()
property_units_schema = PropertyUnitSchema(many=True)
property_unit_create_schema = PropertyUnitCreateSchema()
property_unit_update_schema = PropertyUnitUpdateSchema()
property_unit_list_schema = PropertyUnitListSchema()
property_unit_stats_schema = PropertyUnitStatsSchema()
property_unit_duplicate_check_schema = PropertyUnitDuplicateCheckSchema()
property_unit_bulk_action_schema = PropertyUnitBulkActionSchema()
property_unit_by_type_schema = PropertyUnitByTypeSchema()
property_unit_by_company_schema = PropertyUnitByCompanySchema()
property_unit_occupancy_schema = PropertyUnitOccupancySchema()
property_unit_address_search_schema = PropertyUnitAddressSearchSchema()
