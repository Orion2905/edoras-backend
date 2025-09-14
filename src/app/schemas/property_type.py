# Property Type Schemas - Sistema Validazione Completo

from marshmallow import Schema, fields, validates, ValidationError, validate, pre_load
from datetime import datetime


class PropertyTypeSchema(Schema):
    """Schema per serializzazione completa di un tipo di proprietà."""
    
    id = fields.Integer(dump_only=True)
    name = fields.String(required=True, validate=validate.Length(min=1, max=100))
    description = fields.String(allow_none=True)
    code = fields.String(allow_none=True, validate=validate.Length(max=20))
    is_active = fields.Boolean(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    
    # Campi calcolati
    units_count = fields.Integer(dump_only=True)
    
    # Relationships (quando necessario)
    property_units = fields.List(fields.Nested('PropertyUnitSchema', exclude=['property_type']), dump_only=True)


class PropertyTypeCreateSchema(Schema):
    """Schema per creazione nuovo tipo di proprietà."""
    
    name = fields.String(
        required=True, 
        validate=validate.Length(min=1, max=100),
        error_messages={'required': 'Il nome del tipo di proprietà è obbligatorio'}
    )
    description = fields.String(
        allow_none=True,
        missing=None
    )
    code = fields.String(
        allow_none=True,
        validate=validate.Length(max=20),
        missing=None
    )
    
    @validates('name')
    def validate_name(self, value):
        """Validazione personalizzata per il nome."""
        if not value or not value.strip():
            raise ValidationError('Il nome del tipo di proprietà non può essere vuoto')
        
        # Controllo caratteri speciali
        if any(char in value for char in ['<', '>', '&', '"', "'"]):
            raise ValidationError('Il nome del tipo di proprietà contiene caratteri non validi')
        
        # Controllo lunghezza minima significativa
        if len(value.strip()) < 2:
            raise ValidationError('Il nome del tipo di proprietà deve essere di almeno 2 caratteri')
    
    @validates('code')
    def validate_code(self, value):
        """Validazione personalizzata per il codice."""
        if value and value.strip():
            # Il codice deve essere alfanumerico
            if not value.strip().replace('_', '').replace('-', '').isalnum():
                raise ValidationError('Il codice deve contenere solo caratteri alfanumerici, trattini e underscore')
            
            # Controllo lunghezza minima
            if len(value.strip()) < 2:
                raise ValidationError('Il codice deve essere di almeno 2 caratteri')


class PropertyTypeUpdateSchema(Schema):
    """Schema per aggiornamento tipo di proprietà."""
    
    name = fields.String(
        validate=validate.Length(min=1, max=100),
        allow_none=True
    )
    description = fields.String(allow_none=True)
    code = fields.String(
        validate=validate.Length(max=20),
        allow_none=True
    )
    is_active = fields.Boolean(allow_none=True)
    
    @validates('name')
    def validate_name(self, value):
        """Validazione personalizzata per il nome."""
        if value is not None:
            if not value or not value.strip():
                raise ValidationError('Il nome del tipo di proprietà non può essere vuoto')
            
            # Controllo caratteri speciali
            if any(char in value for char in ['<', '>', '&', '"', "'"]):
                raise ValidationError('Il nome del tipo di proprietà contiene caratteri non validi')
            
            # Controllo lunghezza minima significativa
            if len(value.strip()) < 2:
                raise ValidationError('Il nome del tipo di proprietà deve essere di almeno 2 caratteri')
    
    @validates('code')
    def validate_code(self, value):
        """Validazione personalizzata per il codice."""
        if value is not None and value and value.strip():
            # Il codice deve essere alfanumerico
            if not value.strip().replace('_', '').replace('-', '').isalnum():
                raise ValidationError('Il codice deve contenere solo caratteri alfanumerici, trattini e underscore')
            
            # Controllo lunghezza minima
            if len(value.strip()) < 2:
                raise ValidationError('Il codice deve essere di almeno 2 caratteri')


class PropertyTypeListSchema(Schema):
    """Schema per lista tipi di proprietà con filtri."""
    
    page = fields.Integer(validate=validate.Range(min=1), missing=1)
    per_page = fields.Integer(validate=validate.Range(min=1, max=100), missing=20)
    is_active = fields.Boolean(allow_none=True, missing=True)
    search = fields.String(allow_none=True, validate=validate.Length(max=100))
    sort_by = fields.String(
        validate=validate.OneOf(['name', 'code', 'units_count', 'created_at']),
        missing='name'
    )
    sort_order = fields.String(
        validate=validate.OneOf(['asc', 'desc']),
        missing='asc'
    )


class PropertyTypeStatsSchema(Schema):
    """Schema per statistiche tipi di proprietà."""
    
    total_types = fields.Integer(dump_only=True)
    active_types = fields.Integer(dump_only=True)
    inactive_types = fields.Integer(dump_only=True)
    total_units = fields.Integer(dump_only=True)
    most_used_type = fields.String(dump_only=True)
    least_used_type = fields.String(dump_only=True)
    types_with_units = fields.Integer(dump_only=True)
    types_without_units = fields.Integer(dump_only=True)
    units_distribution = fields.Dict(dump_only=True)  # {type_name: count}


class PropertyTypeDuplicateCheckSchema(Schema):
    """Schema per controllo duplicati tipi di proprietà."""
    
    name = fields.String(required=True)
    code = fields.String(allow_none=True)
    exclude_id = fields.Integer(allow_none=True, missing=None)


class PropertyTypeBulkActionSchema(Schema):
    """Schema per azioni bulk su tipi di proprietà."""
    
    ids = fields.List(
        fields.Integer(validate=validate.Range(min=1)),
        required=True,
        validate=validate.Length(min=1, max=50),
        error_messages={'required': 'Lista di ID è obbligatoria'}
    )
    action = fields.String(
        required=True,
        validate=validate.OneOf(['activate', 'deactivate', 'delete']),
        error_messages={'required': 'Azione da eseguire è obbligatoria'}
    )


class PropertyTypeUnitsSchema(Schema):
    """Schema per ottenere unità per tipo di proprietà."""
    
    include_inactive_units = fields.Boolean(missing=False)
    include_unit_details = fields.Boolean(missing=True)


class PropertyTypeValidationSchema(Schema):
    """Schema per validazione tipo di proprietà."""
    
    name = fields.String(required=True)
    code = fields.String(allow_none=True)
    
    @validates('name')
    def validate_name_format(self, value):
        """Validazione formato nome per tipi standard."""
        if not value or not value.strip():
            raise ValidationError('Nome obbligatorio')
        
        # Lista tipi comuni per suggerimenti
        common_types = [
            'Villa', 'Appartamento', 'Attico', 'Loft', 'Monolocale', 'Bilocale', 
            'Trilocale', 'Quadrilocale', 'Ufficio', 'Negozio', 'Magazzino', 
            'Capannone', 'Laboratorio', 'Showroom', 'Garage', 'Box Auto',
            'Cantina', 'Soffitta', 'Terreno', 'Rustico', 'Casale'
        ]
        
        # Non è un errore, ma potremmo fornire suggerimenti
        # Il controllo è puramente informativo


class PropertyTypeTemplateSchema(Schema):
    """Schema per template tipi di proprietà predefiniti."""
    
    category = fields.String(
        validate=validate.OneOf(['residenziale', 'commerciale', 'industriale', 'altro']),
        missing='residenziale'
    )


# Inizializzazione schemi
property_type_schema = PropertyTypeSchema()
property_types_schema = PropertyTypeSchema(many=True)
property_type_create_schema = PropertyTypeCreateSchema()
property_type_update_schema = PropertyTypeUpdateSchema()
property_type_list_schema = PropertyTypeListSchema()
property_type_stats_schema = PropertyTypeStatsSchema()
property_type_duplicate_check_schema = PropertyTypeDuplicateCheckSchema()
property_type_bulk_action_schema = PropertyTypeBulkActionSchema()
property_type_units_schema = PropertyTypeUnitsSchema()
property_type_validation_schema = PropertyTypeValidationSchema()
property_type_template_schema = PropertyTypeTemplateSchema()
