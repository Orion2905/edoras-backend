# ScraperAccess Model

import json
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..extensions import db
from .base import BaseModel


class ScraperAccess(BaseModel):
    """Modello per gestire gli accessi alle piattaforme di scraping per ogni azienda."""
    
    __tablename__ = 'scraper_access'
    
    # Campi base
    platform_name = Column(String(100), nullable=False, index=True)  # Nome piattaforma (Enel, Eni, A2A, etc.)
    platform_type = Column(String(50), nullable=False, index=True)   # Tipo (energia, gas, telecom, etc.)
    platform_url = Column(String(255), nullable=True)               # URL base della piattaforma
    
    # Credenziali (JSON flessibile per diverse piattaforme)
    access_data = Column(JSON, nullable=False)  # {"username": "...", "password": "...", "customer_code": "...", etc.}
    
    # Stato e configurazione
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)     # Se le credenziali sono state verificate
    last_verified = Column(DateTime, nullable=True)                 # Ultima verifica credenziali
    last_scrape = Column(DateTime, nullable=True)                   # Ultimo scraping effettuato
    
    # Configurazione scraping
    scrape_frequency = Column(String(20), default='daily', nullable=False)  # daily, weekly, monthly
    auto_scrape = Column(Boolean, default=True, nullable=False)     # Scraping automatico abilitato
    
    # Note e configurazioni aggiuntive
    notes = Column(Text, nullable=True)
    config_json = Column(JSON, nullable=True)  # Configurazioni aggiuntive specifiche per piattaforma
    
    # Relazione con azienda
    company_id = Column(Integer, ForeignKey('companies.id'), nullable=False, index=True)
    
    # Indici per performance
    __table_args__ = (
        db.UniqueConstraint('company_id', 'platform_name', name='uq_company_platform'),
        db.Index('idx_scraper_platform_type_active', 'platform_type', 'is_active'),
        db.Index('idx_scraper_company_active', 'company_id', 'is_active'),
    )
    
    def __init__(self, **kwargs):
        super(ScraperAccess, self).__init__(**kwargs)
    
    @classmethod
    def get_by_company(cls, company_id, active_only=True):
        """Ritorna tutti gli accessi scraper per un'azienda."""
        query = cls.query.filter_by(company_id=company_id)
        if active_only:
            query = query.filter_by(is_active=True)
        return query.order_by(cls.platform_name).all()
    
    @classmethod
    def get_by_platform_type(cls, platform_type, active_only=True):
        """Ritorna tutti gli accessi per tipo di piattaforma."""
        query = cls.query.filter_by(platform_type=platform_type)
        if active_only:
            query = query.filter_by(is_active=True)
        return query.order_by(cls.company_id, cls.platform_name).all()
    
    @classmethod
    def get_company_platform(cls, company_id, platform_name):
        """Ritorna l'accesso specifico per azienda e piattaforma."""
        return cls.query.filter_by(
            company_id=company_id, 
            platform_name=platform_name,
            is_active=True
        ).first()
    
    @classmethod
    def get_auto_scrape_enabled(cls):
        """Ritorna tutti gli accessi con scraping automatico abilitato."""
        return cls.query.filter_by(
            is_active=True, 
            auto_scrape=True, 
            is_verified=True
        ).all()
    
    def set_access_data(self, data_dict):
        """Imposta i dati di accesso da dizionario Python."""
        if not isinstance(data_dict, dict):
            raise ValueError("I dati di accesso devono essere un dizionario")
        self.access_data = data_dict
    
    def get_access_data(self):
        """Ritorna i dati di accesso come dizionario Python."""
        return self.access_data if self.access_data else {}
    
    def get_credential(self, key):
        """Ritorna una credenziale specifica dai dati di accesso."""
        data = self.get_access_data()
        return data.get(key)
    
    def set_credential(self, key, value):
        """Imposta una credenziale specifica nei dati di accesso."""
        data = self.get_access_data()
        data[key] = value
        self.set_access_data(data)
    
    def has_credential(self, key):
        """Verifica se una credenziale specifica esiste."""
        data = self.get_access_data()
        return key in data and data[key] is not None
    
    def get_required_credentials(self):
        """Ritorna le credenziali richieste per il tipo di piattaforma."""
        credentials_map = {
            'energia': ['username', 'password'],
            'gas': ['username', 'password'],
            'telecom': ['username', 'password', 'customer_code'],
            'acqua': ['username', 'password', 'contract_number'],
            'banca': ['username', 'password', 'customer_id'],
            'assicurazione': ['username', 'password', 'policy_number']
        }
        return credentials_map.get(self.platform_type, ['username', 'password'])
    
    def validate_credentials(self):
        """Valida che tutte le credenziali richieste siano presenti."""
        required = self.get_required_credentials()
        data = self.get_access_data()
        missing = []
        
        for field in required:
            if not data.get(field):
                missing.append(field)
        
        return len(missing) == 0, missing
    
    def mark_verified(self, success=True):
        """Marca le credenziali come verificate."""
        self.is_verified = success
        self.last_verified = datetime.utcnow()
        db.session.commit()
    
    def mark_scraped(self):
        """Marca l'ultimo scraping effettuato."""
        self.last_scrape = datetime.utcnow()
        db.session.commit()
    
    def is_scrape_due(self):
        """Verifica se è il momento di effettuare lo scraping."""
        if not self.auto_scrape or not self.is_verified or not self.is_active:
            return False
        
        if not self.last_scrape:
            return True
        
        from datetime import timedelta
        now = datetime.utcnow()
        
        frequency_map = {
            'daily': timedelta(days=1),
            'weekly': timedelta(weeks=1),
            'monthly': timedelta(days=30),
            'hourly': timedelta(hours=1)  # Per test/debug
        }
        
        interval = frequency_map.get(self.scrape_frequency, timedelta(days=1))
        return now >= (self.last_scrape + interval)
    
    def get_config(self, key, default=None):
        """Ritorna una configurazione specifica dal config_json."""
        config = self.config_json if self.config_json else {}
        return config.get(key, default)
    
    def set_config(self, key, value):
        """Imposta una configurazione specifica nel config_json."""
        config = self.config_json if self.config_json else {}
        config[key] = value
        self.config_json = config
    
    def get_masked_credentials(self):
        """Ritorna le credenziali con i valori sensibili mascherati per log/debug."""
        data = self.get_access_data()
        masked = {}
        
        sensitive_fields = ['password', 'token', 'secret', 'key']
        
        for key, value in data.items():
            if any(sensitive in key.lower() for sensitive in sensitive_fields):
                if value:
                    masked[key] = f"{'*' * (len(str(value)) - 2)}{str(value)[-2:]}"
                else:
                    masked[key] = None
            else:
                masked[key] = value
        
        return masked
    
    @property
    def company_name(self):
        """Ritorna il nome dell'azienda."""
        return self.company.display_name if self.company else "Nessuna Azienda"
    
    @property
    def status_summary(self):
        """Ritorna un riassunto dello stato dell'accesso."""
        status = []
        
        if not self.is_active:
            status.append("Disattivato")
        elif self.is_verified:
            status.append("Verificato")
        else:
            status.append("Non verificato")
        
        if self.auto_scrape:
            status.append(f"Auto-scrape {self.scrape_frequency}")
        
        if self.is_scrape_due():
            status.append("Scraping dovuto")
        
        return " | ".join(status)
    
    def to_dict(self, include_credentials=False):
        """Converte il modello in dizionario."""
        data = {
            'id': self.id,
            'platform_name': self.platform_name,
            'platform_type': self.platform_type,
            'platform_url': self.platform_url,
            'is_active': self.is_active,
            'is_verified': self.is_verified,
            'last_verified': self.last_verified.isoformat() if self.last_verified else None,
            'last_scrape': self.last_scrape.isoformat() if self.last_scrape else None,
            'scrape_frequency': self.scrape_frequency,
            'auto_scrape': self.auto_scrape,
            'notes': self.notes,
            'company_id': self.company_id,
            'company_name': self.company_name,
            'status_summary': self.status_summary,
            'is_scrape_due': self.is_scrape_due(),
            'required_credentials': self.get_required_credentials(),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
        
        if include_credentials:
            data['access_data'] = self.get_access_data()
            data['config_json'] = self.config_json
        else:
            # Includi solo credenziali mascherate per sicurezza
            data['access_data_masked'] = self.get_masked_credentials()
        
        return data
    
    def __repr__(self):
        return f'<ScraperAccess {self.platform_name} for {self.company_name} ({self.platform_type})>'


# Funzioni di utilità per gestione piattaforme
def get_supported_platforms():
    """Ritorna le piattaforme supportate con i loro tipi."""
    return {
        'energia': [
            'Enel Energia', 'ENI Plenitude', 'A2A Energia', 'Edison', 'Hera Energia',
            'Acea Energia', 'Iren Mercato', 'Sorgenia', 'Green Network Energy'
        ],
        'gas': [
            'ENI Gas', 'Italgas', 'A2A Gas', 'Hera Gas', 'Iren Gas',
            'Edison Gas', 'Snam Rete Gas'
        ],
        'telecom': [
            'TIM', 'Vodafone', 'WindTre', 'Iliad', 'Fastweb',
            'Tiscali', 'Linkem'
        ],
        'acqua': [
            'Acea ATO 2', 'CAP Holding', 'Hera Acqua', 'Iren Acqua',
            'A2A Ciclo Idrico', 'Acque SpA'
        ],
        'banca': [
            'Intesa Sanpaolo', 'UniCredit', 'Banco BPM', 'BPER Banca',
            'Monte dei Paschi', 'Crédit Agricole', 'BNL', 'UBI Banca'
        ],
        'assicurazione': [
            'Generali', 'Allianz', 'AXA', 'Zurich', 'Cattolica',
            'UnipolSai', 'Reale Mutua'
        ]
    }


def create_default_access_template(platform_type, platform_name):
    """Crea un template di default per i dati di accesso."""
    templates = {
        'energia': {
            'username': '',
            'password': '',
            'customer_code': '',  # Codice cliente
            'pod_codes': []       # Lista POD associati
        },
        'gas': {
            'username': '',
            'password': '',
            'customer_code': '',
            'pdr_codes': []       # Lista PDR associati
        },
        'telecom': {
            'username': '',
            'password': '',
            'customer_code': '',
            'phone_numbers': []   # Numeri di telefono associati
        },
        'acqua': {
            'username': '',
            'password': '',
            'contract_number': '',
            'meter_codes': []     # Codici contatori
        },
        'banca': {
            'username': '',
            'password': '',
            'customer_id': '',
            'account_numbers': [] # Numeri conto
        },
        'assicurazione': {
            'username': '',
            'password': '',
            'policy_number': '',
            'policy_codes': []    # Codici polizze
        }
    }
    
    return templates.get(platform_type, {
        'username': '',
        'password': ''
    })
