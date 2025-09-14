"""
Modello Invoice per la gestione delle fatture
"""

from decimal import Decimal
from sqlalchemy import Column, Integer, String, Date, Numeric, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from .base import BaseModel
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Numeric, Date, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from decimal import Decimal
from ..extensions import db


class Invoice(db.Model):
    """Modello per le fatture"""
    
    __tablename__ = 'invoices'
    
    # Primary Key
    id = Column(Integer, primary_key=True)
    
    # File Info
    file_name = Column(String(255), nullable=True)
    file_path = Column(String(500), nullable=True)
    
    # Supplier Info
    supplier = Column(String(255), nullable=False, index=True)
    supplier_vat = Column(String(20), nullable=True, index=True)  # fornitore_piva
    
    # Invoice Info
    invoice_number = Column(String(50), nullable=False, index=True)  # num_fattura
    invoice_date = Column(Date, nullable=False, index=True)  # data
    document_type = Column(String(50), nullable=True)  # tipo_documento
    
    # Article/Product Info
    article_description = Column(Text, nullable=True)  # descrizione_articolo
    article_code = Column(String(100), nullable=True, index=True)  # codice_articolo
    unit_of_measure = Column(String(20), nullable=True)  # unita_misura
    
    # Period Info
    period_start_date = Column(Date, nullable=True)  # data_inizio_periodo
    period_end_date = Column(Date, nullable=True)  # data_fine_periodo
    
    # Quantity and Pricing
    quantity = Column(Numeric(12, 4), nullable=True, default=Decimal('1.0000'))
    unit_price_with_vat = Column(Numeric(12, 4), nullable=True)  # prezzo_unitario_iva_comp
    total_price_with_vat = Column(Numeric(12, 4), nullable=True)  # prezzo_totale_riga_iva_comp
    unit_price_without_vat = Column(Numeric(12, 4), nullable=True)  # prezzo_unitario_no_iva
    total_price_without_vat = Column(Numeric(12, 4), nullable=True)  # prezzo_totale_riga_no_iva
    
    # VAT Info
    vat_percentage = Column(Numeric(5, 2), nullable=True)  # iva_perc
    vat_nature = Column(String(50), nullable=True)  # natura_iva
    
    # Management Data
    management_data_type = Column(String(100), nullable=True)  # tipo_dato_gestionale
    management_text_ref = Column(String(255), nullable=True)  # rif_testo_gestionale
    payment_method = Column(String(100), nullable=True)  # modalita_pagamento
    
    # Categories (Foreign Keys)
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=True)
    subcategory_id = Column(Integer, ForeignKey('subcategories.id'), nullable=True)
    minicategory_id = Column(Integer, ForeignKey('minicategories.id'), nullable=True)
    
    # Company relation
    company_id = Column(Integer, ForeignKey('companies.id'), nullable=True, index=True)
    
    # Additional Fields
    notes = Column(Text, nullable=True)  # NOTE
    allocation = Column(String(255), nullable=True)  # RIPARTIZIONE
    depreciation = Column(String(255), nullable=True)  # AMMORTAMENTO
    
    # Document Type and Status Management
    document_status = Column(String(20), nullable=False, default='invoice')  # 'invoice', 'receipt', 'delivery_note', 'estimate'
    is_final = Column(Boolean, nullable=False, default=True)  # False per documenti temporanei/scontrini
    temp_reference = Column(String(100), nullable=True, index=True)  # Riferimento temporaneo per matching
    awaiting_invoice = Column(Boolean, nullable=False, default=False)  # True se aspettiamo fattura definitiva
    linked_invoice_id = Column(Integer, ForeignKey('invoices.id'), nullable=True, index=True)  # Link alla fattura definitiva
    
    # Status and Processing
    is_processed = Column(Boolean, default=False, nullable=False)
    is_validated = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # Relationships
    category = relationship('Category', back_populates='invoices')
    subcategory = relationship('Subcategory', back_populates='invoices')
    minicategory = relationship('Minicategory', back_populates='invoices')
    
    # Self-referencing relationship per linked invoices
    linked_invoice = relationship('Invoice', remote_side=[id], backref='temporary_documents')
    
    def __repr__(self):
        return f'<Invoice {self.invoice_number} - {self.supplier} ({self.invoice_date})>'
    
    def to_dict(self):
        """Converti il modello in dizionario"""
        return {
            'id': self.id,
            'file_name': self.file_name,
            'file_path': self.file_path,
            'supplier': self.supplier,
            'supplier_vat': self.supplier_vat,
            'invoice_number': self.invoice_number,
            'invoice_date': self.invoice_date.isoformat() if self.invoice_date else None,
            'document_type': self.document_type,
            'article_description': self.article_description,
            'article_code': self.article_code,
            'unit_of_measure': self.unit_of_measure,
            'period_start_date': self.period_start_date.isoformat() if self.period_start_date else None,
            'period_end_date': self.period_end_date.isoformat() if self.period_end_date else None,
            'quantity': float(self.quantity) if self.quantity else None,
            'unit_price_with_vat': float(self.unit_price_with_vat) if self.unit_price_with_vat else None,
            'total_price_with_vat': float(self.total_price_with_vat) if self.total_price_with_vat else None,
            'unit_price_without_vat': float(self.unit_price_without_vat) if self.unit_price_without_vat else None,
            'total_price_without_vat': float(self.total_price_without_vat) if self.total_price_without_vat else None,
            'vat_percentage': float(self.vat_percentage) if self.vat_percentage else None,
            'vat_nature': self.vat_nature,
            'management_data_type': self.management_data_type,
            'management_text_ref': self.management_text_ref,
            'payment_method': self.payment_method,
            'category_id': self.category_id,
            'subcategory_id': self.subcategory_id,
            'minicategory_id': self.minicategory_id,
            'company_id': self.company_id,
            'notes': self.notes,
            'allocation': self.allocation,
            'depreciation': self.depreciation,
            
            # Document Status Fields
            'document_status': self.document_status,
            'is_final': self.is_final,
            'temp_reference': self.temp_reference,
            'awaiting_invoice': self.awaiting_invoice,
            'linked_invoice_id': self.linked_invoice_id,
            
            # Status and timestamps
            'is_processed': self.is_processed,
            'is_validated': self.is_validated,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            
            # Relationships
            'category': self.category.to_dict() if self.category else None,
            'subcategory': self.subcategory.to_dict() if self.subcategory else None,
            'minicategory': self.minicategory.to_dict() if self.minicategory else None
        }
    
    @classmethod
    def get_by_company(cls, company_id):
        """Ottieni fatture per azienda"""
        return cls.query.filter_by(company_id=company_id).order_by(cls.invoice_date.desc()).all()
    
    @classmethod
    def get_by_supplier(cls, supplier):
        """Ottieni fatture per fornitore"""
        return cls.query.filter_by(supplier=supplier).order_by(cls.invoice_date.desc()).all()
    
    @classmethod
    def get_by_date_range(cls, start_date, end_date):
        """Ottieni fatture per range di date"""
        return cls.query.filter(
            cls.invoice_date >= start_date,
            cls.invoice_date <= end_date
        ).order_by(cls.invoice_date.desc()).all()
    
    @classmethod
    def get_by_category(cls, category_id):
        """Ottieni fatture per categoria"""
        return cls.query.filter_by(category_id=category_id).order_by(cls.invoice_date.desc()).all()
    
    @classmethod
    def get_unprocessed(cls):
        """Ottieni fatture non processate"""
        return cls.query.filter_by(is_processed=False).order_by(cls.created_at.desc()).all()
    
    @classmethod
    def get_unvalidated(cls):
        """Ottieni fatture non validate"""
        return cls.query.filter_by(is_validated=False).order_by(cls.created_at.desc()).all()
    
    def calculate_totals(self):
        """Calcola automaticamente i totali se mancanti"""
        if self.quantity and self.unit_price_without_vat and not self.total_price_without_vat:
            self.total_price_without_vat = self.quantity * self.unit_price_without_vat
        
        if self.quantity and self.unit_price_with_vat and not self.total_price_with_vat:
            self.total_price_with_vat = self.quantity * self.unit_price_with_vat
    
    def validate_invoice(self):
        """Valida i dati della fattura"""
        errors = []
        
        if not self.supplier:
            errors.append("Supplier is required")
        
        if not self.invoice_number:
            errors.append("Invoice number is required")
        
        if not self.invoice_date:
            errors.append("Invoice date is required")
        
        if self.total_price_without_vat and self.vat_percentage and not self.total_price_with_vat:
            # Calcola automaticamente il prezzo con IVA
            vat_amount = self.total_price_without_vat * (self.vat_percentage / 100)
            self.total_price_with_vat = self.total_price_without_vat + vat_amount
        
        return errors
    
    def calculate_vat(self):
        """Calcola l'importo IVA"""
        if self.total_price_without_vat and self.vat_percentage:
            return self.total_price_without_vat * (self.vat_percentage / 100)
        return Decimal('0.00')
    
    def calculate_price_without_vat(self):
        """Calcola il prezzo unitario senza IVA dal prezzo con IVA"""
        if self.unit_price_with_vat and self.vat_percentage:
            return self.unit_price_with_vat / (1 + (self.vat_percentage / 100))
        return self.unit_price_without_vat or Decimal('0.00')
    
    def is_overdue(self, days=30):
        """Controlla se la fattura è in ritardo per il pagamento"""
        if not self.invoice_date:
            return False
        
        from datetime import date, timedelta
        due_date = self.invoice_date + timedelta(days=days)
        return date.today() > due_date
    
    def get_full_category_path(self):
        """Restituisce il percorso completo della categoria"""
        path_parts = []
        
        if self.category:
            path_parts.append(self.category.name)
        
        if self.subcategory:
            path_parts.append(self.subcategory.name)
        
        if self.minicategory:
            path_parts.append(self.minicategory.name)
        
        return " > ".join(path_parts) if path_parts else "Non categorizzato"
    
    @property
    def company_name(self):
        """Ritorna il nome dell'azienda"""
        return self.company.display_name if self.company else "Nessuna Azienda"
    
    def belongs_to_company(self, company_id):
        """Verifica se la fattura appartiene a una specifica azienda"""
        return self.company_id == company_id
    
    def set_company(self, company_id):
        """Assegna la fattura a un'azienda"""
        self.company_id = company_id
    
    @classmethod
    def get_company_total(cls, company_id, year=None):
        """Calcola il totale delle fatture per un'azienda (opzionalmente per anno)"""
        query = cls.query.filter_by(company_id=company_id)
        if year:
            query = query.filter(db.func.extract('year', cls.invoice_date) == year)
        
        total = query.with_entities(db.func.sum(cls.total_price_with_vat)).scalar()
        return total or Decimal('0.00')
    
    # ===== METODI PER GESTIONE DOCUMENTI TEMPORANEI =====
    
    @property
    def is_receipt(self):
        """Verifica se è uno scontrino/ricevuta"""
        return self.document_status == 'receipt'
    
    @property
    def is_delivery_note(self):
        """Verifica se è una bolla di consegna"""
        return self.document_status == 'delivery_note'
    
    @property
    def is_temporary(self):
        """Verifica se è un documento temporaneo"""
        return not self.is_final
    
    @property
    def has_linked_invoice(self):
        """Verifica se ha una fattura collegata"""
        return self.linked_invoice_id is not None
    
    def mark_as_receipt(self, temp_reference=None):
        """Marca il documento come scontrino temporaneo"""
        self.document_status = 'receipt'
        self.is_final = False
        self.awaiting_invoice = True
        if temp_reference:
            self.temp_reference = temp_reference
        db.session.commit()
    
    def mark_as_delivery_note(self, temp_reference=None):
        """Marca il documento come bolla di consegna temporanea"""
        self.document_status = 'delivery_note'
        self.is_final = False
        self.awaiting_invoice = True
        if temp_reference:
            self.temp_reference = temp_reference
        db.session.commit()
    
    def convert_to_final_invoice(self):
        """Converte un documento temporaneo in fattura definitiva"""
        self.document_status = 'invoice'
        self.is_final = True
        self.awaiting_invoice = False
        self.temp_reference = None
        db.session.commit()
    
    def link_to_invoice(self, invoice_id):
        """Collega questo documento a una fattura definitiva"""
        self.linked_invoice_id = invoice_id
        self.awaiting_invoice = False
        db.session.commit()
    
    @classmethod
    def find_potential_duplicates(cls, supplier_vat, total_amount, invoice_date, tolerance_days=7, tolerance_amount=0.01):
        """
        Trova potenziali fatture duplicate basandosi su:
        - Stessa partita IVA fornitore
        - Importo simile (con tolleranza)
        - Date vicine (con tolleranza giorni)
        """
        from datetime import timedelta
        
        # Calcola range di date
        start_date = invoice_date - timedelta(days=tolerance_days)
        end_date = invoice_date + timedelta(days=tolerance_days)
        
        # Calcola range di importi
        min_amount = total_amount - Decimal(str(tolerance_amount))
        max_amount = total_amount + Decimal(str(tolerance_amount))
        
        return cls.query.filter(
            cls.supplier_vat == supplier_vat,
            cls.invoice_date.between(start_date, end_date),
            cls.total_price_with_vat.between(min_amount, max_amount)
        ).all()
    
    @classmethod
    def find_awaiting_invoices_for_supplier(cls, supplier_vat):
        """Trova documenti temporanei in attesa di fattura per un fornitore"""
        return cls.query.filter(
            cls.supplier_vat == supplier_vat,
            cls.awaiting_invoice == True,
            cls.is_final == False
        ).all()
    
    def check_for_matching_temporary_docs(self):
        """
        Controlla se esistono documenti temporanei che potrebbero corrispondere a questa fattura
        """
        if not self.is_final or self.document_status != 'invoice':
            return []
        
        return self.find_awaiting_invoices_for_supplier(self.supplier_vat)
    
    @classmethod
    def get_temporary_documents(cls, company_id=None):
        """Ottieni tutti i documenti temporanei"""
        query = cls.query.filter(cls.is_final == False)
        if company_id:
            query = query.filter(cls.company_id == company_id)
        return query.all()
    
    @classmethod
    def get_awaiting_invoices(cls, company_id=None):
        """Ottieni documenti in attesa di fattura definitiva"""
        query = cls.query.filter(
            cls.is_final == False,
            cls.awaiting_invoice == True
        )
        if company_id:
            query = query.filter(cls.company_id == company_id)
        return query.all()
    
    def create_duplicate_alert(self, potential_duplicates):
        """
        Crea un alert per potenziali duplicati
        Questo metodo può essere esteso per integrare con un sistema di notifiche
        """
        alert_data = {
            'type': 'potential_duplicate',
            'invoice_id': self.id,
            'invoice_number': self.invoice_number,
            'supplier': self.supplier,
            'amount': float(self.total_price_with_vat) if self.total_price_with_vat else 0,
            'date': self.invoice_date.isoformat() if self.invoice_date else None,
            'duplicates': [
                {
                    'id': dup.id,
                    'number': dup.invoice_number,
                    'status': dup.document_status,
                    'is_final': dup.is_final,
                    'amount': float(dup.total_price_with_vat) if dup.total_price_with_vat else 0,
                    'date': dup.invoice_date.isoformat() if dup.invoice_date else None
                } for dup in potential_duplicates
            ]
        }
        
        # TODO: Implementare sistema di notifiche/alert
        print(f"🚨 ALERT: Potenziali duplicati trovati per fattura {self.invoice_number}")
        print(f"📄 Documenti simili: {len(potential_duplicates)}")
        
        return alert_data
        return total or Decimal('0.00')
    
    @classmethod 
    def get_company_invoices_by_year(cls, company_id, year):
        """Ottieni fatture di un'azienda per anno specifico"""
        return cls.query.filter(
            cls.company_id == company_id,
            db.func.extract('year', cls.invoice_date) == year
        ).order_by(cls.invoice_date.desc()).all()
