#!/usr/bin/env python3
"""
Test script per verificare le funzionalità della tabella scraper_access
"""

import os
import sys
import json
from datetime import datetime, timedelta

# Aggiungi il percorso del src al PYTHONPATH
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

# Imposta la stringa di connessione direttamente per il test
os.environ['DATABASE_URL'] = 'mssql+pyodbc://edorasadmin:EdorasSecure123!@edoras-sql-2025.database.windows.net/edoras-prod-database?driver=ODBC+Driver+17+for+SQL+Server'

from app import create_app
from app.extensions import db
from app.models import Company, ScraperAccess, Role, User

def test_scraper_access():
    """Test completo delle funzionalità ScraperAccess"""
    
    # Usa configurazione development per usare la stringa di connessione diretta
    app = create_app('development')
    
    with app.app_context():
        print("🧪 Avvio test ScraperAccess...")
        
        try:
            # 0. Pulizia dati test precedenti
            print("🧹 Pulizia dati test precedenti...")
            
            # Rimuovi tutti gli scraper access della company di test
            test_company = Company.query.filter_by(name="Test Company ScraperAccess").first()
            if test_company:
                ScraperAccess.query.filter_by(company_id=test_company.id).delete()
                Company.query.filter_by(name="Test Company ScraperAccess").delete()
                db.session.commit()
                print("✅ Dati test precedenti rimossi")
            
            # 1. Trova o crea una company di test
            company = Company.query.filter_by(name="Test Company ScraperAccess").first()
            if not company:
                company = Company(
                    name="Test Company ScraperAccess",
                    vat_number="IT12345678901",
                    tax_code="12345678901",
                    address="Via Test 123",
                    city="Roma",
                    province="RM",
                    postal_code="00100",
                    country="IT",
                    phone="+39 06 12345678",
                    email="test@scrapertest.com"
                )
                db.session.add(company)
                db.session.commit()
                print(f"✅ Company creata: {company.name} (ID: {company.id})")
            else:
                print(f"✅ Company trovata: {company.name} (ID: {company.id})")
            
            # 2. Test creazione ScraperAccess per Energia
            print("\n📋 Test 1: Creazione accesso Enel Energia")
            
            enel_credentials = {
                "username": "test.user@email.com",
                "password": "password123",
                "codice_contratto": "123456789",
                "codice_cliente": "987654321",
                "additional_info": {
                    "note": "Contratto domestico",
                    "tipo_fornitura": "domestica"
                }
            }
            
            enel_access = ScraperAccess(
                company_id=company.id,
                platform_name="Enel Energia",
                platform_type="energia",
                platform_url="https://www.enel.it/area-clienti",
                access_data=enel_credentials,
                scrape_frequency="weekly",
                auto_scrape=True,
                notes="Account principale per il consumo domestico"
            )
            
            db.session.add(enel_access)
            db.session.commit()
            print(f"✅ ScraperAccess Enel creato (ID: {enel_access.id})")
            
            # 3. Test creazione ScraperAccess per Gas
            print("\n📋 Test 2: Creazione accesso ENI Gas")
            
            eni_credentials = {
                "username": "test.gas@email.com",
                "password": "gaspass456",
                "pdr": "14657481234567890123",
                "customer_code": "GAS987654",
                "fiscal_code": "RSSMRA85M01H501Z"
            }
            
            eni_access = ScraperAccess(
                company_id=company.id,
                platform_name="ENI Gas e Luce",
                platform_type="gas",
                platform_url="https://www.eniplenitude.com/area-clienti",
                access_data=eni_credentials,
                scrape_frequency="monthly",
                auto_scrape=False,
                notes="Fornitura gas metano"
            )
            
            db.session.add(eni_access)
            db.session.commit()
            print(f"✅ ScraperAccess ENI creato (ID: {eni_access.id})")
            
            # 4. Test creazione ScraperAccess per Telecom
            print("\n📋 Test 3: Creazione accesso TIM")
            
            tim_credentials = {
                "username": "3401234567",
                "password": "timpass789",
                "customer_id": "TIM123456789",
                "contract_number": "CT789012345",
                "api_key": "tim_api_key_12345",
                "services": ["mobile", "fibra", "voip"]
            }
            
            tim_access = ScraperAccess(
                company_id=company.id,
                platform_name="TIM MyTIM",
                platform_type="telecom",
                platform_url="https://www.tim.it/assistenza/area-clienti-privati",
                access_data=tim_credentials,
                scrape_frequency="daily",
                auto_scrape=True,
                notes="Account completo con mobile e fibra",
                config_json={"notifications": True, "detailed_usage": True}
            )
            
            db.session.add(tim_access)
            db.session.commit()
            print(f"✅ ScraperAccess TIM creato (ID: {tim_access.id})")
            
            # 5. Test creazione ScraperAccess per Banca
            print("\n📋 Test 4: Creazione accesso Intesa Sanpaolo")
            
            intesa_credentials = {
                "username": "user123456",
                "password": "bankpass000",
                "customer_code": "ISP987654321",
                "iban": "IT60X0306909606100000117681",
                "card_number": "****-****-****-1234",
                "secure_key": "ABCD1234EFGH5678"
            }
            
            intesa_access = ScraperAccess(
                company_id=company.id,
                platform_name="Intesa Sanpaolo",
                platform_type="banca",
                platform_url="https://www.intesasanpaolo.com/",
                access_data=intesa_credentials,
                scrape_frequency="weekly",
                auto_scrape=True,
                notes="Conto corrente principale",
                config_json={"export_format": "csv", "include_cards": True}
            )
            
            db.session.add(intesa_access)
            db.session.commit()
            print(f"✅ ScraperAccess Intesa creato (ID: {intesa_access.id})")
            
            # 6. Test recupero accessi per company
            print("\n🔍 Test 5: Recupero accessi per company")
            
            company_accesses = company.scraper_accesses.all()
            print(f"✅ Trovati {len(company_accesses)} accessi per {company.name}")
            
            for access in company_accesses:
                print(f"   - {access.platform_name} ({access.platform_type})")
                print(f"     Attivo: {access.is_active}, Auto-scrape: {access.auto_scrape}")
                print(f"     Frequenza: {access.scrape_frequency}")
            
            # 7. Test metodi di validazione credenziali
            print("\n🔐 Test 6: Validazione credenziali")
            
            # Test validazione Enel
            enel_valid, enel_missing = enel_access.validate_credentials()
            print(f"✅ Validazione Enel: {enel_valid}")
            if not enel_valid:
                print(f"   Campi mancanti: {enel_missing}")
            
            # Test validazione TIM
            tim_valid, tim_missing = tim_access.validate_credentials()
            print(f"✅ Validazione TIM: {tim_valid}")
            if not tim_valid:
                print(f"   Campi mancanti: {tim_missing}")
            
            # Test validazione Intesa
            intesa_valid, intesa_missing = intesa_access.validate_credentials()
            print(f"✅ Validazione Intesa: {intesa_valid}")
            if not intesa_valid:
                print(f"   Campi mancanti: {intesa_missing}")
            
            # 8. Test mascheramento credenziali
            print("\n🎭 Test 7: Mascheramento credenziali")
            
            for access in [enel_access, tim_access, intesa_access]:
                masked = access.get_masked_credentials()
                print(f"✅ {access.platform_name}:")
                for key, value in masked.items():
                    print(f"   {key}: {value}")
            
            # 9. Test metodi Company per scraper access
            print("\n🏢 Test 8: Metodi Company per ScraperAccess")
            
            # Conta accessi per tipo usando query dirette
            energia_count = ScraperAccess.query.filter_by(
                company_id=company.id,
                platform_type="energia",
                is_active=True
            ).count()
            
            gas_count = ScraperAccess.query.filter_by(
                company_id=company.id,
                platform_type="gas",
                is_active=True
            ).count()
            
            telecom_count = ScraperAccess.query.filter_by(
                company_id=company.id,
                platform_type="telecom",
                is_active=True
            ).count()
            
            banca_count = ScraperAccess.query.filter_by(
                company_id=company.id,
                platform_type="banca",
                is_active=True
            ).count()
            
            total_count = company.get_scraper_accesses_count()
            
            print(f"✅ Conteggi per tipo:")
            print(f"   Energia: {energia_count}")
            print(f"   Gas: {gas_count}")
            print(f"   Telecom: {telecom_count}")
            print(f"   Banca: {banca_count}")
            print(f"   Totale: {total_count}")
            
            # Test ricerca per piattaforma
            enel_found = company.get_scraper_access_by_platform("Enel Energia")
            tim_found = company.get_scraper_access_by_platform("TIM MyTIM")
            
            print(f"✅ Ricerca per piattaforma:")
            print(f"   Enel trovato: {enel_found.platform_name if enel_found else 'Non trovato'}")
            print(f"   TIM trovato: {tim_found.platform_name if tim_found else 'Non trovato'}")
            
            # Test verifica esistenza piattaforma
            has_enel = company.has_scraper_platform("Enel Energia")
            has_acea = company.has_scraper_platform("ACEA")
            
            print(f"✅ Verifica esistenza piattaforma:")
            print(f"   Ha Enel: {has_enel}")
            print(f"   Ha ACEA: {has_acea}")
            
            # 10. Test aggiornamento date di verifica
            print("\n⏰ Test 9: Aggiornamento date")
            
            # Simula verifica credenziali
            enel_access.mark_verified(success=True)
            tim_access.mark_verified(success=False)
            
            print(f"✅ Enel verificato: {enel_access.is_verified} ({enel_access.last_verified})")
            print(f"✅ TIM verificato: {tim_access.is_verified} ({tim_access.last_verified})")
            
            # Simula scraping
            enel_access.mark_scraped()
            
            print(f"✅ Ultimo scrape Enel: {enel_access.last_scrape}")
            
            # 11. Test query avanzate
            print("\n🔎 Test 10: Query avanzate")
            
            # Accessi attivi
            active_accesses = ScraperAccess.query.filter_by(
                company_id=company.id,
                is_active=True
            ).all()
            print(f"✅ Accessi attivi: {len(active_accesses)}")
            
            # Accessi con auto-scrape
            auto_scrape_accesses = ScraperAccess.query.filter_by(
                company_id=company.id,
                auto_scrape=True
            ).all()
            print(f"✅ Accessi con auto-scrape: {len(auto_scrape_accesses)}")
            
            # Accessi per frequenza
            weekly_accesses = ScraperAccess.query.filter_by(
                company_id=company.id,
                scrape_frequency="weekly"
            ).all()
            print(f"✅ Accessi settimanali: {len(weekly_accesses)}")
            
            # Accessi per tipo piattaforma
            energia_accesses = ScraperAccess.query.filter_by(
                company_id=company.id,
                platform_type="energia"
            ).all()
            print(f"✅ Accessi energia: {len(energia_accesses)}")
            
            db.session.commit()
            
            # 12. Test JSON di configurazione
            print("\n⚙️ Test 11: Configurazioni JSON")
            
            # Aggiorna configurazione TIM
            tim_config = {
                "notifications": True,
                "detailed_usage": True,
                "export_format": "json",
                "include_sms": False,
                "data_retention_days": 90
            }
            
            tim_access.config_json = tim_config
            db.session.commit()
            
            print(f"✅ Configurazione TIM aggiornata:")
            for key, value in tim_access.config_json.items():
                print(f"   {key}: {value}")
            
            print("\n🎉 Tutti i test completati con successo!")
            print(f"📊 Riepilogo finale:")
            print(f"   Company: {company.name}")
            print(f"   Accessi totali: {len(company.scraper_accesses.all())}")
            print(f"   Piattaforme supportate: {len(set(a.platform_type for a in company.scraper_accesses.all()))}")
            
        except Exception as e:
            print(f"❌ Errore durante i test: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
            
        return True

if __name__ == "__main__":
    print("🚀 Avvio test ScraperAccess...")
    success = test_scraper_access()
    
    if success:
        print("\n✅ Test completati con successo!")
    else:
        print("\n❌ Test falliti!")
        sys.exit(1)
