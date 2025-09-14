# Role Model

from ..extensions import db
from .base import BaseModel


class Role(BaseModel):
    """Modello per i ruoli degli utenti."""
    
    __tablename__ = 'roles'
    
    # Campi base
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)
    display_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    
    # Livello di accesso (1 = più alto, 3 = più basso)
    access_level = db.Column(db.Integer, nullable=False, index=True)
    
    # Status
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_default = db.Column(db.Boolean, default=False, nullable=False)
    
    # Relazioni
    users = db.relationship('User', backref='role', lazy='dynamic')
    permissions = db.relationship('Permission', backref='role', lazy='dynamic', cascade='all, delete-orphan')
    
    def __init__(self, **kwargs):
        super(Role, self).__init__(**kwargs)
    
    @classmethod
    def get_rohirrim_role(cls):
        """Ritorna il ruolo Rohirrim (developer)."""
        return cls.query.filter_by(name='rohirrim').first()
    
    @classmethod
    def get_lord_role(cls):
        """Ritorna il ruolo Lord (admin)."""
        return cls.query.filter_by(name='lord').first()
    
    @classmethod
    def get_dunedain_role(cls):
        """Ritorna il ruolo Dunedain (viewer)."""
        return cls.query.filter_by(name='dunedain').first()
    
    @classmethod
    def get_default_role(cls):
        """Ritorna il ruolo di default."""
        return cls.query.filter_by(is_default=True).first()
    
    @classmethod
    def get_by_access_level(cls, level):
        """Ritorna ruoli per livello di accesso."""
        return cls.query.filter_by(access_level=level, is_active=True).all()
    
    def has_permission(self, permission_name):
        """Verifica se il ruolo ha un permesso specifico."""
        return self.permissions.filter_by(name=permission_name, is_active=True).first() is not None
    
    def get_permissions_list(self):
        """Ritorna la lista dei permessi attivi del ruolo."""
        return [perm.name for perm in self.permissions.filter_by(is_active=True).all()]
    
    def can_access_level(self, required_level):
        """Verifica se il ruolo può accedere a un livello specifico."""
        return self.access_level <= required_level
    
    def is_rohirrim(self):
        """Verifica se è il ruolo Rohirrim (developer)."""
        return self.name == 'rohirrim'
    
    def is_lord(self):
        """Verifica se è il ruolo Lord (admin)."""
        return self.name == 'lord'
    
    def is_dunedain(self):
        """Verifica se è il ruolo Dunedain (viewer)."""
        return self.name == 'dunedain'
    
    def to_dict(self, include_permissions=False):
        """Converte il modello in dizionario."""
        data = {
            'id': self.id,
            'name': self.name,
            'display_name': self.display_name,
            'description': self.description,
            'access_level': self.access_level,
            'is_active': self.is_active,
            'is_default': self.is_default,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
        
        if include_permissions:
            data['permissions'] = self.get_permissions_list()
            
        return data
    
    def __repr__(self):
        return f'<Role {self.name} (Level {self.access_level})>'


# Funzione per inizializzare i ruoli di default
def init_default_roles():
    """Inizializza i ruoli di default ispirati al Signore degli Anelli."""
    
    # Rohirrim - Developer (massimo accesso)
    rohirrim = Role.query.filter_by(name='rohirrim').first()
    if not rohirrim:
        rohirrim = Role(
            name='rohirrim',
            display_name='Rohirrim',
            description='Guerrieri di Rohan - Accesso completo a tutto il sistema, inclusi dati di sviluppo e debug',
            access_level=1,
            is_active=True,
            is_default=False
        )
        db.session.add(rohirrim)
    
    # Lord - Admin (accesso completo ai propri dati)
    lord = Role.query.filter_by(name='lord').first()
    if not lord:
        lord = Role(
            name='lord',
            display_name='Lord',
            description='Signori della Terra di Mezzo - Accesso completo alle funzionalità della propria azienda',
            access_level=2,
            is_active=True,
            is_default=True  # Ruolo di default
        )
        db.session.add(lord)
    
    # Dunedain - Viewer (solo visualizzazione)
    dunedain = Role.query.filter_by(name='dunedain').first()
    if not dunedain:
        dunedain = Role(
            name='dunedain',
            display_name='Dunedain',
            description='Raminghi del Nord - Accesso in sola lettura ai dati della propria azienda',
            access_level=3,
            is_active=True,
            is_default=False
        )
        db.session.add(dunedain)
    
    try:
        db.session.commit()
        print("Ruoli di default inizializzati con successo!")
    except Exception as e:
        db.session.rollback()
        print(f"Errore nell'inizializzazione dei ruoli: {e}")
