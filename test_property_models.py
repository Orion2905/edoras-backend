#!/usr/bin/env python3
"""
Script di test per i modelli delle unità immobiliari
Testa la creazione e le relazioni tra PropertyType, POD, PropertyUnit e PropertyPod
"""

import sys
import os
from decimal import Decimal

# Aggiungi il path del backend
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from app import create_app
from app.models.property_type import PropertyType
from app.models.pod import POD, PodType
from app.models.property_unit import PropertyUnit
from app.models.property_pod import PropertyPod
from app.extensions import db

def test_property_models():
    """Test dei modelli delle unità immobiliari"""
    
    # Configura l'ambiente per usare il database di produzione con URL diretto
    os.environ['FLASK_ENV'] = 'production'
    os.environ['DATABASE_URL'] = "mssql+pyodbc://edorasadmin:EdorasSecure123!@edoras-sql-2025.database.windows.net/edoras-prod-database?driver=ODBC+Driver+17+for+SQL+Server"
    
    app = create_app('production')
    
    with app.app_context():
        print("🔄 Test dei modelli delle unità immobiliari...")
        
        # Mostra informazioni sul database
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        property_tables = [t for t in tables if t.startswith('property') or t == 'pods']
        print(f"📋 Tabelle immobiliari disponibili: {property_tables}")
        
        # 1. Crea o recupera tipi di proprietà
        print(f"\n🏠 Creazione tipi di proprietà...")
        
        villa_type = PropertyType.query.filter_by(code="VILLA").first()
        if not villa_type:
            villa_type = PropertyType(
                name="Villa",
                description="Villa unifamiliare",
                code="VILLA",
                is_active=True
            )
            db.session.add(villa_type)
            db.session.flush()
            print(f"✅ Tipo proprietà creato: {villa_type.name} (ID: {villa_type.id})")
        else:
            print(f"✅ Tipo proprietà esistente: {villa_type.name} (ID: {villa_type.id})")

        apartment_type = PropertyType.query.filter_by(code="APT").first()
        if not apartment_type:
            apartment_type = PropertyType(
                name="Appartamento",
                description="Appartamento in condominio",
                code="APT",
                is_active=True
            )
            db.session.add(apartment_type)
            db.session.flush()
            print(f"✅ Tipo proprietà creato: {apartment_type.name} (ID: {apartment_type.id})")
        else:
            print(f"✅ Tipo proprietà esistente: {apartment_type.name} (ID: {apartment_type.id})")
        
        # 2. Crea o recupera POD
        print(f"\n⚡ Creazione POD...")
        
        enel_pod = POD.query.filter_by(pod_code="IT001E12345678").first()
        if not enel_pod:
            enel_pod = POD(
                pod_code="IT001E12345678",
                pod_type=PodType.ELECTRICITY,
                supplier="Enel Energia",
                supplier_contract="EE2025001",
                description="POD elettrico principale",
                power_capacity="3.3 kW",
                voltage="220V",
                meter_serial="E123456789",
                is_active=True
            )
            db.session.add(enel_pod)
            db.session.flush()
            print(f"✅ POD creato: {enel_pod.pod_code} ({enel_pod.pod_type.value})")
        else:
            print(f"✅ POD esistente: {enel_pod.pod_code} ({enel_pod.pod_type.value})")

        gas_pod = POD.query.filter_by(pod_code="IT001G98765432").first()
        if not gas_pod:
            gas_pod = POD(
                pod_code="IT001G98765432",
                pod_type=PodType.GAS,
                supplier="Eni Gas e Luce",
                supplier_contract="EG2025001",
                description="POD gas principale",
                meter_serial="G987654321",
                is_active=True
            )
            db.session.add(gas_pod)
            db.session.flush()
            print(f"✅ POD creato: {gas_pod.pod_code} ({gas_pod.pod_type.value})")
        else:
            print(f"✅ POD esistente: {gas_pod.pod_code} ({gas_pod.pod_type.value})")
        
        # 3. Crea o recupera unità immobiliari
        print(f"\n🏡 Creazione unità immobiliari...")
        
        villa_rossi = PropertyUnit.query.filter_by(name="Villa Rossi").first()
        if not villa_rossi:
            villa_rossi = PropertyUnit(
                name="Villa Rossi",
                description="Villa unifamiliare con giardino",
                square_meters=Decimal("250.00"),
                rooms=6,
                bathrooms=3,
                floor="T",
                address="Via Roma 123",
                city="Milano",
                postal_code="20100",
                province="MI",
                property_type_id=villa_type.id,
                is_active=True,
                is_occupied=False
            )
            db.session.add(villa_rossi)
            db.session.flush()
            print(f"✅ Unità immobiliare creata: {villa_rossi.name} ({villa_rossi.square_meters}mq)")
        else:
            print(f"✅ Unità immobiliare esistente: {villa_rossi.name} ({villa_rossi.square_meters}mq)")

        apt_1a = PropertyUnit.query.filter_by(name="Appartamento 1A").first()
        if not apt_1a:
            apt_1a = PropertyUnit(
                name="Appartamento 1A",
                description="Bilocale primo piano",
                square_meters=Decimal("65.50"),
                rooms=2,
                bathrooms=1,
                floor="1",
                address="Via Verdi 45",
                city="Roma",
                postal_code="00100",
                province="RM",
                property_type_id=apartment_type.id,
                is_active=True,
                is_occupied=True
            )
            db.session.add(apt_1a)
            db.session.flush()
            print(f"✅ Unità immobiliare creata: {apt_1a.name} ({apt_1a.square_meters}mq)")
        else:
            print(f"✅ Unità immobiliare esistente: {apt_1a.name} ({apt_1a.square_meters}mq)")
        
        # 4. Crea connessioni POD (se non esistono)
        print(f"\n🔌 Creazione connessioni POD...")
        
        # Villa Rossi -> POD Elettrico
        villa_enel_connection = PropertyPod.query.filter_by(
            property_unit_id=villa_rossi.id, 
            pod_id=enel_pod.id
        ).first()
        
        if not villa_enel_connection:
            try:
                villa_enel_connection = PropertyPod.create_connection(
                    property_unit_id=villa_rossi.id,
                    pod_id=enel_pod.id,
                    is_primary=True,
                    notes="Connessione principale elettrica villa"
                )
                db.session.add(villa_enel_connection)
                db.session.flush()
                print(f"✅ Connessione creata: {villa_rossi.name} -> {enel_pod.pod_code}")
            except ValueError as e:
                print(f"⚠️ Connessione già esistente: {e}")
        else:
            print(f"✅ Connessione esistente: {villa_rossi.name} -> {enel_pod.pod_code}")

        # Villa Rossi -> POD Gas
        villa_gas_connection = PropertyPod.query.filter_by(
            property_unit_id=villa_rossi.id, 
            pod_id=gas_pod.id
        ).first()
        
        if not villa_gas_connection:
            try:
                villa_gas_connection = PropertyPod.create_connection(
                    property_unit_id=villa_rossi.id,
                    pod_id=gas_pod.id,
                    is_primary=True,
                    notes="Connessione principale gas villa"
                )
                db.session.add(villa_gas_connection)
                db.session.flush()
                print(f"✅ Connessione creata: {villa_rossi.name} -> {gas_pod.pod_code}")
            except ValueError as e:
                print(f"⚠️ Connessione già esistente: {e}")
        else:
            print(f"✅ Connessione esistente: {villa_rossi.name} -> {gas_pod.pod_code}")
        
        # Commit dei dati
        db.session.commit()
        
        # 5. Test delle relazioni e metodi
        print(f"\n🔗 Test delle relazioni:")
        
        # PropertyType -> PropertyUnits
        print(f"🏠 Tipo '{villa_type.name}' ha {villa_type.get_units_count()} unità:")
        for unit in villa_type.property_units:
            print(f"   - {unit.name} ({unit.square_meters}mq)")
        
        print(f"🏢 Tipo '{apartment_type.name}' ha {apartment_type.get_units_count()} unità:")
        for unit in apartment_type.property_units:
            print(f"   - {unit.name} ({unit.square_meters}mq)")
        
        # PropertyUnit -> POD
        print(f"\n🔌 Connessioni POD per '{villa_rossi.name}':")
        villa_pods = villa_rossi.get_connected_pods()
        for pod in villa_pods:
            print(f"   - {pod.pod_code} ({pod.pod_type.value}) - {pod.supplier}")
        
        # Test metodi specifici
        villa_enel = villa_rossi.get_electricity_pod()
        villa_gas = villa_rossi.get_gas_pod()
        
        print(f"⚡ POD Elettrico Villa: {villa_enel.pod_code if villa_enel else 'Non connesso'}")
        print(f"🔥 POD Gas Villa: {villa_gas.pod_code if villa_gas else 'Non connesso'}")
        
        # POD -> PropertyUnits
        print(f"\n🏘️ Unità connesse al POD elettrico {enel_pod.pod_code}:")
        enel_properties = enel_pod.get_connected_properties()
        for prop in enel_properties:
            print(f"   - {prop.name} ({prop.property_type.name}) - {prop.square_meters}mq")
        
        # 6. Test di business logic
        print(f"\n📊 Test di business logic:")
        
        print(f"📍 Indirizzo completo Villa: {villa_rossi.get_full_address()}")
        print(f"📍 Indirizzo completo Appartamento: {apt_1a.get_full_address()}")
        
        # Calcolo costo per mq (esempio)
        cost_per_sqm = villa_rossi.calculate_cost_per_sqm(500000)  # €500k
        print(f"💰 Costo per mq Villa (€500k): €{cost_per_sqm}/mq")
        
        # 7. Test query avanzate
        print(f"\n🔍 Query di test:")
        
        # Tutte le ville
        villas = PropertyUnit.get_by_type(villa_type.id)
        print(f"🏠 Ville nel database: {len(villas)}")
        
        # Tutte le unità a Milano
        milan_units = PropertyUnit.get_by_city("Milano")
        print(f"🏙️ Unità a Milano: {len(milan_units)}")
        
        # POD per tipologia
        electricity_pods = POD.get_electricity_pods()
        gas_pods = POD.get_gas_pods()
        print(f"⚡ POD elettrici: {len(electricity_pods)}")
        print(f"🔥 POD gas: {len(gas_pods)}")
        
        print(f"\n✅ Test completato con successo!")
        
        return {
            'property_types': [villa_type, apartment_type],
            'pods': [enel_pod, gas_pod],
            'property_units': [villa_rossi, apt_1a],
            'connections': [villa_enel_connection, villa_gas_connection]
        }

if __name__ == "__main__":
    try:
        results = test_property_models()
        print(f"\n📊 Risultati test:")
        print(f"   - Tipi proprietà: {len(results['property_types'])}")
        print(f"   - POD: {len(results['pods'])}")
        print(f"   - Unità immobiliari: {len(results['property_units'])}")
        print(f"   - Connessioni: {len([c for c in results['connections'] if c])}")
    except Exception as e:
        print(f"❌ Errore durante il test: {e}")
        import traceback
        traceback.print_exc()
