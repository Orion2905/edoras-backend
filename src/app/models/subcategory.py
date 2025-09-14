"""
Subcategory model per gestire le micro categorie delle fatture
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..extensions import db


class Subcategory(db.Model):
    """Modello per le micro categorie delle fatture"""
    
    __tablename__ = 'subcategories'
    
    # Primary Key
    id = Column(Integer, primary_key=True)
    
    # Foreign Key
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=False)
    
    # Subcategory Info
    name = Column(String(100), nullable=False, index=True)
    description = Column(String(255), nullable=True)
    code = Column(String(20), nullable=True, index=True)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # Relationships
    category = relationship('Category', back_populates='subcategories')
    minicategories = relationship('Minicategory', back_populates='subcategory', cascade='all, delete-orphan')
    invoices = relationship('Invoice', back_populates='subcategory')
    
    def __repr__(self):
        return f'<Subcategory {self.name} (Category: {self.category.name if self.category else "None"})>'
    
    def to_dict(self):
        """Converti il modello in dizionario"""
        return {
            'id': self.id,
            'category_id': self.category_id,
            'name': self.name,
            'description': self.description,
            'code': self.code,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'category': self.category.to_dict() if self.category else None,
            'minicategories_count': len(self.minicategories) if self.minicategories else 0
        }
    
    @classmethod
    def get_by_category(cls, category_id):
        """Ottieni sottocategorie per categoria"""
        return cls.query.filter_by(category_id=category_id, is_active=True).order_by(cls.name).all()
    
    @classmethod
    def find_by_name_and_category(cls, name, category_id):
        """Trova sottocategoria per nome e categoria"""
        return cls.query.filter_by(name=name, category_id=category_id).first()
