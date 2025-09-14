"""
Azure Key Vault client per recuperare segreti in modo sicuro
"""
import os
import logging
from typing import Optional
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
from azure.core.exceptions import ResourceNotFoundError

logger = logging.getLogger(__name__)


class KeyVaultClient:
    """Client per Azure Key Vault"""
    
    def __init__(self, vault_url: Optional[str] = None):
        """
        Inizializza il client Key Vault
        
        Args:
            vault_url: URL del Key Vault. Se None, usa variabile ambiente.
        """
        self.vault_url = vault_url or os.getenv('AZURE_KEY_VAULT_URL')
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Inizializza il client Azure Key Vault"""
        if not self.vault_url:
            logger.warning("Azure Key Vault URL non configurato")
            return
        
        try:
            # In Azure App Service usa ManagedIdentityCredential
            # In locale usa DefaultAzureCredential (Azure CLI)
            if os.getenv('WEBSITE_SITE_NAME'):  # Running in Azure App Service
                credential = ManagedIdentityCredential()
                logger.info("Usando ManagedIdentityCredential per Azure App Service")
            else:
                credential = DefaultAzureCredential()
                logger.info("Usando DefaultAzureCredential per sviluppo locale")
            
            self.client = SecretClient(
                vault_url=self.vault_url,
                credential=credential
            )
            
            logger.info(f"Client Key Vault inizializzato per: {self.vault_url}")
            
        except Exception as e:
            logger.error(f"Errore inizializzazione Key Vault client: {e}")
            self.client = None
    
    def get_secret(self, secret_name: str, default_value: Optional[str] = None) -> Optional[str]:
        """
        Recupera un segreto dal Key Vault
        
        Args:
            secret_name: Nome del segreto
            default_value: Valore di default se segreto non trovato
            
        Returns:
            Valore del segreto o default_value
        """
        if not self.client:
            logger.warning(f"Key Vault client non disponibile, uso default per: {secret_name}")
            return default_value
        
        try:
            secret = self.client.get_secret(secret_name)
            logger.debug(f"Segreto '{secret_name}' recuperato da Key Vault")
            return secret.value
            
        except ResourceNotFoundError:
            logger.warning(f"Segreto '{secret_name}' non trovato in Key Vault")
            return default_value
            
        except Exception as e:
            logger.error(f"Errore recupero segreto '{secret_name}': {e}")
            return default_value
    
    def set_secret(self, secret_name: str, secret_value: str) -> bool:
        """
        Imposta un segreto nel Key Vault
        
        Args:
            secret_name: Nome del segreto
            secret_value: Valore del segreto
            
        Returns:
            True se operazione riuscita
        """
        if not self.client:
            logger.error("Key Vault client non disponibile")
            return False
        
        try:
            self.client.set_secret(secret_name, secret_value)
            logger.info(f"Segreto '{secret_name}' impostato in Key Vault")
            return True
            
        except Exception as e:
            logger.error(f"Errore impostazione segreto '{secret_name}': {e}")
            return False
    
    def health_check(self) -> dict:
        """
        Verifica stato connessione Key Vault
        
        Returns:
            Dict con informazioni stato
        """
        if not self.client:
            return {
                'status': 'unhealthy',
                'message': 'Key Vault client non inizializzato',
                'vault_url': self.vault_url
            }
        
        try:
            # Test con un segreto dummy
            test_secret = self.get_secret('health-check-test', 'default')
            return {
                'status': 'healthy',
                'message': 'Key Vault accessibile',
                'vault_url': self.vault_url
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'message': f'Errore accesso Key Vault: {str(e)}',
                'vault_url': self.vault_url
            }


# Singleton instance
_keyvault_client = None


def get_keyvault_client() -> KeyVaultClient:
    """
    Ottieni istanza singleton del client Key Vault
    
    Returns:
        Istanza KeyVaultClient
    """
    global _keyvault_client
    if _keyvault_client is None:
        _keyvault_client = KeyVaultClient()
    return _keyvault_client


def get_secret_or_env(secret_name: str, env_var: str, default: Optional[str] = None) -> Optional[str]:
    """
    Helper per ottenere segreto da Key Vault o variabile ambiente
    
    Args:
        secret_name: Nome segreto in Key Vault
        env_var: Nome variabile ambiente di fallback
        default: Valore di default
        
    Returns:
        Valore del segreto/variabile o default
    """
    # Prima prova Key Vault
    kv_client = get_keyvault_client()
    value = kv_client.get_secret(secret_name)
    
    if value is not None:
        return value
    
    # Fallback a variabile ambiente
    env_value = os.getenv(env_var)
    if env_value is not None:
        return env_value
    
    # Default value
    return default
