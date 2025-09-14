#!/usr/bin/env python3
"""
Script per inizializzare e gestire le migrazioni del database
"""

import os
import sys
from dotenv import load_dotenv

# Carica le variabili ambiente
load_dotenv()

# Aggiungi src al path
sys.path.insert(0, 'src')

from app import create_app
from app.extensions import db
from flask_migrate import init, migrate, upgrade

def init_db():
    """Inizializza Flask-Migrate"""
    app = create_app('development')
    
    with app.app_context():
        print("🚀 Inizializzazione Flask-Migrate...")
        try:
            # Verifica se migrations folder esiste già
            if os.path.exists('migrations'):
                print("⚠️  La cartella migrations esiste già")
                return
            
            # Inizializza Flask-Migrate
            from flask_migrate import Migrate
            Migrate(app, db)
            
            # Crea la cartella migrations
            init()
            print("✅ Flask-Migrate inizializzato con successo!")
            
        except Exception as e:
            print(f"❌ Errore durante l'inizializzazione: {e}")

def create_migration(message="Auto migration"):
    """Crea una nuova migrazione"""
    app = create_app('development')
    
    with app.app_context():
        print(f"🔄 Creazione migrazione: {message}")
        try:
            migrate(message=message)
            print("✅ Migrazione creata con successo!")
        except Exception as e:
            print(f"❌ Errore durante la creazione migrazione: {e}")

def apply_migrations():
    """Applica le migrazioni al database"""
    app = create_app('development')
    
    with app.app_context():
        print("📊 Applicazione migrazioni al database...")
        print(f"Database: {app.config.get('SQLALCHEMY_DATABASE_URI')}")
        
        try:
            upgrade()
            print("✅ Migrazioni applicate con successo!")
            
            # Test connessione
            from sqlalchemy import text
            with db.engine.connect() as conn:
                result = conn.execute(text("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='BASE TABLE'"))
                tables = [row[0] for row in result.fetchall()]
                print(f"📋 Tabelle nel database: {tables}")
                
        except Exception as e:
            print(f"❌ Errore durante l'applicazione migrazioni: {e}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Database Migration Manager')
    parser.add_argument('command', choices=['init', 'migrate', 'upgrade'], 
                       help='Comando da eseguire')
    parser.add_argument('-m', '--message', default='Auto migration',
                       help='Messaggio per la migrazione')
    
    args = parser.parse_args()
    
    if args.command == 'init':
        init_db()
    elif args.command == 'migrate':
        create_migration(args.message)
    elif args.command == 'upgrade':
        apply_migrations()
