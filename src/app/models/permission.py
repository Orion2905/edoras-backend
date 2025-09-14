# Permission Model

from ..extensions import db
from .base import BaseModel


class Permission(BaseModel):
    """Modello per i permessi associati ai ruoli."""
    
    __tablename__ = 'permissions'
    
    # Campi base
    name = db.Column(db.String(100), nullable=False, index=True)
    display_name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    
    # Categoria del permesso
    category = db.Column(db.String(50), nullable=False, index=True)
    
    # Status
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Relazione con ruolo
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False, index=True)
    
    # Indice unico per evitare permessi duplicati per lo stesso ruolo
    __table_args__ = (
        db.UniqueConstraint('role_id', 'name', name='uq_role_permission'),
        db.Index('idx_permission_category_active', 'category', 'is_active'),
    )
    
    def __init__(self, **kwargs):
        super(Permission, self).__init__(**kwargs)
    
    @classmethod
    def get_by_category(cls, category, active_only=True):
        """Ritorna i permessi per categoria."""
        query = cls.query.filter_by(category=category)
        if active_only:
            query = query.filter_by(is_active=True)
        return query.all()
    
    @classmethod
    def get_by_role(cls, role_id, active_only=True):
        """Ritorna i permessi per ruolo."""
        query = cls.query.filter_by(role_id=role_id)
        if active_only:
            query = query.filter_by(is_active=True)
        return query.all()
    
    def to_dict(self):
        """Converte il modello in dizionario."""
        return {
            'id': self.id,
            'name': self.name,
            'display_name': self.display_name,
            'description': self.description,
            'category': self.category,
            'is_active': self.is_active,
            'role_id': self.role_id,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def __repr__(self):
        return f'<Permission {self.name} for Role {self.role_id}>'


# Funzione per inizializzare i permessi di default
def init_default_permissions():
    """Inizializza i permessi di default per i ruoli."""
    
    from .role import Role
    
    # Ottieni i ruoli
    rohirrim = Role.query.filter_by(name='rohirrim').first()
    lord = Role.query.filter_by(name='lord').first()
    dunedain = Role.query.filter_by(name='dunedain').first()
    
    if not all([rohirrim, lord, dunedain]):
        print("Errore: I ruoli non sono stati trovati. Inizializza prima i ruoli.")
        return
    
    # Definisci i permessi per categoria
    permissions_data = {
        # Permessi Rohirrim (Developer) - TUTTO
        rohirrim.id: [
            # System Admin
            ('system.admin', 'Amministrazione Sistema', 'Accesso completo amministrazione sistema', 'system'),
            ('system.debug', 'Debug Sistema', 'Accesso a funzionalità di debug e sviluppo', 'system'),
            ('system.logs', 'Logs Sistema', 'Visualizzazione e gestione logs', 'system'),
            ('system.backup', 'Backup Sistema', 'Gestione backup e ripristino', 'system'),
            
            # Company Management
            ('company.create', 'Crea Aziende', 'Creare nuove aziende', 'company'),
            ('company.read.all', 'Visualizza Tutte Aziende', 'Visualizzare dati di tutte le aziende', 'company'),
            ('company.update.all', 'Modifica Tutte Aziende', 'Modificare dati di tutte le aziende', 'company'),
            ('company.delete', 'Elimina Aziende', 'Eliminare aziende', 'company'),
            
            # User Management
            ('user.create', 'Crea Utenti', 'Creare nuovi utenti', 'user'),
            ('user.read.all', 'Visualizza Tutti Utenti', 'Visualizzare dati di tutti gli utenti', 'user'),
            ('user.update.all', 'Modifica Tutti Utenti', 'Modificare dati di tutti gli utenti', 'user'),
            ('user.delete', 'Elimina Utenti', 'Eliminare utenti', 'user'),
            ('user.roles.manage', 'Gestisci Ruoli', 'Assegnare e modificare ruoli', 'user'),
            
            # Property Management
            ('property.create', 'Crea Proprietà', 'Creare unità immobiliari', 'property'),
            ('property.read.all', 'Visualizza Tutte Proprietà', 'Visualizzare tutte le proprietà', 'property'),
            ('property.update.all', 'Modifica Tutte Proprietà', 'Modificare tutte le proprietà', 'property'),
            ('property.delete', 'Elimina Proprietà', 'Eliminare proprietà', 'property'),
            
            # Invoice Management
            ('invoice.create', 'Crea Fatture', 'Creare fatture', 'invoice'),
            ('invoice.read.all', 'Visualizza Tutte Fatture', 'Visualizzare tutte le fatture', 'invoice'),
            ('invoice.update.all', 'Modifica Tutte Fatture', 'Modificare tutte le fatture', 'invoice'),
            ('invoice.delete', 'Elimina Fatture', 'Eliminare fatture', 'invoice'),
            
            # Booking Management
            ('booking.create', 'Crea Prenotazioni', 'Creare prenotazioni', 'booking'),
            ('booking.read.all', 'Visualizza Tutte Prenotazioni', 'Visualizzare tutte le prenotazioni', 'booking'),
            ('booking.update.all', 'Modifica Tutte Prenotazioni', 'Modificare tutte le prenotazioni', 'booking'),
            ('booking.delete', 'Elimina Prenotazioni', 'Eliminare prenotazioni', 'booking'),
            
            # POD Management
            ('pod.create', 'Crea POD', 'Creare POD', 'pod'),
            ('pod.read.all', 'Visualizza Tutti POD', 'Visualizzare tutti i POD', 'pod'),
            ('pod.update.all', 'Modifica Tutti POD', 'Modificare tutti i POD', 'pod'),
            ('pod.delete', 'Elimina POD', 'Eliminare POD', 'pod'),
        ],
        
        # Permessi Lord (Admin) - Solo la propria azienda
        lord.id: [
            # Company Management (solo propria)
            ('company.read.own', 'Visualizza Propria Azienda', 'Visualizzare dati della propria azienda', 'company'),
            ('company.update.own', 'Modifica Propria Azienda', 'Modificare dati della propria azienda', 'company'),
            
            # User Management (solo propria azienda)
            ('user.create.company', 'Crea Utenti Azienda', 'Creare utenti per la propria azienda', 'user'),
            ('user.read.company', 'Visualizza Utenti Azienda', 'Visualizzare utenti della propria azienda', 'user'),
            ('user.update.company', 'Modifica Utenti Azienda', 'Modificare utenti della propria azienda', 'user'),
            ('user.deactivate.company', 'Disattiva Utenti Azienda', 'Disattivare utenti della propria azienda', 'user'),
            
            # Property Management (solo propria azienda)
            ('property.create', 'Crea Proprietà', 'Creare unità immobiliari', 'property'),
            ('property.read.company', 'Visualizza Proprietà Azienda', 'Visualizzare proprietà della propria azienda', 'property'),
            ('property.update.company', 'Modifica Proprietà Azienda', 'Modificare proprietà della propria azienda', 'property'),
            ('property.delete.company', 'Elimina Proprietà Azienda', 'Eliminare proprietà della propria azienda', 'property'),
            
            # Invoice Management (solo propria azienda)
            ('invoice.create', 'Crea Fatture', 'Creare fatture', 'invoice'),
            ('invoice.read.company', 'Visualizza Fatture Azienda', 'Visualizzare fatture della propria azienda', 'invoice'),
            ('invoice.update.company', 'Modifica Fatture Azienda', 'Modificare fatture della propria azienda', 'invoice'),
            ('invoice.delete.company', 'Elimina Fatture Azienda', 'Eliminare fatture della propria azienda', 'invoice'),
            
            # Booking Management (solo propria azienda)
            ('booking.create', 'Crea Prenotazioni', 'Creare prenotazioni', 'booking'),
            ('booking.read.company', 'Visualizza Prenotazioni Azienda', 'Visualizzare prenotazioni della propria azienda', 'booking'),
            ('booking.update.company', 'Modifica Prenotazioni Azienda', 'Modificare prenotazioni della propria azienda', 'booking'),
            ('booking.delete.company', 'Elimina Prenotazioni Azienda', 'Eliminare prenotazioni della propria azienda', 'booking'),
            
            # POD Management (solo propria azienda)
            ('pod.create', 'Crea POD', 'Creare POD', 'pod'),
            ('pod.read.company', 'Visualizza POD Azienda', 'Visualizzare POD della propria azienda', 'pod'),
            ('pod.update.company', 'Modifica POD Azienda', 'Modificare POD della propria azienda', 'pod'),
            ('pod.delete.company', 'Elimina POD Azienda', 'Eliminare POD della propria azienda', 'pod'),
        ],
        
        # Permessi Dunedain (Viewer) - Solo lettura
        dunedain.id: [
            # Company Management (solo lettura propria)
            ('company.read.own', 'Visualizza Propria Azienda', 'Visualizzare dati della propria azienda', 'company'),
            
            # User Management (solo lettura propria azienda)
            ('user.read.company', 'Visualizza Utenti Azienda', 'Visualizzare utenti della propria azienda', 'user'),
            
            # Property Management (solo lettura propria azienda)
            ('property.read.company', 'Visualizza Proprietà Azienda', 'Visualizzare proprietà della propria azienda', 'property'),
            
            # Invoice Management (solo lettura propria azienda)
            ('invoice.read.company', 'Visualizza Fatture Azienda', 'Visualizzare fatture della propria azienda', 'invoice'),
            
            # Booking Management (solo lettura propria azienda)
            ('booking.read.company', 'Visualizza Prenotazioni Azienda', 'Visualizzare prenotazioni della propria azienda', 'booking'),
            
            # POD Management (solo lettura propria azienda)
            ('pod.read.company', 'Visualizza POD Azienda', 'Visualizzare POD della propria azienda', 'pod'),
        ]
    }
    
    # Crea i permessi
    for role_id, permissions in permissions_data.items():
        for name, display_name, description, category in permissions:
            # Verifica se il permesso esiste già
            existing = Permission.query.filter_by(role_id=role_id, name=name).first()
            if not existing:
                permission = Permission(
                    name=name,
                    display_name=display_name,
                    description=description,
                    category=category,
                    role_id=role_id,
                    is_active=True
                )
                db.session.add(permission)
    
    try:
        db.session.commit()
        print("Permessi di default inizializzati con successo!")
    except Exception as e:
        db.session.rollback()
        print(f"Errore nell'inizializzazione dei permessi: {e}")
