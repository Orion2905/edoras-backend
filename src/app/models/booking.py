"""
Modello Booking per la gestione delle prenotazioni
"""

from sqlalchemy import Column, Integer, String, Date, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime, date, timedelta

from .base import BaseModel


class Booking(BaseModel):
    """
    Modello per la gestione delle prenotazioni
    
    Rappresenta una prenotazione con:
    - ID interno per il database
    - Riferimento CRM esterno (es. Kross)
    - Date arrivo/partenza
    - Collegamento all'unità immobiliare
    - Gestione ospiti e documenti
    """
    
    __tablename__ = 'bookings'
    
    # Campi principali
    id = Column(Integer, primary_key=True, autoincrement=True)  # ID interno database
    crm_reference_id = Column(String(100), nullable=True, index=True)  # ID riferimento CRM (Kross, etc.)
    booking_name = Column(String(255), nullable=False, index=True)  # Nome/Codice prenotazione
    
    # Date soggiorno
    arrival_date = Column(Date, nullable=False, index=True)  # Data arrivo
    departure_date = Column(Date, nullable=False, index=True)  # Data partenza
    
    # Ospiti
    guest_count = Column(Integer, nullable=False, default=1)  # Numero ospiti
    guest_names = Column(Text, nullable=True)  # Nomi ospiti (opzionale)
    
    # Gestione documenti e comunicazioni
    schedine_sent_count = Column(Integer, nullable=False, default=0)  # Numero schedine inviate
    alloggiati_web_sent_date = Column(DateTime, nullable=True)  # Data invio alloggiati web
    
    # Note e dettagli
    notes = Column(Text, nullable=True)
    booking_status = Column(String(50), nullable=False, default='confirmed', index=True)  # confirmed, cancelled, completed
    
    # Relazioni
    property_unit_id = Column(Integer, ForeignKey('property_units.id'), nullable=False, index=True)
    
    # Stato
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamp
    created_at = Column(DateTime, default=func.now(), nullable=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=True)
    
    # Relazioni
    property_unit = relationship(
        'PropertyUnit', 
        backref='bookings'
    )
    
    def __repr__(self):
        return f'<Booking {self.booking_name} ({self.arrival_date} - {self.departure_date}) - {self.property_unit.name if self.property_unit else "No Unit"}>'
    
    def __str__(self):
        return f"{self.booking_name} - {self.property_unit.name if self.property_unit else 'Unknown Unit'}"
    
    @classmethod
    def get_active_bookings(cls):
        """Restituisce tutte le prenotazioni attive"""
        return cls.query.filter_by(is_active=True, booking_status='confirmed').order_by(cls.arrival_date).all()
    
    @classmethod
    def get_by_date_range(cls, start_date, end_date):
        """Restituisce prenotazioni in un range di date"""
        return cls.query.filter(
            cls.arrival_date <= end_date,
            cls.departure_date >= start_date,
            cls.is_active == True
        ).order_by(cls.arrival_date).all()
    
    @classmethod
    def get_current_bookings(cls):
        """Restituisce prenotazioni correnti (in corso oggi)"""
        today = date.today()
        return cls.query.filter(
            cls.arrival_date <= today,
            cls.departure_date >= today,
            cls.is_active == True,
            cls.booking_status == 'confirmed'
        ).order_by(cls.arrival_date).all()
    
    @classmethod
    def get_by_property_unit(cls, property_unit_id):
        """Restituisce tutte le prenotazioni per un'unità immobiliare"""
        return cls.query.filter_by(property_unit_id=property_unit_id, is_active=True).order_by(cls.arrival_date.desc()).all()
    
    @classmethod
    def get_by_crm_reference(cls, crm_reference_id):
        """Trova prenotazione per riferimento CRM"""
        return cls.query.filter_by(crm_reference_id=crm_reference_id, is_active=True).first()
    
    def get_stay_duration(self):
        """Calcola la durata del soggiorno in giorni"""
        if self.arrival_date and self.departure_date:
            return (self.departure_date - self.arrival_date).days
        return 0
    
    def is_current(self):
        """Controlla se la prenotazione è attualmente in corso"""
        today = date.today()
        return (self.arrival_date <= today <= self.departure_date and 
                self.booking_status == 'confirmed' and 
                self.is_active)
    
    def is_future(self):
        """Controlla se la prenotazione è futura"""
        today = date.today()
        return (self.arrival_date > today and 
                self.booking_status == 'confirmed' and 
                self.is_active)
    
    def is_past(self):
        """Controlla se la prenotazione è passata"""
        today = date.today()
        return self.departure_date < today
    
    def get_enel_pod(self):
        """Restituisce il POD ENEL dall'unità immobiliare collegata"""
        if self.property_unit:
            return self.property_unit.get_electricity_pod()
        return None
    
    def get_gas_pod(self):
        """Restituisce il POD GAS dall'unità immobiliare collegata"""
        if self.property_unit:
            return self.property_unit.get_gas_pod()
        return None
    
    def get_pod_info(self):
        """Restituisce informazioni complete sui POD"""
        enel_pod = self.get_enel_pod()
        gas_pod = self.get_gas_pod()
        
        return {
            'enel_pod': {
                'code': enel_pod.pod_code if enel_pod else None,
                'supplier': enel_pod.supplier if enel_pod else None,
                'contract': enel_pod.supplier_contract if enel_pod else None
            },
            'gas_pod': {
                'code': gas_pod.pod_code if gas_pod else None,
                'supplier': gas_pod.supplier if gas_pod else None,
                'contract': gas_pod.supplier_contract if gas_pod else None
            }
        }
    
    def send_schedina(self):
        """Incrementa il contatore delle schedine inviate"""
        self.schedine_sent_count += 1
    
    def mark_alloggiati_web_sent(self, sent_date=None):
        """Segna come inviato l'alloggiati web"""
        if sent_date is None:
            sent_date = datetime.now()
        self.alloggiati_web_sent_date = sent_date
    
    def is_alloggiati_web_sent(self):
        """Controlla se l'alloggiati web è stato inviato"""
        return self.alloggiati_web_sent_date is not None
    
    def confirm_booking(self):
        """Conferma la prenotazione"""
        self.booking_status = 'confirmed'
    
    def cancel_booking(self):
        """Cancella la prenotazione"""
        self.booking_status = 'cancelled'
    
    def complete_booking(self):
        """Completa la prenotazione"""
        self.booking_status = 'completed'
    
    def activate(self):
        """Attiva la prenotazione"""
        self.is_active = True
    
    def deactivate(self):
        """Disattiva la prenotazione"""
        self.is_active = False
    
    def get_booking_summary(self):
        """Restituisce un riassunto completo della prenotazione"""
        enel_pod = self.get_enel_pod()
        gas_pod = self.get_gas_pod()
        
        return {
            'booking_info': {
                'id': self.id,
                'crm_reference': self.crm_reference_id,
                'name': self.booking_name,
                'status': self.booking_status,
                'arrival_date': self.arrival_date.isoformat() if self.arrival_date else None,
                'departure_date': self.departure_date.isoformat() if self.departure_date else None,
                'duration_days': self.get_stay_duration(),
                'guest_count': self.guest_count,
                'is_current': self.is_current(),
                'is_future': self.is_future()
            },
            'property_info': {
                'unit_id': self.property_unit.id if self.property_unit else None,
                'unit_name': self.property_unit.name if self.property_unit else None,
                'unit_type': self.property_unit.property_type.name if self.property_unit and self.property_unit.property_type else None,
                'square_meters': float(self.property_unit.square_meters) if self.property_unit else None,
                'address': self.property_unit.get_full_address() if self.property_unit else None
            },
            'pod_info': {
                'enel_pod_code': enel_pod.pod_code if enel_pod else None,
                'enel_supplier': enel_pod.supplier if enel_pod else None,
                'gas_pod_code': gas_pod.pod_code if gas_pod else None,
                'gas_supplier': gas_pod.supplier if gas_pod else None
            },
            'documents': {
                'schedine_sent_count': self.schedine_sent_count,
                'alloggiati_web_sent': self.is_alloggiati_web_sent(),
                'alloggiati_web_sent_date': self.alloggiati_web_sent_date.isoformat() if self.alloggiati_web_sent_date else None
            }
        }
    
    def validate_booking(self):
        """Valida i dati della prenotazione"""
        errors = []
        
        if not self.booking_name:
            errors.append("Booking name is required")
        
        if not self.arrival_date:
            errors.append("Arrival date is required")
        
        if not self.departure_date:
            errors.append("Departure date is required")
        
        if self.arrival_date and self.departure_date and self.arrival_date >= self.departure_date:
            errors.append("Departure date must be after arrival date")
        
        if not self.property_unit_id:
            errors.append("Property unit is required")
        
        if self.guest_count < 1:
            errors.append("Guest count must be at least 1")
        
        return errors
