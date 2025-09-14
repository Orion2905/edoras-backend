# Base Model

from ..extensions import db


class BaseModel(db.Model):
    """
    Modello base con campi comuni per tutti i modelli.
    """
    __abstract__ = True
    
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(
        db.DateTime, 
        default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp()
    )
    
    def save(self):
        """Salva il modello nel database."""
        db.session.add(self)
        db.session.commit()
        return self
    
    def delete(self):
        """Elimina il modello dal database."""
        db.session.delete(self)
        db.session.commit()
        return True
    
    def to_dict(self):
        """Converte il modello in dizionario."""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
