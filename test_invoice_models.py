#!/usr/bin/env python3
"""
Script di test per i modelli delle fatture
Testa la creazione e le relazioni tra Category, Subcategory, Minicategory e Invoice
"""

import sys
import os
from datetime import datetime, date
from decimal import Decimal

# Aggiungi il path del backend
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from app import create_app
from app.models.category import Category
from app.models.subcategory import Subcategory
from app.models.minicategory import Minicategory
from app.models.invoice import Invoice
from app.extensions import db

def test_invoice_models():
    """Test dei modelli delle fatture"""
    
    # Configura l'ambiente per usare il database di produzione con URL diretto
    os.environ['FLASK_ENV'] = 'production'
    os.environ['DATABASE_URL'] = "mssql+pyodbc://edorasadmin:EdorasSecure123!@edoras-sql-2025.database.windows.net/edoras-prod-database?driver=ODBC+Driver+17+for+SQL+Server"
    
    app = create_app('production')  # Forza la configurazione di produzione
    
    with app.app_context():
        print("🔄 Test dei modelli delle fatture...")
        
        # Mostra informazioni sul database
        db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
        if 'azure' in db_uri.lower() or 'edoras-sql' in db_uri.lower():
            print(f"📊 Database: Azure SQL Database")
        elif 'sqlite' in db_uri.lower():
            print(f"📊 Database: SQLite locale")
        else:
            print(f"📊 Database: Altri")
        
        # Verifica che le tabelle esistano
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"📋 Tabelle disponibili: {tables}")
        
        if 'categories' not in tables:
            print("❌ Le tabelle delle fatture non sono state create. Eseguire prima le migrazioni.")
            return
        
        # 1. Crea o recupera una categoria
        category = Category.query.filter_by(code="INFO").first()
        if not category:
            category = Category(
                name="Attrezzature Informatiche",
                description="Computer, periferiche e software",
                code="INFO",
                is_active=True
            )
            db.session.add(category)
            db.session.flush()  # Per ottenere l'ID
            print(f"✅ Categoria creata: {category.name} (ID: {category.id})")
        else:
            print(f"✅ Categoria esistente: {category.name} (ID: {category.id})")
        
        # 2. Crea o recupera una sottocategoria
        subcategory = Subcategory.query.filter_by(code="DESK", category_id=category.id).first()
        if not subcategory:
            subcategory = Subcategory(
                category_id=category.id,
                name="Computer Desktop",
                description="Computer desktop e workstation",
                code="DESK",
                is_active=True
            )
            db.session.add(subcategory)
            db.session.flush()
            print(f"✅ Sottocategoria creata: {subcategory.name} (ID: {subcategory.id})")
        else:
            print(f"✅ Sottocategoria esistente: {subcategory.name} (ID: {subcategory.id})")
        
        # 3. Crea o recupera una minicategoria
        minicategory = Minicategory.query.filter_by(code="GAME", subcategory_id=subcategory.id).first()
        if not minicategory:
            minicategory = Minicategory(
                subcategory_id=subcategory.id,
                name="Desktop Gaming",
                description="Computer desktop per gaming e grafica",
                code="GAME",
                is_active=True
            )
            db.session.add(minicategory)
            db.session.flush()
            print(f"✅ Minicategoria creata: {minicategory.name} (ID: {minicategory.id})")
        else:
            print(f"✅ Minicategoria esistente: {minicategory.name} (ID: {minicategory.id})")
        
        # 4. Crea o recupera una fattura
        invoice = Invoice.query.filter_by(invoice_number="FAT-2025-001").first()
        if not invoice:
            invoice = Invoice(
                supplier="TechStore SRL",
                supplier_vat="IT12345678901",
                invoice_number="FAT-2025-001",
                invoice_date=date(2025, 1, 15),
                document_type="Fattura",
                article_description="Computer Desktop Gaming - Intel i7, RTX 4070, 32GB RAM",
                article_code="DESK-GAME-001",
                unit_of_measure="Pezzo",
                quantity=Decimal("1.0000"),
                unit_price_with_vat=Decimal("2400.0000"),
                total_price_with_vat=Decimal("2400.0000"),
                unit_price_without_vat=Decimal("1967.2131"),
                total_price_without_vat=Decimal("1967.2131"),
                vat_percentage=Decimal("22.00"),
                payment_method="Bonifico bancario",
                category_id=category.id,
                subcategory_id=subcategory.id,
                minicategory_id=minicategory.id,
                notes="Computer per ufficio sviluppo software",
                allocation="Ufficio tecnico",
                is_processed=False,
                is_validated=False
            )
            db.session.add(invoice)
            # Commit dei dati
            db.session.commit()
            print(f"✅ Fattura creata: {invoice.invoice_number} (ID: {invoice.id})")
        else:
            print(f"✅ Fattura esistente: {invoice.invoice_number} (ID: {invoice.id})")
        
        # 5. Test delle relazioni
        print("\n🔗 Test delle relazioni:")
        
        # Relazione Category -> Subcategories
        print(f"📁 Categoria '{category.name}' ha {len(category.subcategories)} sottocategorie:")
        for sub in category.subcategories:
            print(f"   - {sub.name}")
        
        # Relazione Subcategory -> Minicategories
        print(f"📂 Sottocategoria '{subcategory.name}' ha {len(subcategory.minicategories)} minicategorie:")
        for mini in subcategory.minicategories:
            print(f"   - {mini.name}")
        
        # Relazione Invoice -> Categories
        print(f"📄 Fattura '{invoice.invoice_number}':")
        print(f"   - Categoria: {invoice.category.name if invoice.category else 'N/A'}")
        print(f"   - Sottocategoria: {invoice.subcategory.name if invoice.subcategory else 'N/A'}")
        print(f"   - Minicategoria: {invoice.minicategory.name if invoice.minicategory else 'N/A'}")
        
        # 6. Test metodi di business logic
        print(f"\n💰 Importi calcolati:")
        print(f"   - IVA calcolata: €{invoice.calculate_vat()}")
        print(f"   - Prezzo unitario senza IVA: €{invoice.calculate_price_without_vat()}")
        print(f"   - È in ritardo: {invoice.is_overdue()}")
        print(f"   - Categoria completa: {invoice.get_full_category_path()}")
        
        # 7. Verifica query con relazioni
        print(f"\n🔍 Query di test:")
        
        # Trova tutte le fatture per categoria
        invoices_in_category = Invoice.query.filter_by(category_id=category.id).all()
        print(f"   - Fatture nella categoria '{category.name}': {len(invoices_in_category)}")
        
        # Trova tutte le categorie attive
        active_categories = Category.query.filter_by(is_active=True).all()
        print(f"   - Categorie attive: {len(active_categories)}")
        
        print("\n✅ Test completato con successo!")
        
        return {
            'category': category,
            'subcategory': subcategory,
            'minicategory': minicategory,
            'invoice': invoice
        }

if __name__ == "__main__":
    try:
        results = test_invoice_models()
        print(f"\n📊 Risultati test:")
        for key, value in results.items():
            print(f"   - {key}: {value}")
    except Exception as e:
        print(f"❌ Errore durante il test: {e}")
        import traceback
        traceback.print_exc()
