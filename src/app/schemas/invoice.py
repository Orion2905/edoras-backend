# Invoice Schemas - Sistema CRUD Completo

from marshmallow import Schema, fields, validate, validates, ValidationError
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from datetime import date
from decimal import Decimal
from ..models.invoice import Invoice
from ..models.company import Company


class InvoiceSchema(SQLAlchemyAutoSchema):
    """Schema per la serializzazione completa delle fatture."""
    
    class Meta:
        model = Invoice
        load_instance = True
        
    # Campi computati
    company_name = fields.Method("get_company_name")
    category_path = fields.Method("get_category_path")
    vat_amount = fields.Method("get_vat_amount")
    
    def get_company_name(self, obj):
        """Ritorna il nome dell'azienda."""
        return obj.company.display_name if obj.company else None
    
    def get_category_path(self, obj):
        """Ritorna il percorso completo della categoria."""
        try:
            return obj.get_full_category_path()
        except:
            return None
    
    def get_vat_amount(self, obj):
        """Calcola l'importo IVA."""
        try:
            return float(obj.calculate_vat()) if obj.calculate_vat() else 0.0
        except:
            return 0.0


class InvoiceCreateSchema(Schema):
    """Schema per la creazione di nuove fatture."""
    
    # Obbligatori
    company_id = fields.Integer(required=True, validate=validate.Range(min=1))
    supplier = fields.String(required=True, validate=validate.Length(min=1, max=255))
    invoice_number = fields.String(required=True, validate=validate.Length(min=1, max=100))
    invoice_date = fields.Date(required=True)
    
    # Opzionali
    supplier_vat = fields.String(validate=validate.Length(max=20))
    article_description = fields.String()
    quantity = fields.Decimal(places=4, validate=validate.Range(min=0))
    unit_price_with_vat = fields.Decimal(places=4, validate=validate.Range(min=0))
    total_price_with_vat = fields.Decimal(places=4, validate=validate.Range(min=0))
    document_status = fields.String(validate=validate.OneOf(['draft', 'receipt', 'delivery_note', 'invoice']))
    is_final = fields.Boolean()
    notes = fields.String()
    
    @validates('company_id')
    def validate_company_exists(self, value):
        """Verifica che l'azienda esista."""
        company = Company.query.get(value)
        if not company:
            raise ValidationError('Azienda non trovata')
    
    @validates('invoice_date')
    def validate_invoice_date(self, value):
        """Verifica che la data non sia futura."""
        if value > date.today():
            raise ValidationError('La data fattura non può essere futura')


class InvoiceUpdateSchema(Schema):
    """Schema per l'aggiornamento delle fatture."""
    
    # Solo campi modificabili
    article_description = fields.String()
    quantity = fields.Decimal(places=4, validate=validate.Range(min=0))
    unit_price_with_vat = fields.Decimal(places=4, validate=validate.Range(min=0))
    total_price_with_vat = fields.Decimal(places=4, validate=validate.Range(min=0))
    notes = fields.String()
    category_id = fields.Integer(validate=validate.Range(min=1))
    subcategory_id = fields.Integer(validate=validate.Range(min=1))
    minicategory_id = fields.Integer(validate=validate.Range(min=1))


class InvoiceListSchema(Schema):
    """Schema per i filtri della lista fatture."""
    
    # Filtri di ricerca
    search = fields.String()
    supplier = fields.String()
    supplier_vat = fields.String()
    invoice_number = fields.String()
    
    # Filtri per date
    start_date = fields.Date()
    end_date = fields.Date()
    year = fields.Integer(validate=validate.Range(min=2000, max=2100))
    month = fields.Integer(validate=validate.Range(min=1, max=12))
    
    # Filtri per importi
    min_amount = fields.Decimal(places=2, validate=validate.Range(min=0))
    max_amount = fields.Decimal(places=2, validate=validate.Range(min=0))
    
    # Filtri per categorie
    category_id = fields.Integer(validate=validate.Range(min=1))
    subcategory_id = fields.Integer(validate=validate.Range(min=1))
    minicategory_id = fields.Integer(validate=validate.Range(min=1))
    
    # Filtri per azienda
    company_id = fields.Integer(validate=validate.Range(min=1))
    
    # Filtri per stato
    document_status = fields.String(validate=validate.OneOf(['draft', 'receipt', 'delivery_note', 'invoice']))
    is_final = fields.Boolean()
    awaiting_invoice = fields.Boolean()
    is_processed = fields.Boolean()
    is_validated = fields.Boolean()
    
    # Opzioni di visualizzazione
    include_categories = fields.Boolean()
    include_company = fields.Boolean()
    include_totals = fields.Boolean()
    
    # Paginazione e ordinamento
    page = fields.Integer(validate=validate.Range(min=1))
    per_page = fields.Integer(validate=validate.Range(min=1, max=100))
    sort_by = fields.String()
    sort_order = fields.String(validate=validate.OneOf(['asc', 'desc']))


class InvoiceWorkflowSchema(Schema):
    """Schema per azioni di workflow."""
    
    action = fields.String(
        required=True,
        validate=validate.OneOf([
            'mark_as_receipt',
            'mark_as_delivery_note', 
            'convert_to_invoice',
            'link_to_invoice',
            'mark_as_processed',
            'mark_as_validated'
        ])
    )
    temp_reference = fields.String()
    linked_invoice_id = fields.Integer(validate=validate.Range(min=1))
    notes = fields.String()


class InvoiceDuplicateCheckSchema(Schema):
    """Schema per controllo duplicati."""
    
    supplier_vat = fields.String(required=True)
    total_amount = fields.Decimal(places=2, required=True, validate=validate.Range(min=0))
    invoice_date = fields.Date(required=True)
    tolerance_days = fields.Integer(validate=validate.Range(min=0, max=30))
    tolerance_amount = fields.Decimal(places=2, validate=validate.Range(min=0, max=100))


# Istanze schema per utilizzo nell'app
invoice_schema = InvoiceSchema()
invoices_schema = InvoiceSchema(many=True)
invoice_create_schema = InvoiceCreateSchema()
invoice_update_schema = InvoiceUpdateSchema()
invoice_list_schema = InvoiceListSchema()
invoice_workflow_schema = InvoiceWorkflowSchema()
invoice_duplicate_check_schema = InvoiceDuplicateCheckSchema()
