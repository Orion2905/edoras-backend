#!/usr/bin/env python3
"""
Script di test per gli endpoint Company CRUD
"""

import json
import requests
from datetime import datetime

# Configurazione base
BASE_URL = "http://localhost:5000/api/v1"

def test_company_endpoints():
    """Test di base per gli endpoint Company."""
    
    print("🧪 Test degli endpoint Company CRUD")
    print("=" * 50)
    
    # Test GET /companies (senza autenticazione - dovrebbe fallire)
    print("\n1. Test GET /companies (senza auth)")
    try:
        response = requests.get(f"{BASE_URL}/companies")
        print(f"   Status: {response.status_code}")
        if response.status_code == 401:
            print("   ✅ Autenticazione richiesta correttamente")
        else:
            print(f"   ❌ Risposta inattesa: {response.json()}")
    except Exception as e:
        print(f"   ❌ Errore: {e}")
    
    # Test GET /companies/1 (senza autenticazione - dovrebbe fallire)
    print("\n2. Test GET /companies/1 (senza auth)")
    try:
        response = requests.get(f"{BASE_URL}/companies/1")
        print(f"   Status: {response.status_code}")
        if response.status_code == 401:
            print("   ✅ Autenticazione richiesta correttamente")
        else:
            print(f"   ❌ Risposta inattesa: {response.json()}")
    except Exception as e:
        print(f"   ❌ Errore: {e}")
    
    # Test POST /companies (senza autenticazione - dovrebbe fallire)
    print("\n3. Test POST /companies (senza auth)")
    try:
        company_data = {
            "name": "Test Company",
            "legal_name": "Test Company S.r.l.",
            "vat_number": "IT12345678901",
            "email": "test@company.com"
        }
        response = requests.post(
            f"{BASE_URL}/companies",
            json=company_data,
            headers={"Content-Type": "application/json"}
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 401:
            print("   ✅ Autenticazione richiesta correttamente")
        else:
            print(f"   ❌ Risposta inattesa: {response.json()}")
    except Exception as e:
        print(f"   ❌ Errore: {e}")
    
    print("\n" + "=" * 50)
    print("📝 Note:")
    print("- Tutti i test dovrebbero restituire 401 (Unauthorized)")
    print("- Per test completi servono token JWT validi")
    print("- Gli endpoint sono protetti correttamente")
    
    return True

def test_schemas():
    """Test di validazione degli schemi Marshmallow."""
    
    print("\n🔍 Test di validazione schemi")
    print("=" * 30)
    
    # Importa gli schemi per testare la validazione
    try:
        import sys
        sys.path.append('/Users/orionstanchieri/Documents/Projects/Edoras/backend/src')
        
        from app.schemas.company import (
            company_create_schema,
            company_update_schema
        )
        
        # Test schema di creazione valido
        print("\n1. Test schema creazione (valido)")
        valid_data = {
            "name": "Test Company",
            "legal_name": "Test Company S.r.l.",
            "vat_number": "IT12345678901",
            "email": "test@company.com",
            "city": "Milano",
            "country": "IT"
        }
        
        try:
            result = company_create_schema.load(valid_data)
            print("   ✅ Validazione OK")
            print(f"   Dati: {result}")
        except Exception as e:
            print(f"   ❌ Errore validazione: {e}")
        
        # Test schema di creazione non valido
        print("\n2. Test schema creazione (non valido)")
        invalid_data = {
            "name": "",  # Nome vuoto
            "email": "invalid-email",  # Email non valida
            "country": "INVALID"  # Codice paese troppo lungo
        }
        
        try:
            result = company_create_schema.load(invalid_data)
            print("   ❌ Validazione dovrebbe fallire!")
        except Exception as e:
            print("   ✅ Validazione fallita correttamente")
            print(f"   Errori: {e}")
        
        # Test schema di aggiornamento
        print("\n3. Test schema aggiornamento")
        update_data = {
            "name": "Updated Company Name",
            "is_active": False
        }
        
        try:
            result = company_update_schema.load(update_data)
            print("   ✅ Validazione OK")
            print(f"   Dati: {result}")
        except Exception as e:
            print(f"   ❌ Errore validazione: {e}")
            
    except ImportError as e:
        print(f"   ❌ Errore import schemi: {e}")
        return False
    
    return True

def main():
    """Funzione principale di test."""
    
    print("🚀 Test del sistema Company CRUD")
    print("Data:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print()
    
    # Test degli endpoint
    try:
        test_company_endpoints()
    except Exception as e:
        print(f"❌ Errore nei test endpoint: {e}")
    
    # Test degli schemi
    try:
        test_schemas()
    except Exception as e:
        print(f"❌ Errore nei test schemi: {e}")
    
    print("\n🎯 Test completati!")

if __name__ == "__main__":
    main()
