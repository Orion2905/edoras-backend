"""
Minicategory model per gestire le mini categorie delle fatture
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..extensions import db


class Minicategory(db.Model):
    """Modello per le mini categorie delle fatture"""
    
    __tablename__ = 'minicategories'
    
    # Primary Key
    id = Column(Integer, primary_key=True)
    
    # Foreign Key
    subcategory_id = Column(Integer, ForeignKey('subcategories.id'), nullable=False)
    
    # Minicategory Info
    name = Column(String(100), nullable=False, index=True)
    description = Column(String(255), nullable=True)
    code = Column(String(20), nullable=True, index=True)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # Relationships
    subcategory = relationship('Subcategory', back_populates='minicategories')
    invoices = relationship('Invoice', back_populates='minicategory')
    
    def __repr__(self):
        return f'<Minicategory {self.name} (Subcategory: {self.subcategory.name if self.subcategory else "None"})>'
    
    def to_dict(self):
        """Converti il modello in dizionario"""
        return {
            'id': self.id,
            'subcategory_id': self.subcategory_id,
            'name': self.name,
            'description': self.description,
            'code': self.code,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'subcategory': self.subcategory.to_dict() if self.subcategory else None,
            'category': self.subcategory.category.to_dict() if self.subcategory and self.subcategory.category else None
        }
    
    @classmethod
    def get_by_subcategory(cls, subcategory_id):
        """Ottieni minicategorie per sottocategoria"""
        return cls.query.filter_by(subcategory_id=subcategory_id, is_active=True).order_by(cls.name).all()
    
    @classmethod
    def find_by_name_and_subcategory(cls, name, subcategory_id):
        """Trova minicategoria per nome e sottocategoria"""
        return cls.query.filter_by(name=name, subcategory_id=subcategory_id).first()
