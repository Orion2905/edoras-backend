#!/usr/bin/env python3
"""
Script di test per i modelli delle prenotazioni
Testa la creazione e le relazioni tra Booking, PropertyUnit e POD
"""

import sys
import os
from datetime import datetime, date, timedelta

# Aggiungi il path del backend
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from app import create_app
from app.models.booking import Booking
from app.models.property_unit import PropertyUnit
from app.models.property_type import PropertyType
from app.models.pod import POD, PodType
from app.extensions import db

def test_booking_models():
    """Test dei modelli delle prenotazioni"""
    
    # Configura l'ambiente per usare il database di produzione con URL diretto
    os.environ['FLASK_ENV'] = 'production'
    os.environ['DATABASE_URL'] = "mssql+pyodbc://edorasadmin:EdorasSecure123!@edoras-sql-2025.database.windows.net/edoras-prod-database?driver=ODBC+Driver+17+for+SQL+Server"
    
    app = create_app('production')
    
    with app.app_context():
        print("🔄 Test dei modelli delle prenotazioni...")
        
        # Verifica che le tabelle esistano
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"📋 Tabelle disponibili: {len(tables)} tabelle")
        
        if 'bookings' not in tables:
            print("❌ La tabella bookings non è stata creata. Eseguire prima le migrazioni.")
            return
        
        # 1. Recupera unità immobiliari esistenti (creati nel test precedente)
        print(f"\n🏠 Recupero unità immobiliari esistenti...")
        
        villa_rossi = PropertyUnit.query.filter_by(name="Villa Rossi").first()
        apt_1a = PropertyUnit.query.filter_by(name="Appartamento 1A").first()
        
        if not villa_rossi or not apt_1a:
            print("❌ Unità immobiliari non trovate. Eseguire prima il test delle proprietà.")
            return
            
        print(f"✅ Recuperata Villa Rossi (ID: {villa_rossi.id})")
        print(f"✅ Recuperato Appartamento 1A (ID: {apt_1a.id})")
        
        # 2. Crea prenotazioni di test
        print(f"\n📅 Creazione prenotazioni...")
        
        # Prenotazione 1: Villa Rossi - Soggiorno futuro
        booking1 = Booking.query.filter_by(booking_name="BOOK-VILLA-001").first()
        if not booking1:
            booking1 = Booking(
                booking_name="BOOK-VILLA-001",
                crm_reference_id="KRS-2025-0001",
                arrival_date=date.today() + timedelta(days=7),  # Tra una settimana
                departure_date=date.today() + timedelta(days=14),  # Due settimane
                guest_count=4,
                guest_names="Mario Rossi, Giulia Rossi, Marco Rossi, Anna Rossi",
                property_unit_id=villa_rossi.id,
                notes="Famiglia con bambini, servono lettini aggiuntivi",
                booking_status="confirmed",
                is_active=True
            )
            db.session.add(booking1)
            db.session.flush()
            print(f"✅ Prenotazione creata: {booking1.booking_name} (ID: {booking1.id})")
        else:
            print(f"✅ Prenotazione esistente: {booking1.booking_name} (ID: {booking1.id})")
        
        # Prenotazione 2: Appartamento 1A - Soggiorno corrente
        booking2 = Booking.query.filter_by(booking_name="BOOK-APT-001").first()
        if not booking2:
            booking2 = Booking(
                booking_name="BOOK-APT-001",
                crm_reference_id="KRS-2025-0002",
                arrival_date=date.today() - timedelta(days=2),  # Iniziato 2 giorni fa
                departure_date=date.today() + timedelta(days=5),  # Finisce fra 5 giorni
                guest_count=2,
                guest_names="Luca Bianchi, Sara Bianchi",
                property_unit_id=apt_1a.id,
                notes="Viaggio di lavoro, check-in tardivo",
                booking_status="confirmed",
                schedine_sent_count=1,
                is_active=True
            )
            db.session.add(booking2)
            db.session.flush()
            print(f"✅ Prenotazione creata: {booking2.booking_name} (ID: {booking2.id})")
        else:
            print(f"✅ Prenotazione esistente: {booking2.booking_name} (ID: {booking2.id})")
        
        # Prenotazione 3: Villa Rossi - Soggiorno passato
        booking3 = Booking.query.filter_by(booking_name="BOOK-VILLA-002").first()
        if not booking3:
            booking3 = Booking(
                booking_name="BOOK-VILLA-002",
                crm_reference_id="KRS-2025-0003",
                arrival_date=date.today() - timedelta(days=20),  # 20 giorni fa
                departure_date=date.today() - timedelta(days=15),  # 15 giorni fa
                guest_count=6,
                guest_names="Giuseppe Verdi, Maria Verdi, Family",
                property_unit_id=villa_rossi.id,
                notes="Soggiorno completato",
                booking_status="completed",
                schedine_sent_count=2,
                alloggiati_web_sent_date=datetime.now() - timedelta(days=18),
                is_active=True
            )
            db.session.add(booking3)
            db.session.flush()
            print(f"✅ Prenotazione creata: {booking3.booking_name} (ID: {booking3.id})")
        else:
            print(f"✅ Prenotazione esistente: {booking3.booking_name} (ID: {booking3.id})")
        
        # Commit dei dati
        db.session.commit()
        
        # 3. Test dei metodi di business logic
        print(f"\n🔍 Test dei metodi di business logic:")
        
        # Durata soggiorno
        print(f"📅 Durata soggiorno Villa (booking1): {booking1.get_stay_duration()} giorni")
        print(f"📅 Durata soggiorno Appartamento (booking2): {booking2.get_stay_duration()} giorni")
        
        # Stato prenotazioni
        print(f"🟢 Booking1 è futuro: {booking1.is_future()}")
        print(f"🟡 Booking2 è corrente: {booking2.is_current()}")
        print(f"🔴 Booking3 è passato: {booking3.is_past()}")
        
        # 4. Test accesso POD tramite unità immobiliare
        print(f"\n🔌 Test accesso POD tramite prenotazioni:")
        
        # POD Villa Rossi
        villa_enel = booking1.get_enel_pod()
        villa_gas = booking1.get_gas_pod()
        print(f"⚡ Villa - POD ENEL: {villa_enel.pod_code if villa_enel else 'Non trovato'}")
        print(f"🔥 Villa - POD GAS: {villa_gas.pod_code if villa_gas else 'Non trovato'}")
        
        # POD Appartamento (non dovrebbe avere POD se non configurati)
        apt_enel = booking2.get_enel_pod()
        apt_gas = booking2.get_gas_pod()
        print(f"⚡ Appartamento - POD ENEL: {apt_enel.pod_code if apt_enel else 'Non configurato'}")
        print(f"🔥 Appartamento - POD GAS: {apt_gas.pod_code if apt_gas else 'Non configurato'}")
        
        # 5. Test gestione schedine e alloggiati web
        print(f"\n📋 Test gestione documenti:")
        
        print(f"📤 Booking1 - Schedine inviate: {booking1.schedine_sent_count}")
        print(f"📤 Booking2 - Schedine inviate: {booking2.schedine_sent_count}")
        print(f"📤 Booking3 - Schedine inviate: {booking3.schedine_sent_count}")
        
        print(f"🌐 Booking1 - Alloggiati web inviato: {booking1.is_alloggiati_web_sent()}")
        print(f"🌐 Booking2 - Alloggiati web inviato: {booking2.is_alloggiati_web_sent()}")
        print(f"🌐 Booking3 - Alloggiati web inviato: {booking3.is_alloggiati_web_sent()}")
        
        # Test invio schedina
        print(f"\\n📨 Test invio schedina per booking1...")
        old_count = booking1.schedine_sent_count
        booking1.send_schedina()
        db.session.commit()
        print(f"✅ Schedine inviate aggiornate: {old_count} -> {booking1.schedine_sent_count}")
        
        # Test invio alloggiati web
        if not booking2.is_alloggiati_web_sent():
            print(f"\\n🌐 Test invio alloggiati web per booking2...")
            booking2.mark_alloggiati_web_sent()
            db.session.commit()
            print(f"✅ Alloggiati web marcato come inviato: {booking2.alloggiati_web_sent_date}")
        
        # 6. Test query avanzate
        print(f"\n📊 Test query avanzate:")
        
        # Prenotazioni correnti
        current_bookings = Booking.get_current_bookings()
        print(f"🟡 Prenotazioni correnti: {len(current_bookings)}")
        for booking in current_bookings:
            print(f"   - {booking.booking_name} ({booking.property_unit.name})")
        
        # Prenotazioni attive
        active_bookings = Booking.get_active_bookings()
        print(f"🟢 Prenotazioni attive confermate: {len(active_bookings)}")
        
        # Prenotazioni per unità immobiliare
        villa_bookings = Booking.get_by_property_unit(villa_rossi.id)
        print(f"🏠 Prenotazioni Villa Rossi: {len(villa_bookings)}")
        
        # Prenotazioni per range di date
        start_date = date.today() - timedelta(days=30)
        end_date = date.today() + timedelta(days=30)
        range_bookings = Booking.get_by_date_range(start_date, end_date)
        print(f"📅 Prenotazioni ultimo/prossimo mese: {len(range_bookings)}")
        
        # 7. Test riassunto completo prenotazione
        print(f"\n📋 Test riassunto completo prenotazione:")
        
        summary = booking1.get_booking_summary()
        print(f"📊 Riassunto {booking1.booking_name}:")
        print(f"   - Proprietà: {summary['property_info']['unit_name']} ({summary['property_info']['unit_type']})")
        print(f"   - Date: {summary['booking_info']['arrival_date']} -> {summary['booking_info']['departure_date']}")
        print(f"   - Durata: {summary['booking_info']['duration_days']} giorni")
        print(f"   - Ospiti: {summary['booking_info']['guest_count']}")
        print(f"   - POD ENEL: {summary['pod_info']['enel_pod_code'] or 'N/A'}")
        print(f"   - POD GAS: {summary['pod_info']['gas_pod_code'] or 'N/A'}")
        
        # 8. Test validazione
        print(f"\n✅ Test validazione prenotazioni:")
        
        errors = booking1.validate_booking()
        print(f"📋 Errori validazione booking1: {len(errors)} errori")
        if errors:
            for error in errors:
                print(f"   - {error}")
        
        # Test prenotazione invalida
        invalid_booking = Booking(
            booking_name="",  # Nome vuoto
            arrival_date=date.today(),
            departure_date=date.today() - timedelta(days=1),  # Data partenza prima di arrivo
            guest_count=0,  # Nessun ospite
            property_unit_id=None  # Nessuna unità
        )
        invalid_errors = invalid_booking.validate_booking()
        print(f"❌ Errori validazione prenotazione invalida: {len(invalid_errors)} errori")
        for error in invalid_errors:
            print(f"   - {error}")
        
        print(f"\n✅ Test completato con successo!")
        
        return {
            'bookings': [booking1, booking2, booking3],
            'property_units': [villa_rossi, apt_1a],
            'current_bookings': current_bookings,
            'active_bookings': active_bookings
        }

if __name__ == "__main__":
    try:
        results = test_booking_models()
        print(f"\n📊 Risultati test:")
        print(f"   - Prenotazioni create: {len(results['bookings'])}")
        print(f"   - Unità immobiliari utilizzate: {len(results['property_units'])}")
        print(f"   - Prenotazioni correnti: {len(results['current_bookings'])}")
        print(f"   - Prenotazioni attive: {len(results['active_bookings'])}")
    except Exception as e:
        print(f"❌ Errore durante il test: {e}")
        import traceback
        traceback.print_exc()
