# Company Schemas

from marshmallow import Schema, fields, validate, post_load
from ..models.company import Company


class CompanySchema(Schema):
    """Schema per la serializzazione delle aziende."""
    
    id = fields.Integer(dump_only=True)
    name = fields.String(required=True, validate=validate.Length(min=2, max=200))
    legal_name = fields.String(validate=validate.Length(max=200), allow_none=True)
    display_name = fields.String(dump_only=True)
    vat_number = fields.String(validate=validate.Length(max=20), allow_none=True)
    tax_code = fields.String(validate=validate.Length(max=20), allow_none=True)
    
    # Informazioni di contatto
    email = fields.Email(validate=validate.Length(max=120), allow_none=True)
    phone = fields.String(validate=validate.Length(max=20), allow_none=True)
    website = fields.Url(allow_none=True)
    
    # Indirizzo
    address = fields.String(validate=validate.Length(max=255), allow_none=True)
    city = fields.String(validate=validate.Length(max=100), allow_none=True)
    province = fields.String(validate=validate.Length(max=10), allow_none=True)
    postal_code = fields.String(validate=validate.Length(max=10), allow_none=True)
    country = fields.String(validate=validate.Length(min=2, max=2), missing='IT')
    full_address = fields.String(dump_only=True)
    
    # Status
    is_active = fields.Boolean(dump_only=True)
    
    # Timestamps
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    
    # Relazioni (opzionali)
    users_count = fields.Integer(dump_only=True)
    property_units_count = fields.Integer(dump_only=True)
    scraper_accesses_count = fields.Integer(dump_only=True)
    total_invoices_amount = fields.Float(dump_only=True)


class CompanyCreateSchema(Schema):
    """Schema per la creazione di una nuova azienda."""
    
    name = fields.String(required=True, validate=validate.Length(min=2, max=200))
    legal_name = fields.String(validate=validate.Length(max=200), allow_none=True)
    vat_number = fields.String(validate=validate.Length(max=20), allow_none=True)
    tax_code = fields.String(validate=validate.Length(max=20), allow_none=True)
    
    # Informazioni di contatto
    email = fields.Email(validate=validate.Length(max=120), allow_none=True)
    phone = fields.String(validate=validate.Length(max=20), allow_none=True)
    website = fields.Url(allow_none=True)
    
    # Indirizzo
    address = fields.String(validate=validate.Length(max=255), allow_none=True)
    city = fields.String(validate=validate.Length(max=100), allow_none=True)
    province = fields.String(validate=validate.Length(max=10), allow_none=True)
    postal_code = fields.String(validate=validate.Length(max=10), allow_none=True)
    country = fields.String(validate=validate.Length(min=2, max=2), missing='IT')


class CompanyUpdateSchema(Schema):
    """Schema per l'aggiornamento di un'azienda esistente."""
    
    name = fields.String(validate=validate.Length(min=2, max=200), allow_none=True)
    legal_name = fields.String(validate=validate.Length(max=200), allow_none=True)
    vat_number = fields.String(validate=validate.Length(max=20), allow_none=True)
    tax_code = fields.String(validate=validate.Length(max=20), allow_none=True)
    
    # Informazioni di contatto
    email = fields.Email(validate=validate.Length(max=120), allow_none=True)
    phone = fields.String(validate=validate.Length(max=20), allow_none=True)
    website = fields.Url(allow_none=True)
    
    # Indirizzo
    address = fields.String(validate=validate.Length(max=255), allow_none=True)
    city = fields.String(validate=validate.Length(max=100), allow_none=True)
    province = fields.String(validate=validate.Length(max=10), allow_none=True)
    postal_code = fields.String(validate=validate.Length(max=10), allow_none=True)
    country = fields.String(validate=validate.Length(min=2, max=2), allow_none=True)
    
    # Status
    is_active = fields.Boolean(allow_none=True)


# Istanze degli schemi per l'uso nell'API
company_schema = CompanySchema()
companies_schema = CompanySchema(many=True)
company_create_schema = CompanyCreateSchema()
company_update_schema = CompanyUpdateSchema()
