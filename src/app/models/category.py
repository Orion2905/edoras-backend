"""
Category model per gestire le macro categorie delle fatture
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..extensions import db


class Category(db.Model):
    """Modello per le macro categorie delle fatture"""
    
    __tablename__ = 'categories'
    
    # Primary Key
    id = Column(Integer, primary_key=True)
    
    # Category Info
    name = Column(String(100), nullable=False, unique=True, index=True)
    description = Column(String(255), nullable=True)
    code = Column(String(20), nullable=True, unique=True, index=True)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # Relationships
    subcategories = relationship('Subcategory', back_populates='category', cascade='all, delete-orphan')
    invoices = relationship('Invoice', back_populates='category')
    
    def __repr__(self):
        return f'<Category {self.name}>'
    
    def to_dict(self):
        """Converti il modello in dizionario"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'code': self.code,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'subcategories_count': len(self.subcategories) if self.subcategories else 0
        }
    
    @classmethod
    def get_active_categories(cls):
        """Ottieni tutte le categorie attive"""
        return cls.query.filter_by(is_active=True).order_by(cls.name).all()
    
    @classmethod
    def find_by_name(cls, name):
        """Trova categoria per nome"""
        return cls.query.filter_by(name=name).first()
    
    @classmethod
    def find_by_code(cls, code):
        """Trova categoria per codice"""
        return cls.query.filter_by(code=code).first()
