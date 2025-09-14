# Subcategory Schemas - Sistema Validazione Completo

from marshmallow import Schema, fields, validates, ValidationError, validate, pre_load, post_load
from datetime import datetime


class SubcategorySchema(Schema):
    """Schema per serializzazione completa di una sottocategoria."""
    
    id = fields.Integer(dump_only=True)
    category_id = fields.Integer(required=True, validate=validate.Range(min=1))
    name = fields.String(required=True, validate=validate.Length(min=1, max=100))
    description = fields.String(allow_none=True, validate=validate.Length(max=255))
    code = fields.String(allow_none=True, validate=validate.Length(max=20))
    is_active = fields.Boolean(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    
    # Relationships (quando necessario)
    category = fields.Nested('CategorySchema', dump_only=True, exclude=['subcategories'])
    minicategories = fields.List(fields.Nested('MinicategorySchema', exclude=['subcategory']), dump_only=True)
    minicategories_count = fields.Integer(dump_only=True)
    invoices_count = fields.Integer(dump_only=True)


class SubcategoryCreateSchema(Schema):
    """Schema per creazione nuova sottocategoria."""
    
    category_id = fields.Integer(
        required=True,
        validate=validate.Range(min=1),
        error_messages={'required': 'La categoria è obbligatoria'}
    )
    name = fields.String(
        required=True, 
        validate=validate.Length(min=1, max=100),
        error_messages={'required': 'Il nome della sottocategoria è obbligatorio'}
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
            raise ValidationError('Il nome della sottocategoria non può essere vuoto')
        
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


class SubcategoryUpdateSchema(Schema):
    """Schema per aggiornamento sottocategoria esistente."""
    
    category_id = fields.Integer(
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
                raise ValidationError('Il nome della sottocategoria non può essere vuoto')
            
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


class SubcategoryListSchema(Schema):
    """Schema per parametri di ricerca e filtri lista sottocategorie."""
    
    search = fields.String(
        allow_none=True,
        validate=validate.Length(max=100),
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
    has_minicategories = fields.Boolean(missing=None)
    has_invoices = fields.Boolean(missing=None)


class SubcategoryStatsSchema(Schema):
    """Schema per risposta statistiche sottocategorie."""
    
    total_subcategories = fields.Integer()
    active_subcategories = fields.Integer()
    subcategories_with_minicategories = fields.Integer()
    subcategories_with_invoices = fields.Integer()
    most_used_subcategory = fields.String(allow_none=True)
    least_used_subcategory = fields.String(allow_none=True)
    by_category = fields.List(fields.Dict())
    average_minicategories_per_subcategory = fields.Float()


class SubcategoryDuplicateCheckSchema(Schema):
    """Schema per controllo duplicati sottocategoria."""
    
    name = fields.String(required=True, validate=validate.Length(min=1, max=100))
    category_id = fields.Integer(required=True, validate=validate.Range(min=1))
    code = fields.String(allow_none=True, validate=validate.Length(max=20))
    exclude_id = fields.Integer(allow_none=True, missing=None)
    
    @validates('name')
    def validate_name(self, value):
        """Validazione nome per controllo duplicati."""
        if not value or not value.strip():
            raise ValidationError('Il nome è obbligatorio per il controllo duplicati')


class SubcategoryBulkActionSchema(Schema):
    """Schema per azioni bulk su sottocategorie."""
    
    subcategory_ids = fields.List(
        fields.Integer(validate=validate.Range(min=1)),
        required=True,
        validate=validate.Length(min=1, max=50)
    )
    action = fields.String(
        required=True,
        validate=validate.OneOf(['activate', 'deactivate', 'delete', 'move_to_category'])
    )
    target_category_id = fields.Integer(
        allow_none=True,
        validate=validate.Range(min=1),
        missing=None
    )
    
    @validates('subcategory_ids')
    def validate_subcategory_ids(self, value):
        """Validazione IDs sottocategorie."""
        if not value:
            raise ValidationError('Almeno una sottocategoria deve essere selezionata')
        
        # Controlla duplicati
        if len(value) != len(set(value)):
            raise ValidationError('IDs sottocategoria duplicati non sono permessi')
    
    @post_load
    def validate_move_action(self, data, **kwargs):
        """Validazione speciale per azione di spostamento."""
        if data['action'] == 'move_to_category':
            if not data.get('target_category_id'):
                raise ValidationError('target_category_id è obbligatorio per l\'azione move_to_category')
        return data


class SubcategoryByCategorySchema(Schema):
    """Schema per ottenere sottocategorie per categoria."""
    
    category_id = fields.Integer(required=True, validate=validate.Range(min=1))
    include_inactive = fields.Boolean(missing=False)


class SubcategoryHierarchySchema(Schema):
    """Schema per visualizzazione gerarchica completa."""
    
    category_id = fields.Integer(allow_none=True, validate=validate.Range(min=1))
    include_inactive = fields.Boolean(missing=False)
    include_minicategories = fields.Boolean(missing=True)
    include_counts = fields.Boolean(missing=True)


# Istanze globali degli schemi
subcategory_schema = SubcategorySchema()
subcategories_schema = SubcategorySchema(many=True)
subcategory_create_schema = SubcategoryCreateSchema()
subcategory_update_schema = SubcategoryUpdateSchema()
subcategory_list_schema = SubcategoryListSchema()
subcategory_stats_schema = SubcategoryStatsSchema()
subcategory_duplicate_check_schema = SubcategoryDuplicateCheckSchema()
subcategory_bulk_action_schema = SubcategoryBulkActionSchema()
subcategory_by_category_schema = SubcategoryByCategorySchema()
subcategory_hierarchy_schema = SubcategoryHierarchySchema()
