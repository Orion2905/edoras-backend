# Flask Services

from ..models.user import User
from ..extensions import db


class UserService:
    """Service per la gestione degli utenti."""
    
    @staticmethod
    def create_user(email, username, password, first_name=None, last_name=None):
        """
        Crea un nuovo utente.
        
        Args:
            email (str): Email dell'utente
            username (str): Username dell'utente  
            password (str): Password dell'utente
            first_name (str, optional): Nome dell'utente
            last_name (str, optional): Cognome dell'utente
            
        Returns:
            User: L'utente creato
            
        Raises:
            ValueError: Se email o username sono già in uso
        """
        # Verifica se email già esiste
        if User.query.filter_by(email=email).first():
            raise ValueError("Email already exists")
            
        # Verifica se username già esiste
        if User.query.filter_by(username=username).first():
            raise ValueError("Username already exists")
            
        # Crea nuovo utente
        user = User(
            email=email,
            username=username,
            first_name=first_name,
            last_name=last_name
        )
        user.set_password(password)
        user.save()
        
        return user
    
    @staticmethod
    def authenticate_user(email, password):
        """
        Autentica un utente.
        
        Args:
            email (str): Email dell'utente
            password (str): Password dell'utente
            
        Returns:
            User|None: L'utente se autenticato, None altrimenti
        """
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password) and user.is_active:
            user.update_last_login()
            return user
            
        return None
    
    @staticmethod
    def get_user_by_id(user_id):
        """
        Ottieni utente per ID.
        
        Args:
            user_id (int): ID dell'utente
            
        Returns:
            User|None: L'utente se trovato, None altrimenti
        """
        return User.query.get(user_id)
    
    @staticmethod
    def update_user(user, **kwargs):
        """
        Aggiorna un utente.
        
        Args:
            user (User): L'utente da aggiornare
            **kwargs: Campi da aggiornare
            
        Returns:
            User: L'utente aggiornato
        """
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)
                
        user.save()
        return user
    
    @staticmethod
    def change_password(user, current_password, new_password):
        """
        Cambia la password di un utente.
        
        Args:
            user (User): L'utente
            current_password (str): Password attuale
            new_password (str): Nuova password
            
        Returns:
            bool: True se password cambiata, False altrimenti
        """
        if not user.check_password(current_password):
            return False
            
        user.set_password(new_password)
        user.save()
        return True
    
    @staticmethod
    def delete_user(user):
        """
        Elimina un utente.
        
        Args:
            user (User): L'utente da eliminare
            
        Returns:
            bool: True se eliminato con successo
        """
        user.delete()
        return True
