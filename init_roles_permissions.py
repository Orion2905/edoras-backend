#!/usr/bin/env python3
"""
Script per inizializzare ruoli e permessi nel database di produzione
"""

import sys
import os

# Aggiungi il percorso per gli import
sys.path.append('src')

from src.app import create_app
from src.app.extensions import db
from src.app.models.role import init_default_roles
from src.app.models.permission import init_default_permissions

def initialize_roles_and_permissions():
    """Inizializza ruoli e permessi nel database"""
    
    # Configura environment per usare Azure SQL
    os.environ['DATABASE_URL'] = "mssql+pyodbc://edorasadmin:EdorasSecure123!@edoras-sql-2025.database.windows.net/edoras-prod-database?driver=ODBC+Driver+17+for+SQL+Server"
    
    app = create_app()
    
    with app.app_context():
        print("🏰 INIZIALIZZAZIONE RUOLI E PERMESSI EDORAS")
        print("="*50)
        print(f"🔗 Database: edoras-sql-2025.database.windows.net")
        
        # Verifica connessione database
        try:
            result = db.session.execute(db.text("SELECT COUNT(*) FROM companies")).scalar()
            print(f"✅ Connesso al database - {result} aziende presenti")
        except Exception as e:
            print(f"❌ Errore connessione database: {e}")
            return
        
        # Inizializza ruoli
        print("\n📋 Inizializzazione ruoli...")
        try:
            init_default_roles()
            print("✅ Ruoli inizializzati con successo!")
        except Exception as e:
            print(f"❌ Errore inizializzazione ruoli: {e}")
            return
        
        # Inizializza permessi
        print("\n🔐 Inizializzazione permessi...")
        try:
            init_default_permissions()
            print("✅ Permessi inizializzati con successo!")
        except Exception as e:
            print(f"❌ Errore inizializzazione permessi: {e}")
            return
        
        # Verifica risultati
        from src.app.models import Role, Permission
        
        roles = Role.query.all()
        permissions = Permission.query.all()
        
        print(f"\n📊 RISULTATI:")
        print(f"   👑 Ruoli creati: {len(roles)}")
        for role in roles:
            role_perms = Permission.query.filter_by(role_id=role.id).count()
            print(f"      - {role.display_name} ({role.name}): {role_perms} permessi")
        
        print(f"   🔐 Permessi totali: {len(permissions)}")
        
        print(f"\n🌟 INIZIALIZZAZIONE COMPLETATA!")
        print("   Sistema ruoli pronto per l'uso!")

if __name__ == "__main__":
    initialize_roles_and_permissions()
