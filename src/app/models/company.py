# Company Model

from ..extensions import db
from .base import BaseModel


class Company(BaseModel):
    """Modello per le aziende/organizzazioni."""
    
    __tablename__ = 'companies'
    
    # Campi base
    name = db.Column(db.String(200), nullable=False, index=True)
    legal_name = db.Column(db.String(200), nullable=True)  # Ragione sociale
    vat_number = db.Column(db.String(20), unique=True, nullable=True, index=True)  # Partita IVA
    tax_code = db.Column(db.String(20), unique=True, nullable=True, index=True)  # Codice Fiscale
    
    # Informazioni di contatto
    email = db.Column(db.String(120), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    website = db.Column(db.String(255), nullable=True)
    
    # Indirizzo
    address = db.Column(db.String(255), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    province = db.Column(db.String(10), nullable=True)
    postal_code = db.Column(db.String(10), nullable=True)
    country = db.Column(db.String(2), default='IT', nullable=False)  # Codice ISO 2 lettere
    
    # Status
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Relazioni
    users = db.relationship('User', backref='company', lazy='dynamic', cascade='all, delete-orphan')
    property_units = db.relationship('PropertyUnit', backref='company', lazy='dynamic', cascade='all, delete-orphan')
    invoices = db.relationship('Invoice', backref='company', lazy='dynamic', cascade='all, delete-orphan')
    scraper_accesses = db.relationship('ScraperAccess', backref='company', lazy='dynamic', cascade='all, delete-orphan')
    
    def __init__(self, **kwargs):
        super(Company, self).__init__(**kwargs)
    
    @property
    def display_name(self):
        """Ritorna il nome da visualizzare (preferendo legal_name se disponibile)."""
        return self.legal_name if self.legal_name else self.name
    
    @property
    def full_address(self):
        """Ritorna l'indirizzo completo formattato."""
        address_parts = []
        if self.address:
            address_parts.append(self.address)
        if self.city:
            city_part = self.city
            if self.province:
                city_part += f" ({self.province})"
            if self.postal_code:
                city_part = f"{self.postal_code} {city_part}"
            address_parts.append(city_part)
        if self.country and self.country != 'IT':
            address_parts.append(self.country)
        
        return ', '.join(address_parts) if address_parts else None
    
    def get_active_users(self):
        """Ritorna gli utenti attivi dell'azienda."""
        return self.users.filter_by(is_active=True).all()
    
    def get_active_property_units(self):
        """Ritorna le unità immobiliari attive dell'azienda."""
        return self.property_units.filter_by(is_active=True).all()
    
    def get_total_invoices_amount(self, year=None):
        """Calcola il totale delle fatture dell'azienda per anno specifico o totale."""
        from .invoice import Invoice
        query = self.invoices
        if year:
            query = query.filter(db.extract('year', Invoice.issue_date) == year)
        
        total = query.with_entities(db.func.sum(Invoice.total_amount)).scalar()
        return total or 0
    
    def get_users_count(self):
        """Ritorna il numero di utenti dell'azienda."""
        return self.users.filter_by(is_active=True).count()
    
    def get_property_units_count(self):
        """Ritorna il numero di unità immobiliari dell'azienda."""
        return self.property_units.filter_by(is_active=True).count()
    
    def get_scraper_accesses_count(self):
        """Ritorna il numero di accessi scraper dell'azienda."""
        return self.scraper_accesses.filter_by(is_active=True).count()
    
    def get_active_scraper_accesses(self):
        """Ritorna gli accessi scraper attivi dell'azienda."""
        return self.scraper_accesses.filter_by(is_active=True).all()
    
    def get_scraper_access_by_platform(self, platform_name):
        """Ritorna l'accesso scraper per una piattaforma specifica."""
        return self.scraper_accesses.filter_by(
            platform_name=platform_name, 
            is_active=True
        ).first()
    
    def has_scraper_platform(self, platform_name):
        """Verifica se l'azienda ha accesso a una piattaforma specifica."""
        return self.get_scraper_access_by_platform(platform_name) is not None
    
    def to_dict(self, include_relationships=False):
        """Converte il modello in dizionario."""
        data = {
            'id': self.id,
            'name': self.name,
            'legal_name': self.legal_name,
            'display_name': self.display_name,
            'vat_number': self.vat_number,
            'tax_code': self.tax_code,
            'email': self.email,
            'phone': self.phone,
            'website': self.website,
            'address': self.address,
            'city': self.city,
            'province': self.province,
            'postal_code': self.postal_code,
            'country': self.country,
            'full_address': self.full_address,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
        
        if include_relationships:
            data.update({
                'users_count': self.get_users_count(),
                'property_units_count': self.get_property_units_count(),
                'scraper_accesses_count': self.get_scraper_accesses_count(),
                'total_invoices_amount': self.get_total_invoices_amount()
            })
            
        return data
    
    def __repr__(self):
        return f'<Company {self.name}>'
