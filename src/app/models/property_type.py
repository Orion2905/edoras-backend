"""
Modello PropertyType per la gestione dei tipi di unità immobiliari
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import BaseModel


class PropertyType(BaseModel):
    """
    Modello per i tipi di unità immobiliari
    
    Rappresenta i diversi tipi di proprietà immobiliari come:
    - Villa
    - Appartamento
    - Ufficio
    - Magazzino
    - etc.
    """
    
    __tablename__ = 'property_types'
    
    # Campi principali
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    code = Column(String(20), nullable=True, unique=True, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamp
    created_at = Column(DateTime, default=func.now(), nullable=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=True)
    
    # Relazioni
    property_units = relationship(
        'PropertyUnit', 
        back_populates='property_type',
        cascade='all, delete-orphan',
        lazy='dynamic'
    )
    
    def __repr__(self):
        return f'<PropertyType {self.name} ({self.code})>'
    
    def __str__(self):
        return self.name
    
    @classmethod
    def get_active(cls):
        """Restituisce tutti i tipi di proprietà attivi"""
        return cls.query.filter_by(is_active=True).order_by(cls.name).all()
    
    @classmethod
    def get_by_code(cls, code):
        """Trova un tipo di proprietà per codice"""
        return cls.query.filter_by(code=code, is_active=True).first()
    
    def get_units_count(self):
        """Restituisce il numero di unità immobiliari di questo tipo"""
        return self.property_units.count()
    
    def activate(self):
        """Attiva il tipo di proprietà"""
        self.is_active = True
    
    def deactivate(self):
        """Disattiva il tipo di proprietà"""
        self.is_active = False
