"""
Modello POD per la gestione dei Point of Delivery (POD ENEL/GAS)
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from .base import BaseModel


class PodType(enum.Enum):
    """Enum per i tipi di POD"""
    ELECTRICITY = "ELECTRICITY"  # POD ENEL
    GAS = "GAS"                  # POD GAS
    WATER = "WATER"              # POD Acqua (futuro)
    HEATING = "HEATING"          # POD Riscaldamento (futuro)


class POD(BaseModel):
    """
    Modello per i POD (Point of Delivery)
    
    Rappresenta i punti di consegna delle utenze:
    - POD ENEL (Elettricità)
    - POD GAS
    - Altri tipi di utenze
    """
    
    __tablename__ = 'pods'
    
    # Campi principali
    id = Column(Integer, primary_key=True, autoincrement=True)
    pod_code = Column(String(50), nullable=False, unique=True, index=True)
    pod_type = Column(Enum(PodType), nullable=False, index=True)
    supplier = Column(String(100), nullable=True)  # Fornitore (Enel, Eni, etc.)
    supplier_contract = Column(String(50), nullable=True)  # Numero contratto
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Dati tecnici
    power_capacity = Column(String(20), nullable=True)  # Potenza impegnata (per elettricità)
    voltage = Column(String(20), nullable=True)  # Tensione (per elettricità)
    meter_serial = Column(String(50), nullable=True)  # Numero contatore
    
    # Timestamp
    created_at = Column(DateTime, default=func.now(), nullable=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=True)
    
    # Relazioni
    property_pods = relationship(
        'PropertyPod', 
        back_populates='pod',
        cascade='all, delete-orphan',
        lazy='dynamic'
    )
    
    def __repr__(self):
        return f'<POD {self.pod_code} ({self.pod_type.value})>'
    
    def __str__(self):
        return f"{self.pod_code} - {self.pod_type.value}"
    
    @classmethod
    def get_by_type(cls, pod_type):
        """Restituisce tutti i POD di un tipo specifico"""
        return cls.query.filter_by(pod_type=pod_type, is_active=True).order_by(cls.pod_code).all()
    
    @classmethod
    def get_by_code(cls, pod_code):
        """Trova un POD per codice"""
        return cls.query.filter_by(pod_code=pod_code, is_active=True).first()
    
    @classmethod
    def get_electricity_pods(cls):
        """Restituisce tutti i POD elettrici"""
        return cls.get_by_type(PodType.ELECTRICITY)
    
    @classmethod
    def get_gas_pods(cls):
        """Restituisce tutti i POD gas"""
        return cls.get_by_type(PodType.GAS)
    
    def get_connected_properties(self):
        """Restituisce tutte le proprietà connesse a questo POD"""
        return [pp.property_unit for pp in self.property_pods]
    
    def get_connected_properties_count(self):
        """Restituisce il numero di proprietà connesse"""
        return self.property_pods.count()
    
    def activate(self):
        """Attiva il POD"""
        self.is_active = True
    
    def deactivate(self):
        """Disattiva il POD"""
        self.is_active = False
    
    def is_electricity(self):
        """Controlla se è un POD elettrico"""
        return self.pod_type == PodType.ELECTRICITY
    
    def is_gas(self):
        """Controlla se è un POD gas"""
        return self.pod_type == PodType.GAS
