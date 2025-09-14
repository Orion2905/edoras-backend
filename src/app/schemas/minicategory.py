# Minicategory Schemas - Sistema Validazione Completo

from marshmallow import Schema, fields, validates, ValidationError, validate, pre_load, post_load
from datetime import datetime


class MinicategorySchema(Schema):
    """Schema per serializzazione completa di una minicategoria."""
    
    id = fields.Integer(dump_only=True)
    subcategory_id = fields.Integer(required=True, validate=validate.Range(min=1))
    name = fields.String(required=True, validate=validate.Length(min=1, max=100))
    description = fields.String(allow_none=True, validate=validate.Length(max=255))
    code = fields.String(allow_none=True, validate=validate.Length(max=20))
    is_active = fields.Boolean(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    
    # Relationships (quando necessario)
    subcategory = fields.Nested('SubcategorySchema', dump_only=True, exclude=['minicategories'])
    category = fields.Nested('CategorySchema', dump_only=True, exclude=['subcategories'])
    invoices_count = fields.Integer(dump_only=True)


class MinicategoryCreateSchema(Schema):
    """Schema per creazione nuova minicategoria."""
    
    subcategory_id = fields.Integer(
        required=True,
        validate=validate.Range(min=1),
        error_messages={'required': 'La sottocategoria è obbligatoria'}
    )
    name = fields.String(
        required=True, 
        validate=validate.Length(min=1, max=100),
        error_messages={'required': 'Il nome della minicategoria è obbligatorio'}
    )
    description = fields.String(
        allow_none=True, 
        validate=validate.Length(max=255),
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
            raise ValidationError('Il nome della minicategoria non può essere vuoto')
        
        # Controllo caratteri speciali
        if any(char in value for char in ['<', '>', '&', '"', "'"]):
            raise ValidationError('Il nome non può contenere caratteri speciali HTML')
    
    @validates('code')
    def validate_code(self, value):
        """Validazione personalizzata per il codice."""
        if value and not value.strip():
            raise ValidationError('Il codice non può essere una stringa vuota')
        
        if value and not value.replace('_', '').replace('-', '').isalnum():
            raise ValidationError('Il codice può contenere solo lettere, numeri, _ e -')
    
    @pre_load
    def clean_data(self, data, **kwargs):
        """Pulizia dati in input."""
        if isinstance(data, dict):
            # Trim stringhe
            for key in ['name', 'description', 'code']:
                if key in data and isinstance(data[key], str):
                    data[key] = data[key].strip() or None
        return data


class MinicategoryUpdateSchema(Schema):
    """Schema per aggiornamento minicategoria esistente."""
    
    subcategory_id = fields.Integer(
        validate=validate.Range(min=1),
        missing=None
    )
    name = fields.String(
        validate=validate.Length(min=1, max=100),
        missing=None
    )
    description = fields.String(
        allow_none=True, 
        validate=validate.Length(max=255),
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
        if value is not None:
            if not value or not value.strip():
                raise ValidationError('Il nome della minicategoria non può essere vuoto')
            
            if any(char in value for char in ['<', '>', '&', '"', "'"]):
                raise ValidationError('Il nome non può contenere caratteri speciali HTML')
    
    @validates('code')
    def validate_code(self, value):
        """Validazione personalizzata per il codice."""
        if value is not None:
            if value and not value.strip():
                raise ValidationError('Il codice non può essere una stringa vuota')
            
            if value and not value.replace('_', '').replace('-', '').isalnum():
                raise ValidationError('Il codice può contenere solo lettere, numeri, _ e -')
    
    @pre_load
    def clean_data(self, data, **kwargs):
        """Pulizia dati in input."""
        if isinstance(data, dict):
            # Trim stringhe
            for key in ['name', 'description', 'code']:
                if key in data and isinstance(data[key], str):
                    data[key] = data[key].strip() or None
        return data


class MinicategoryListSchema(Schema):
    """Schema per parametri di ricerca e filtri lista minicategorie."""
    
    search = fields.String(
        allow_none=True,
        validate=validate.Length(max=100),
        missing=None
    )
    subcategory_id = fields.Integer(
        allow_none=True,
        validate=validate.Range(min=1),
        missing=None
    )
    category_id = fields.Integer(
        allow_none=True,
        validate=validate.Range(min=1),
        missing=None
    )
    is_active = fields.Boolean(missing=True)
    sort_by = fields.String(
        validate=validate.OneOf(['name', 'code', 'created_at', 'updated_at']),
        missing='name'
    )
    sort_order = fields.String(
        validate=validate.OneOf(['asc', 'desc']),
        missing='asc'
    )
    page = fields.Integer(validate=validate.Range(min=1), missing=1)
    per_page = fields.Integer(validate=validate.Range(min=1, max=100), missing=20)
    
    # Filtri specifici
    has_invoices = fields.Boolean(missing=None)


class MinicategoryStatsSchema(Schema):
    """Schema per risposta statistiche minicategorie."""
    
    total_minicategories = fields.Integer()
    active_minicategories = fields.Integer()
    minicategories_with_invoices = fields.Integer()
    most_used_minicategory = fields.String(allow_none=True)
    least_used_minicategory = fields.String(allow_none=True)
    by_subcategory = fields.List(fields.Dict())
    by_category = fields.List(fields.Dict())


class MinicategoryDuplicateCheckSchema(Schema):
    """Schema per controllo duplicati minicategoria."""
    
    name = fields.String(required=True, validate=validate.Length(min=1, max=100))
    subcategory_id = fields.Integer(required=True, validate=validate.Range(min=1))
    code = fields.String(allow_none=True, validate=validate.Length(max=20))
    exclude_id = fields.Integer(allow_none=True, missing=None)
    
    @validates('name')
    def validate_name(self, value):
        """Validazione nome per controllo duplicati."""
        if not value or not value.strip():
            raise ValidationError('Il nome è obbligatorio per il controllo duplicati')


class MinicategoryBulkActionSchema(Schema):
    """Schema per azioni bulk su minicategorie."""
    
    minicategory_ids = fields.List(
        fields.Integer(validate=validate.Range(min=1)),
        required=True,
        validate=validate.Length(min=1, max=50)
    )
    action = fields.String(
        required=True,
        validate=validate.OneOf(['activate', 'deactivate', 'delete', 'move_to_subcategory'])
    )
    target_subcategory_id = fields.Integer(
        allow_none=True,
        validate=validate.Range(min=1),
        missing=None
    )
    
    @validates('minicategory_ids')
    def validate_minicategory_ids(self, value):
        """Validazione IDs minicategorie."""
        if not value:
            raise ValidationError('Almeno una minicategoria deve essere selezionata')
        
        # Controlla duplicati
        if len(value) != len(set(value)):
            raise ValidationError('IDs minicategoria duplicati non sono permessi')
    
    @post_load
    def validate_move_action(self, data, **kwargs):
        """Validazione speciale per azione di spostamento."""
        if data['action'] == 'move_to_subcategory':
            if not data.get('target_subcategory_id'):
                raise ValidationError('target_subcategory_id è obbligatorio per l\'azione move_to_subcategory')
        return data


class MinicategoryBySubcategorySchema(Schema):
    """Schema per ottenere minicategorie per sottocategoria."""
    
    subcategory_id = fields.Integer(required=True, validate=validate.Range(min=1))
    include_inactive = fields.Boolean(missing=False)


# Istanze globali degli schemi
minicategory_schema = MinicategorySchema()
minicategories_schema = MinicategorySchema(many=True)
minicategory_create_schema = MinicategoryCreateSchema()
minicategory_update_schema = MinicategoryUpdateSchema()
minicategory_list_schema = MinicategoryListSchema()
minicategory_stats_schema = MinicategoryStatsSchema()
minicategory_duplicate_check_schema = MinicategoryDuplicateCheckSchema()
minicategory_bulk_action_schema = MinicategoryBulkActionSchema()
minicategory_by_subcategory_schema = MinicategoryBySubcategorySchema()
