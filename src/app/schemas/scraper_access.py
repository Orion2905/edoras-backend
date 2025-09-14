# Scraper Access Schemas - Sistema Validazione Completo

from marshmallow import Schema, fields, validates, ValidationError, validate, pre_load
from datetime import datetime


class ScraperAccessSchema(Schema):
    """Schema per serializzazione completa di un accesso scraper."""
    
    id = fields.Integer(dump_only=True)
    platform_name = fields.String(required=True, validate=validate.Length(min=1, max=100))
    platform_type = fields.String(required=True, validate=validate.Length(min=1, max=50))
    platform_url = fields.String(allow_none=True, validate=validate.Length(max=255))
    access_data = fields.Dict(dump_only=True)  # Credenziali complete solo per admin
    access_data_masked = fields.Dict(dump_only=True)  # Credenziali mascherate per sicurezza
    is_active = fields.Boolean(dump_only=True)
    is_verified = fields.Boolean(dump_only=True)
    last_verified = fields.DateTime(dump_only=True, allow_none=True)
    last_scrape = fields.DateTime(dump_only=True, allow_none=True)
    scrape_frequency = fields.String(dump_only=True)
    auto_scrape = fields.Boolean(dump_only=True)
    notes = fields.String(dump_only=True, allow_none=True)
    config_json = fields.Dict(dump_only=True, allow_none=True)
    company_id = fields.Integer(dump_only=True)
    company_name = fields.String(dump_only=True)
    status_summary = fields.String(dump_only=True)
    is_scrape_due = fields.Boolean(dump_only=True)
    required_credentials = fields.List(fields.String(), dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


class ScraperAccessCreateSchema(Schema):
    """Schema per creazione nuovo accesso scraper."""
    
    platform_name = fields.String(
        required=True, 
        validate=validate.Length(min=1, max=100),
        error_messages={'required': 'Il nome della piattaforma è obbligatorio'}
    )
    platform_type = fields.String(
        required=True,
        validate=validate.OneOf(['energia', 'gas', 'telecom', 'acqua', 'banca', 'assicurazione']),
        error_messages={'required': 'Il tipo di piattaforma è obbligatorio'}
    )
    platform_url = fields.String(
        allow_none=True, 
        validate=validate.Length(max=255),
        missing=None
    )
    access_data = fields.Dict(
        required=True,
        error_messages={'required': 'I dati di accesso sono obbligatori'}
    )
    scrape_frequency = fields.String(
        validate=validate.OneOf(['hourly', 'daily', 'weekly', 'monthly']),
        missing='daily'
    )
    auto_scrape = fields.Boolean(missing=True)
    notes = fields.String(
        allow_none=True, 
        validate=validate.Length(max=1000),
        missing=None
    )
    config_json = fields.Dict(allow_none=True, missing=None)
    company_id = fields.Integer(
        required=True,
        error_messages={'required': 'L\'ID dell\'azienda è obbligatorio'}
    )
    
    @validates('platform_name')
    def validate_platform_name(self, value):
        """Validazione personalizzata per il nome piattaforma."""
        if not value or not value.strip():
            raise ValidationError('Il nome della piattaforma non può essere vuoto')
        
        # Controllo caratteri speciali
        if any(char in value for char in ['<', '>', '&', '"', "'"]):
            raise ValidationError('Il nome della piattaforma contiene caratteri non validi')
    
    @validates('access_data')
    def validate_access_data(self, value):
        """Validazione dei dati di accesso."""
        if not isinstance(value, dict):
            raise ValidationError('I dati di accesso devono essere un oggetto JSON valido')
        
        if not value:
            raise ValidationError('I dati di accesso non possono essere vuoti')
        
        # Verifica che almeno username e password siano presenti
        if 'username' not in value or not value.get('username'):
            raise ValidationError('Username è obbligatorio nei dati di accesso')
        
        if 'password' not in value or not value.get('password'):
            raise ValidationError('Password è obbligatoria nei dati di accesso')
    
    @validates('platform_url')
    def validate_platform_url(self, value):
        """Validazione URL piattaforma."""
        if value and value.strip():
            import re
            url_pattern = re.compile(
                r'^https?://'  # http:// or https://
                r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
                r'localhost|'  # localhost...
                r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
                r'(?::\d+)?'  # optional port
                r'(?:/?|[/?]\S+)$', re.IGNORECASE)
            
            if not url_pattern.match(value.strip()):
                raise ValidationError('URL della piattaforma non è valido')


class ScraperAccessUpdateSchema(Schema):
    """Schema per aggiornamento accesso scraper."""
    
    platform_name = fields.String(
        validate=validate.Length(min=1, max=100),
        allow_none=True
    )
    platform_type = fields.String(
        validate=validate.OneOf(['energia', 'gas', 'telecom', 'acqua', 'banca', 'assicurazione']),
        allow_none=True
    )
    platform_url = fields.String(
        validate=validate.Length(max=255),
        allow_none=True
    )
    access_data = fields.Dict(allow_none=True)
    is_active = fields.Boolean(allow_none=True)
    scrape_frequency = fields.String(
        validate=validate.OneOf(['hourly', 'daily', 'weekly', 'monthly']),
        allow_none=True
    )
    auto_scrape = fields.Boolean(allow_none=True)
    notes = fields.String(
        validate=validate.Length(max=1000),
        allow_none=True
    )
    config_json = fields.Dict(allow_none=True)
    
    @validates('platform_name')
    def validate_platform_name(self, value):
        """Validazione personalizzata per il nome piattaforma."""
        if value is not None:
            if not value or not value.strip():
                raise ValidationError('Il nome della piattaforma non può essere vuoto')
            
            # Controllo caratteri speciali
            if any(char in value for char in ['<', '>', '&', '"', "'"]):
                raise ValidationError('Il nome della piattaforma contiene caratteri non validi')
    
    @validates('access_data')
    def validate_access_data(self, value):
        """Validazione dei dati di accesso."""
        if value is not None:
            if not isinstance(value, dict):
                raise ValidationError('I dati di accesso devono essere un oggetto JSON valido')
            
            if not value:
                raise ValidationError('I dati di accesso non possono essere vuoti')
            
            # Verifica che almeno username e password siano presenti se forniti
            if 'username' in value and not value.get('username'):
                raise ValidationError('Username non può essere vuoto')
            
            if 'password' in value and not value.get('password'):
                raise ValidationError('Password non può essere vuota')
    
    @validates('platform_url')
    def validate_platform_url(self, value):
        """Validazione URL piattaforma."""
        if value is not None and value and value.strip():
            import re
            url_pattern = re.compile(
                r'^https?://'  # http:// or https://
                r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
                r'localhost|'  # localhost...
                r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
                r'(?::\d+)?'  # optional port
                r'(?:/?|[/?]\S+)$', re.IGNORECASE)
            
            if not url_pattern.match(value.strip()):
                raise ValidationError('URL della piattaforma non è valido')


class ScraperAccessListSchema(Schema):
    """Schema per lista accessi scraper con filtri."""
    
    page = fields.Integer(validate=validate.Range(min=1), missing=1)
    per_page = fields.Integer(validate=validate.Range(min=1, max=100), missing=20)
    platform_type = fields.String(allow_none=True)
    company_id = fields.Integer(allow_none=True)
    is_active = fields.Boolean(allow_none=True, missing=True)
    is_verified = fields.Boolean(allow_none=True)
    auto_scrape = fields.Boolean(allow_none=True)
    scrape_due = fields.Boolean(allow_none=True)  # Solo accessi che richiedono scraping
    search = fields.String(allow_none=True, validate=validate.Length(max=100))
    sort_by = fields.String(
        validate=validate.OneOf(['platform_name', 'platform_type', 'company_name', 'last_verified', 'last_scrape', 'created_at']),
        missing='platform_name'
    )
    sort_order = fields.String(
        validate=validate.OneOf(['asc', 'desc']),
        missing='asc'
    )


class ScraperAccessStatsSchema(Schema):
    """Schema per statistiche accessi scraper."""
    
    total_accesses = fields.Integer(dump_only=True)
    active_accesses = fields.Integer(dump_only=True)
    verified_accesses = fields.Integer(dump_only=True)
    auto_scrape_enabled = fields.Integer(dump_only=True)
    pending_verification = fields.Integer(dump_only=True)
    scrape_due_count = fields.Integer(dump_only=True)
    by_platform_type = fields.Dict(dump_only=True)
    by_company = fields.Dict(dump_only=True)
    recent_scrapes = fields.Integer(dump_only=True)  # Ultimi 7 giorni


class ScraperAccessDuplicateCheckSchema(Schema):
    """Schema per controllo duplicati accessi scraper."""
    
    platform_name = fields.String(required=True)
    company_id = fields.Integer(required=True)
    exclude_id = fields.Integer(allow_none=True, missing=None)


class ScraperAccessBulkActionSchema(Schema):
    """Schema per azioni bulk su accessi scraper."""
    
    ids = fields.List(
        fields.Integer(validate=validate.Range(min=1)),
        required=True,
        validate=validate.Length(min=1, max=100),
        error_messages={'required': 'Lista di ID è obbligatoria'}
    )
    action = fields.String(
        required=True,
        validate=validate.OneOf(['activate', 'deactivate', 'enable_auto_scrape', 'disable_auto_scrape', 'verify_credentials', 'delete']),
        error_messages={'required': 'Azione da eseguire è obbligatoria'}
    )


class ScraperAccessVerificationSchema(Schema):
    """Schema per verifica credenziali accesso scraper."""
    
    force_verify = fields.Boolean(missing=False)
    test_connection = fields.Boolean(missing=True)


class ScraperAccessCredentialsSchema(Schema):
    """Schema per aggiornamento credenziali specifiche."""
    
    credentials = fields.Dict(
        required=True,
        error_messages={'required': 'Le credenziali sono obbligatorie'}
    )
    verify_after_update = fields.Boolean(missing=True)
    
    @validates('credentials')
    def validate_credentials(self, value):
        """Validazione credenziali."""
        if not isinstance(value, dict):
            raise ValidationError('Le credenziali devono essere un oggetto JSON valido')
        
        if not value:
            raise ValidationError('Le credenziali non possono essere vuote')
        
        # Verifica che non ci siano chiavi vuote
        for key, val in value.items():
            if not key or not key.strip():
                raise ValidationError('Le chiavi delle credenziali non possono essere vuote')


class ScraperAccessPlatformTypesSchema(Schema):
    """Schema per tipi di piattaforma supportati."""
    
    supported_platforms = fields.Dict(dump_only=True)
    platform_types = fields.List(fields.String(), dump_only=True)


# Inizializzazione schemi
scraper_access_schema = ScraperAccessSchema()
scraper_accesses_schema = ScraperAccessSchema(many=True)
scraper_access_create_schema = ScraperAccessCreateSchema()
scraper_access_update_schema = ScraperAccessUpdateSchema()
scraper_access_list_schema = ScraperAccessListSchema()
scraper_access_stats_schema = ScraperAccessStatsSchema()
scraper_access_duplicate_check_schema = ScraperAccessDuplicateCheckSchema()
scraper_access_bulk_action_schema = ScraperAccessBulkActionSchema()
scraper_access_verification_schema = ScraperAccessVerificationSchema()
scraper_access_credentials_schema = ScraperAccessCredentialsSchema()
scraper_access_platform_types_schema = ScraperAccessPlatformTypesSchema()
