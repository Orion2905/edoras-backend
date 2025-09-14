"""
Modello PropertyPod per la gestione delle relazioni tra unità immobiliari e POD
"""

from sqlalchemy import Column, Integer, ForeignKey, DateTime, Boolean, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import BaseModel


class PropertyPod(BaseModel):
    """
    Modello per la relazione many-to-many tra PropertyUnit e POD
    
    Regole di business:
    - Un POD può essere collegato a più unità immobiliari
    - Un'unità immobiliare può avere UN SOLO POD per tipologia (ENEL, GAS, etc.)
    - Vincolo di unicità su (property_unit_id, pod_type)
    """
    
    __tablename__ = 'property_pods'
    
    # Campi principali
    id = Column(Integer, primary_key=True, autoincrement=True)
    property_unit_id = Column(Integer, ForeignKey('property_units.id'), nullable=False, index=True)
    pod_id = Column(Integer, ForeignKey('pods.id'), nullable=False, index=True)
    
    # Metadati della relazione
    is_primary = Column(Boolean, default=True, nullable=False)  # POD principale per questa tipologia
    is_active = Column(Boolean, default=True, nullable=False)
    notes = Column(Text, nullable=True)
    
    # Timestamp
    created_at = Column(DateTime, default=func.now(), nullable=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=True)
    
    # Relazioni
    property_unit = relationship(
        'PropertyUnit', 
        back_populates='property_pods'
    )
    
    pod = relationship(
        'POD', 
        back_populates='property_pods'
    )
    
    # Vincoli di unicità
    __table_args__ = (
        # Un'unità immobiliare può avere un solo POD attivo per tipologia
        # Questo vincolo verrà gestito a livello applicativo dato che 
        # coinvolge campi di tabelle diverse
    )
    
    def __repr__(self):
        unit_name = self.property_unit.name if self.property_unit else "Unknown Unit"
        pod_code = self.pod.pod_code if self.pod else "Unknown POD"
        pod_type = self.pod.pod_type.value if self.pod and self.pod.pod_type else "Unknown Type"
        return f'<PropertyPod {unit_name} -> {pod_code} ({pod_type})>'
    
    def __str__(self):
        unit_name = self.property_unit.name if self.property_unit else "Unknown Unit"
        pod_code = self.pod.pod_code if self.pod else "Unknown POD"
        return f"{unit_name} -> {pod_code}"
    
    @classmethod
    def get_by_unit(cls, property_unit_id):
        """Restituisce tutte le connessioni POD per un'unità"""
        return cls.query.filter_by(property_unit_id=property_unit_id, is_active=True).all()
    
    @classmethod
    def get_by_pod(cls, pod_id):
        """Restituisce tutte le connessioni per un POD"""
        return cls.query.filter_by(pod_id=pod_id, is_active=True).all()
    
    @classmethod
    def get_by_unit_and_pod_type(cls, property_unit_id, pod_type):
        """Trova la connessione tra un'unità e un tipo di POD"""
        return cls.query.join(cls.pod).filter(
            cls.property_unit_id == property_unit_id,
            cls.is_active == True,
            # Filtro per pod_type viene fatto tramite join
        ).filter_by(pod_type=pod_type).first()
    
    @classmethod
    def create_connection(cls, property_unit_id, pod_id, is_primary=True, notes=None):
        """
        Crea una nuova connessione tra unità e POD
        
        Verifica che l'unità non abbia già un POD dello stesso tipo
        """
        from .pod import POD
        from .property_unit import PropertyUnit
        
        # Verifica che l'unità e il POD esistano
        unit = PropertyUnit.query.get(property_unit_id)
        pod = POD.query.get(pod_id)
        
        if not unit:
            raise ValueError(f"PropertyUnit with id {property_unit_id} not found")
        if not pod:
            raise ValueError(f"POD with id {pod_id} not found")
        
        # Verifica che l'unità non abbia già un POD di questo tipo
        existing = cls.get_by_unit_and_pod_type(property_unit_id, pod.pod_type)
        if existing:
            raise ValueError(
                f"PropertyUnit {unit.name} already has a {pod.pod_type.value} POD: {existing.pod.pod_code}"
            )
        
        # Crea la connessione
        connection = cls(
            property_unit_id=property_unit_id,
            pod_id=pod_id,
            is_primary=is_primary,
            notes=notes
        )
        
        return connection
    
    def activate(self):
        """Attiva la connessione"""
        self.is_active = True
    
    def deactivate(self):
        """Disattiva la connessione"""
        self.is_active = False
    
    def set_primary(self):
        """Imposta come connessione principale"""
        self.is_primary = True
    
    def unset_primary(self):
        """Rimuove come connessione principale"""
        self.is_primary = False
    
    def get_pod_type(self):
        """Restituisce il tipo di POD di questa connessione"""
        return self.pod.pod_type if self.pod else None
    
    def get_connection_info(self):
        """Restituisce informazioni complete sulla connessione"""
        if not self.property_unit or not self.pod:
            return {}
        
        return {
            'property_unit': {
                'id': self.property_unit.id,
                'name': self.property_unit.name,
                'square_meters': float(self.property_unit.square_meters),
                'type': self.property_unit.property_type.name if self.property_unit.property_type else None
            },
            'pod': {
                'id': self.pod.id,
                'code': self.pod.pod_code,
                'type': self.pod.pod_type.value,
                'supplier': self.pod.supplier
            },
            'connection': {
                'is_primary': self.is_primary,
                'is_active': self.is_active,
                'created_at': self.created_at.isoformat() if self.created_at else None,
                'notes': self.notes
            }
        }
