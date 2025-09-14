"""
Modello PropertyUnit per la gestione delle unità immobiliari
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Numeric, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from decimal import Decimal

from .base import BaseModel


class PropertyUnit(BaseModel):
    """
    Modello per le unità immobiliari
    
    Rappresenta una singola unità immobiliare con:
    - Tipologia (collegata a PropertyType)
    - Metratura
    - Connessioni POD (tramite PropertyPod)
    """
    
    __tablename__ = 'property_units'
    
    # Campi principali
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, index=True)  # Villa Rossi, Appartamento 1A, etc.
    description = Column(Text, nullable=True)
    
    # Dati tecnici
    square_meters = Column(Numeric(8, 2), nullable=False)  # MQ
    rooms = Column(Integer, nullable=True)  # Numero locali
    bathrooms = Column(Integer, nullable=True)  # Numero bagni
    floor = Column(String(10), nullable=True)  # Piano
    
    # Dati di ubicazione
    address = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    postal_code = Column(String(10), nullable=True)
    province = Column(String(5), nullable=True)
    
    # Relazioni
    property_type_id = Column(Integer, ForeignKey('property_types.id'), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey('companies.id'), nullable=True, index=True)  # Collegamento azienda
    
    # Stato
    is_active = Column(Boolean, default=True, nullable=False)
    is_occupied = Column(Boolean, default=False, nullable=False)
    
    # Timestamp
    created_at = Column(DateTime, default=func.now(), nullable=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=True)
    
    # Relazioni
    property_type = relationship(
        'PropertyType', 
        back_populates='property_units'
    )
    
    property_pods = relationship(
        'PropertyPod', 
        back_populates='property_unit',
        cascade='all, delete-orphan',
        lazy='dynamic'
    )
    
    def __repr__(self):
        return f'<PropertyUnit {self.name} ({self.property_type.name if self.property_type else "No Type"}) - {self.square_meters}mq>'
    
    def __str__(self):
        return f"{self.name} - {self.square_meters}mq"
    
    @classmethod
    def get_by_company(cls, company_id, active_only=True):
        """Restituisce tutte le unità di un'azienda specifica"""
        query = cls.query.filter_by(company_id=company_id)
        if active_only:
            query = query.filter_by(is_active=True)
        return query.order_by(cls.name).all()
    
    @classmethod
    def get_by_type(cls, property_type_id):
        """Restituisce tutte le unità di un tipo specifico"""
        return cls.query.filter_by(property_type_id=property_type_id, is_active=True).order_by(cls.name).all()
    
    @classmethod
    def get_active(cls):
        """Restituisce tutte le unità attive"""
        return cls.query.filter_by(is_active=True).order_by(cls.name).all()
    
    @classmethod
    def get_by_city(cls, city):
        """Restituisce tutte le unità di una città"""
        return cls.query.filter_by(city=city, is_active=True).order_by(cls.name).all()
    
    def get_connected_pods(self):
        """Restituisce tutti i POD connessi a questa unità"""
        return [pp.pod for pp in self.property_pods]
    
    def get_pod_by_type(self, pod_type):
        """Restituisce il POD di un tipo specifico connesso a questa unità"""
        from .pod import PodType
        for pp in self.property_pods:
            if pp.pod and pp.pod.pod_type == pod_type:
                return pp.pod
        return None
    
    def get_electricity_pod(self):
        """Restituisce il POD elettrico"""
        from .pod import PodType
        return self.get_pod_by_type(PodType.ELECTRICITY)
    
    def get_gas_pod(self):
        """Restituisce il POD gas"""
        from .pod import PodType
        return self.get_pod_by_type(PodType.GAS)
    
    def has_pod_type(self, pod_type):
        """Controlla se l'unità ha già un POD di questo tipo"""
        return self.get_pod_by_type(pod_type) is not None
    
    def get_full_address(self):
        """Restituisce l'indirizzo completo"""
        parts = []
        if self.address:
            parts.append(self.address)
        if self.city and self.postal_code:
            parts.append(f"{self.postal_code} {self.city}")
        elif self.city:
            parts.append(self.city)
        if self.province:
            parts.append(f"({self.province})")
        
        return ", ".join(parts) if parts else "Indirizzo non specificato"
    
    def calculate_cost_per_sqm(self, total_cost):
        """Calcola il costo per metro quadro"""
        if self.square_meters and total_cost:
            return Decimal(str(total_cost)) / self.square_meters
        return Decimal('0.00')
    
    def activate(self):
        """Attiva l'unità"""
        self.is_active = True
    
    def deactivate(self):
        """Disattiva l'unità"""
        self.is_active = False
    
    def occupy(self):
        """Segna l'unità come occupata"""
        self.is_occupied = True
    
    def vacate(self):
        """Segna l'unità come libera"""
        self.is_occupied = False
    
    @property
    def company_name(self):
        """Ritorna il nome dell'azienda proprietaria"""
        return self.company.display_name if self.company else "Nessuna Azienda"
    
    def belongs_to_company(self, company_id):
        """Verifica se l'unità appartiene a una specifica azienda"""
        return self.company_id == company_id
    
    def set_company(self, company_id):
        """Assegna l'unità a un'azienda"""
        self.company_id = company_id
