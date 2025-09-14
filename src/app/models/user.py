# User Model

from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from ..extensions import db
from .base import BaseModel


class User(BaseModel):
    """Modello per gli utenti dell'applicazione."""
    
    __tablename__ = 'users'
    
    # Campi base
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    
    # Informazioni personali
    first_name = db.Column(db.String(50), nullable=True)
    last_name = db.Column(db.String(50), nullable=True)
    avatar_url = db.Column(db.String(255), nullable=True)
    
    # Status e permessi
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)  # Deprecated - usar role
    email_verified = db.Column(db.Boolean, default=False, nullable=False)
    
    # Relazioni
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=True, index=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=True, index=True)
    
    # Timestamps
    last_login = db.Column(db.DateTime, nullable=True)
    
    def set_password(self, password):
        """Imposta la password dell'utente."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Verifica la password dell'utente."""
        return check_password_hash(self.password_hash, password)
    
    def update_last_login(self):
        """Aggiorna l'ultimo login."""
        self.last_login = datetime.utcnow()
        db.session.commit()
    
    @property
    def full_name(self):
        """Ritorna il nome completo."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username
    
    @property
    def company_name(self):
        """Ritorna il nome dell'azienda."""
        return self.company.display_name if self.company else None
    
    @property
    def role_name(self):
        """Ritorna il nome del ruolo."""
        return self.role.display_name if self.role else 'Nessun Ruolo'
    
    @property
    def access_level(self):
        """Ritorna il livello di accesso."""
        return self.role.access_level if self.role else 999  # Nessun accesso se non ha ruolo
    
    def has_permission(self, permission_name):
        """Verifica se l'utente ha un permesso specifico."""
        if not self.role or not self.is_active:
            return False
        return self.role.has_permission(permission_name)
    
    def can_access_level(self, required_level):
        """Verifica se l'utente può accedere a un livello specifico."""
        if not self.role or not self.is_active:
            return False
        return self.role.can_access_level(required_level)
    
    def is_rohirrim(self):
        """Verifica se l'utente è un Rohirrim (developer)."""
        return self.role and self.role.is_rohirrim() and self.is_active
    
    def is_lord(self):
        """Verifica se l'utente è un Lord (admin)."""
        return self.role and self.role.is_lord() and self.is_active
    
    def is_dunedain(self):
        """Verifica se l'utente è un Dunedain (viewer)."""
        return self.role and self.role.is_dunedain() and self.is_active
    
    def can_manage_company(self, company_id=None):
        """Verifica se l'utente può gestire un'azienda specifica."""
        if not self.is_active:
            return False
        
        # Rohirrim può gestire tutte le aziende
        if self.is_rohirrim():
            return True
        
        # Lord può gestire solo la propria azienda
        if self.is_lord():
            target_company = company_id or (self.company_id if self.company else None)
            return target_company == self.company_id
        
        return False
    
    def can_view_company(self, company_id=None):
        """Verifica se l'utente può visualizzare un'azienda specifica."""
        if not self.is_active:
            return False
        
        # Rohirrim può vedere tutte le aziende
        if self.is_rohirrim():
            return True
        
        # Lord e Dunedain possono vedere solo la propria azienda
        if self.is_lord() or self.is_dunedain():
            target_company = company_id or (self.company_id if self.company else None)
            return target_company == self.company_id
        
        return False
    
    def get_permissions_list(self):
        """Ritorna la lista dei permessi dell'utente."""
        if not self.role or not self.is_active:
            return []
        return self.role.get_permissions_list()
    
    def set_company_and_role(self, company_id, role_name=None):
        """Imposta azienda e ruolo (di default Lord se non specificato)."""
        self.company_id = company_id
        
        if role_name:
            from .role import Role
            role = Role.query.filter_by(name=role_name, is_active=True).first()
            if role:
                self.role_id = role.id
        else:
            # Imposta ruolo di default (Lord)
            from .role import Role
            default_role = Role.get_default_role()
            if default_role:
                self.role_id = default_role.id
    
    def to_dict(self, include_sensitive=False):
        """Converte il modello in dizionario."""
        data = {
            'id': self.id,
            'email': self.email,
            'username': self.username,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': self.full_name,
            'avatar_url': self.avatar_url,
            'is_active': self.is_active,
            'email_verified': self.email_verified,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'company_id': self.company_id,
            'company_name': self.company_name,
            'role_id': self.role_id,
            'role_name': self.role_name,
            'access_level': self.access_level,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
        
        if include_sensitive:
            data.update({
                'is_admin': self.is_admin,  # Deprecated
                'permissions': self.get_permissions_list(),
                'is_rohirrim': self.is_rohirrim(),
                'is_lord': self.is_lord(),
                'is_dunedain': self.is_dunedain()
            })
            
        return data
    
    def __repr__(self):
        return f'<User {self.username}>'
