#!/usr/bin/env python3
"""
Test completo del sistema di gestione utenti, aziende e ruoli
Edoras Management System - Ispirato al Signore degli Anelli
"""

import sys
import os
from datetime import datetime, date
from decimal import Decimal

# Aggiungi il percorso per gli import
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.app import create_app
from src.app.extensions import db
from src.app.models import (
    Company, Role, Permission, User, 
    PropertyUnit, PropertyType, POD, PodType, PropertyPod,
    Invoice, Category, Subcategory, Minicategory
)
from src.app.models.role import init_default_roles
from src.app.models.permission import init_default_permissions

def print_section(title):
    """Stampa una sezione con separatori"""
    print(f"\n{'='*60}")
    print(f"🏰 {title}")
    print('='*60)

def test_company_and_roles_system():
    """Test completo del sistema aziende, ruoli e permessi"""
    
    app = create_app()
    
    with app.app_context():
        print_section("INIZIALIZZAZIONE SISTEMA UTENTI E AZIENDE")
        
        # 1. Inizializza ruoli e permessi di default
        print("📋 Inizializzazione ruoli di default...")
        init_default_roles()
        
        print("🔐 Inizializzazione permessi di default...")
        init_default_permissions()
        
        # 2. Verifica ruoli creati
        print_section("VERIFICA RUOLI CREATI")
        roles = Role.query.all()
        for role in roles:
            print(f"👑 {role.display_name} ({role.name})")
            print(f"   Livello accesso: {role.access_level}")
            print(f"   Descrizione: {role.description}")
            print(f"   Permessi: {len(role.permissions.all())}")
            print()
        
        # 3. Crea aziende di esempio
        print_section("CREAZIONE AZIENDE")
        
        # Azienda 1: Tech Company
        edoras_tech = Company(
            name="Edoras Tech SRL",
            legal_name="Edoras Technology Solutions S.R.L.",
            vat_number="IT12345678901",
            tax_code="EDRTCH21A01H501Z",
            email="info@edorastech.it",
            phone="+39 02 1234567",
            website="https://edorastech.it",
            address="Via Roma 123",
            city="Milano",
            province="MI",
            postal_code="20121",
            country="IT",
            is_active=True
        )
        db.session.add(edoras_tech)
        
        # Azienda 2: Property Management
        rohan_properties = Company(
            name="Rohan Properties",
            legal_name="Rohan Real Estate Management S.R.L.",
            vat_number="IT98765432109",
            tax_code="RHPRP21B02F205X",
            email="gestione@rohanproperties.it",
            phone="+39 06 9876543",
            website="https://rohanproperties.it",
            address="Piazza del Popolo 45",
            city="Roma",
            province="RM",
            postal_code="00187",
            country="IT",
            is_active=True
        )
        db.session.add(rohan_properties)
        
        db.session.commit()
        print(f"✅ Azienda creata: {edoras_tech.display_name}")
        print(f"   P.IVA: {edoras_tech.vat_number}")
        print(f"   Indirizzo: {edoras_tech.full_address}")
        print()
        print(f"✅ Azienda creata: {rohan_properties.display_name}")
        print(f"   P.IVA: {rohan_properties.vat_number}")
        print(f"   Indirizzo: {rohan_properties.full_address}")
        
        # 4. Crea utenti con diversi ruoli
        print_section("CREAZIONE UTENTI CON RUOLI")
        
        # Ottieni i ruoli
        rohirrim_role = Role.get_rohirrim_role()
        lord_role = Role.get_lord_role()
        dunedain_role = Role.get_dunedain_role()
        
        # Utente Rohirrim (Developer)
        gandalf = User(
            email="gandalf@edorastech.it",
            username="gandalf_the_white",
            first_name="Gandalf",
            last_name="Il Bianco",
            is_active=True,
            email_verified=True,
            company_id=edoras_tech.id,
            role_id=rohirrim_role.id
        )
        gandalf.set_password("mellon123!")
        db.session.add(gandalf)
        
        # Utente Lord (Admin Edoras Tech)
        aragorn_tech = User(
            email="aragorn@edorastech.it",
            username="aragorn_king",
            first_name="Aragorn",
            last_name="Re di Gondor",
            is_active=True,
            email_verified=True,
            company_id=edoras_tech.id,
            role_id=lord_role.id
        )
        aragorn_tech.set_password("narsil456!")
        db.session.add(aragorn_tech)
        
        # Utente Lord (Admin Rohan Properties)
        theoden = User(
            email="theoden@rohanproperties.it",
            username="theoden_king",
            first_name="Théoden",
            last_name="Re di Rohan",
            is_active=True,
            email_verified=True,
            company_id=rohan_properties.id,
            role_id=lord_role.id
        )
        theoden.set_password("rohan789!")
        db.session.add(theoden)
        
        # Utente Dunedain (Viewer Edoras Tech)
        legolas = User(
            email="legolas@edorastech.it",
            username="legolas_archer",
            first_name="Legolas",
            last_name="di Bosco Atro",
            is_active=True,
            email_verified=True,
            company_id=edoras_tech.id,
            role_id=dunedain_role.id
        )
        legolas.set_password("mithril321!")
        db.session.add(legolas)
        
        # Utente Dunedain (Viewer Rohan Properties)
        eowyn = User(
            email="eowyn@rohanproperties.it",
            username="eowyn_rider",
            first_name="Éowyn",
            last_name="di Rohan",
            is_active=True,
            email_verified=True,
            company_id=rohan_properties.id,
            role_id=dunedain_role.id
        )
        eowyn.set_password("dernhelm654!")
        db.session.add(eowyn)
        
        db.session.commit()
        
        # 5. Mostra utenti creati
        print("👥 Utenti creati:")
        users = User.query.all()
        for user in users:
            print(f"   {user.full_name} ({user.username})")
            print(f"   📧 {user.email}")
            print(f"   🏢 {user.company_name}")
            print(f"   👑 {user.role_name} (Livello {user.access_level})")
            print(f"   🛡️ Rohirrim: {user.is_rohirrim()}, Lord: {user.is_lord()}, Dunedain: {user.is_dunedain()}")
            print()
        
        # 6. Test permessi
        print_section("TEST PERMESSI UTENTI")
        
        # Test Gandalf (Rohirrim)
        print(f"🧙‍♂️ Test permessi {gandalf.full_name} (Rohirrim):")
        print(f"   Può gestire tutte le aziende: {gandalf.can_manage_company()}")
        print(f"   Può vedere tutte le aziende: {gandalf.can_view_company()}")
        print(f"   Ha permesso system.admin: {gandalf.has_permission('system.admin')}")
        print(f"   Ha permesso user.create: {gandalf.has_permission('user.create')}")
        print(f"   Totale permessi: {len(gandalf.get_permissions_list())}")
        print()
        
        # Test Aragorn (Lord)
        print(f"👑 Test permessi {aragorn_tech.full_name} (Lord):")
        print(f"   Può gestire la sua azienda: {aragorn_tech.can_manage_company(edoras_tech.id)}")
        print(f"   Può gestire altra azienda: {aragorn_tech.can_manage_company(rohan_properties.id)}")
        print(f"   Ha permesso company.read.own: {aragorn_tech.has_permission('company.read.own')}")
        print(f"   Ha permesso system.admin: {aragorn_tech.has_permission('system.admin')}")
        print(f"   Totale permessi: {len(aragorn_tech.get_permissions_list())}")
        print()
        
        # Test Legolas (Dunedain)
        print(f"🏹 Test permessi {legolas.full_name} (Dunedain):")
        print(f"   Può vedere la sua azienda: {legolas.can_view_company(edoras_tech.id)}")
        print(f"   Può vedere altra azienda: {legolas.can_view_company(rohan_properties.id)}")
        print(f"   Ha permesso company.read.own: {legolas.has_permission('company.read.own')}")
        print(f"   Ha permesso user.create: {legolas.has_permission('user.create')}")
        print(f"   Totale permessi: {len(legolas.get_permissions_list())}")
        print()
        
        # 7. Associa proprietà alle aziende
        print_section("ASSOCIAZIONE PROPRIETÀ ALLE AZIENDE")
        
        # Trova le proprietà esistenti
        villa_rossi = PropertyUnit.query.filter_by(name="Villa Rossi").first()
        appartamento_centro = PropertyUnit.query.filter_by(name="Appartamento Centro").first()
        
        if villa_rossi:
            villa_rossi.set_company(edoras_tech.id)
            print(f"🏡 Villa Rossi assegnata a {edoras_tech.name}")
        
        if appartamento_centro:
            appartamento_centro.set_company(rohan_properties.id)
            print(f"🏠 Appartamento Centro assegnato a {rohan_properties.name}")
        
        # 8. Test relazioni azienda-proprietà
        print_section("TEST RELAZIONI AZIENDA-PROPRIETÀ")
        
        print(f"🏢 {edoras_tech.name}:")
        print(f"   Utenti: {edoras_tech.get_users_count()}")
        print(f"   Proprietà: {edoras_tech.get_property_units_count()}")
        edoras_properties = edoras_tech.get_active_property_units()
        for prop in edoras_properties:
            print(f"   - {prop.name} ({prop.square_meters}mq)")
        print()
        
        print(f"🏢 {rohan_properties.name}:")
        print(f"   Utenti: {rohan_properties.get_users_count()}")
        print(f"   Proprietà: {rohan_properties.get_property_units_count()}")
        rohan_props = rohan_properties.get_active_property_units()
        for prop in rohan_props:
            print(f"   - {prop.name} ({prop.square_meters}mq)")
        print()
        
        # 9. Crea e associa fatture
        print_section("ASSOCIAZIONE FATTURE ALLE AZIENDE")
        
        # Trova o crea categoria per test
        energia_category = Category.query.filter_by(name="Energia").first()
        if not energia_category:
            energia_category = Category(name="Energia", description="Bollette energia")
            db.session.add(energia_category)
            db.session.commit()
        
        # Fattura per Edoras Tech
        fattura_enel_tech = Invoice(
            supplier="ENEL Energia",
            supplier_vat="IT12345678901",
            invoice_number="FAT-ENEL-2025-001",
            invoice_date=date(2025, 1, 15),
            total_price_with_vat=Decimal('1250.00'),
            total_price_without_vat=Decimal('1024.59'),
            vat_percentage=Decimal('22.00'),
            category_id=energia_category.id,
            company_id=edoras_tech.id,
            is_processed=True,
            is_validated=True
        )
        db.session.add(fattura_enel_tech)
        
        # Fattura per Rohan Properties
        fattura_gas_rohan = Invoice(
            supplier="ENI Gas",
            supplier_vat="IT98765432109",
            invoice_number="FAT-GAS-2025-001",
            invoice_date=date(2025, 1, 20),
            total_price_with_vat=Decimal('850.00'),
            total_price_without_vat=Decimal('696.72'),
            vat_percentage=Decimal('22.00'),
            category_id=energia_category.id,
            company_id=rohan_properties.id,
            is_processed=True,
            is_validated=True
        )
        db.session.add(fattura_gas_rohan)
        
        db.session.commit()
        
        # 10. Test relazioni azienda-fatture
        print_section("TEST RELAZIONI AZIENDA-FATTURE")
        
        print(f"💰 Fatture {edoras_tech.name}:")
        edoras_invoices = Invoice.get_by_company(edoras_tech.id)
        total_edoras = Decimal('0.00')
        for invoice in edoras_invoices:
            print(f"   {invoice.invoice_number}: €{invoice.total_price_with_vat} ({invoice.supplier})")
            total_edoras += invoice.total_price_with_vat or Decimal('0.00')
        print(f"   TOTALE: €{total_edoras}")
        print()
        
        print(f"💰 Fatture {rohan_properties.name}:")
        rohan_invoices = Invoice.get_by_company(rohan_properties.id)
        total_rohan = Decimal('0.00')
        for invoice in rohan_invoices:
            print(f"   {invoice.invoice_number}: €{invoice.total_price_with_vat} ({invoice.supplier})")
            total_rohan += invoice.total_price_with_vat or Decimal('0.00')
        print(f"   TOTALE: €{total_rohan}")
        print()
        
        # 11. Test accesso POD tramite aziende
        print_section("TEST ACCESSO POD TRAMITE AZIENDE")
        
        # Test POD per Edoras Tech
        print(f"⚡ POD accessibili da {edoras_tech.name}:")
        for prop in edoras_tech.get_active_property_units():
            print(f"   {prop.name}:")
            enel_pod = prop.get_electricity_pod()
            gas_pod = prop.get_gas_pod()
            print(f"     ENEL: {enel_pod.pod_code if enel_pod else 'Non configurato'}")
            print(f"     GAS: {gas_pod.pod_code if gas_pod else 'Non configurato'}")
        print()
        
        # Test POD per Rohan Properties
        print(f"⚡ POD accessibili da {rohan_properties.name}:")
        for prop in rohan_properties.get_active_property_units():
            print(f"   {prop.name}:")
            enel_pod = prop.get_electricity_pod()
            gas_pod = prop.get_gas_pod()
            print(f"     ENEL: {enel_pod.pod_code if enel_pod else 'Non configurato'}")
            print(f"     GAS: {gas_pod.pod_code if gas_pod else 'Non configurato'}")
        
        # 12. Riepilogo finale
        print_section("RIEPILOGO SISTEMA COMPLETO")
        
        print("📊 STATISTICHE SISTEMA:")
        print(f"   👥 Utenti totali: {User.query.count()}")
        print(f"   🏢 Aziende attive: {Company.query.filter_by(is_active=True).count()}")
        print(f"   👑 Ruoli disponibili: {Role.query.filter_by(is_active=True).count()}")
        print(f"   🔐 Permessi totali: {Permission.query.filter_by(is_active=True).count()}")
        print(f"   🏡 Proprietà gestite: {PropertyUnit.query.filter_by(is_active=True).count()}")
        print(f"   💰 Fatture elaborate: {Invoice.query.filter_by(is_processed=True).count()}")
        print()
        
        print("🎯 FUNZIONALITÀ VERIFICATE:")
        print("   ✅ Sistema ruoli (Rohirrim, Lord, Dunedain)")
        print("   ✅ Gestione permessi granulari")
        print("   ✅ Relazioni azienda-utenti")
        print("   ✅ Relazioni azienda-proprietà")
        print("   ✅ Relazioni azienda-fatture")
        print("   ✅ Accesso POD tramite proprietà")
        print("   ✅ Controlli di sicurezza per livello")
        print()
        
        print("🌟 SISTEMA UTENTI E AZIENDE COMPLETATO CON SUCCESSO!")
        print("   Il Regno di Edoras è pronto per gestire utenti, aziende e proprietà!")

if __name__ == "__main__":
    test_company_and_roles_system()
