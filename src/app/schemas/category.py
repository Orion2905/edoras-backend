# Category Schemas - Sistema Validazione Completo

from marshmallow import Schema, fields, validates, ValidationError, validate, pre_load
from datetime import datetime


class CategorySchema(Schema):
    """Schema per serializzazione completa di una categoria."""
    
    id = fields.Integer(dump_only=True)
    name = fields.String(required=True, validate=validate.Length(min=1, max=100))
    description = fields.String(allow_none=True, validate=validate.Length(max=255))
    code = fields.String(allow_none=True, validate=validate.Length(max=20))
    is_active = fields.Boolean(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    subcategories_count = fields.Integer(dump_only=True)
    
    # Relationships (quando necessario)
    subcategories = fields.List(fields.Nested('SubcategorySchema', exclude=['category']), dump_only=True)
    invoices_count = fields.Integer(dump_only=True)


class CategoryCreateSchema(Schema):
    """Schema per creazione nuova categoria."""
    
    name = fields.String(
        required=True, 
        validate=validate.Length(min=1, max=100),
        error_messages={'required': 'Il nome della categoria è obbligatorio'}
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
            raise ValidationError('Il nome della categoria non può essere vuoto')
        
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


class CategoryUpdateSchema(Schema):
    """Schema per aggiornamento categoria esistente."""
    
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
                raise ValidationError('Il nome della categoria non può essere vuoto')
            
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


class CategoryListSchema(Schema):
    """Schema per parametri di ricerca e filtri lista categorie."""
    
    search = fields.String(
        allow_none=True,
        validate=validate.Length(max=100),
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
    has_subcategories = fields.Boolean(missing=None)
    has_invoices = fields.Boolean(missing=None)


class CategoryStatsSchema(Schema):
    """Schema per risposta statistiche categorie."""
    
    total_categories = fields.Integer()
    active_categories = fields.Integer()
    categories_with_subcategories = fields.Integer()
    categories_with_invoices = fields.Integer()
    most_used_category = fields.String(allow_none=True)
    least_used_category = fields.String(allow_none=True)


class CategoryDuplicateCheckSchema(Schema):
    """Schema per controllo duplicati categoria."""
    
    name = fields.String(required=True, validate=validate.Length(min=1, max=100))
    code = fields.String(allow_none=True, validate=validate.Length(max=20))
    exclude_id = fields.Integer(allow_none=True, missing=None)
    
    @validates('name')
    def validate_name(self, value):
        """Validazione nome per controllo duplicati."""
        if not value or not value.strip():
            raise ValidationError('Il nome è obbligatorio per il controllo duplicati')


class CategoryBulkActionSchema(Schema):
    """Schema per azioni bulk su categorie."""
    
    category_ids = fields.List(
        fields.Integer(validate=validate.Range(min=1)),
        required=True,
        validate=validate.Length(min=1, max=50)
    )
    action = fields.String(
        required=True,
        validate=validate.OneOf(['activate', 'deactivate', 'delete'])
    )
    
    @validates('category_ids')
    def validate_category_ids(self, value):
        """Validazione IDs categorie."""
        if not value:
            raise ValidationError('Almeno una categoria deve essere selezionata')
        
        # Controlla duplicati
        if len(value) != len(set(value)):
            raise ValidationError('IDs categoria duplicati non sono permessi')


# Istanze globali degli schemi
category_schema = CategorySchema()
categories_schema = CategorySchema(many=True)
category_create_schema = CategoryCreateSchema()
category_update_schema = CategoryUpdateSchema()
category_list_schema = CategoryListSchema()
category_stats_schema = CategoryStatsSchema()
category_duplicate_check_schema = CategoryDuplicateCheckSchema()
category_bulk_action_schema = CategoryBulkActionSchema()
