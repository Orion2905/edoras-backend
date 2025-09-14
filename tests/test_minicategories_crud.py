# Test Minicategories CRUD API

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from src.app.models.minicategory import Minicategory
from src.app.models.subcategory import Subcategory
from src.app.models.category import Category
from src.app.models.invoice import Invoice
from src.app.models.user import User
from src.app.models.role import Role
from src.app.models.company import Company
from src.app.extensions import db


class TestMinicategoriesAPI:
    """Test suite per Minicategories CRUD API"""
    
    @pytest.fixture(autouse=True)
    def setup_test_data(self, test_client, init_database):
        """Setup dati di test per ogni test."""
        self.client = test_client
        
        # Crea ruoli
        self.rohirrim_role = Role(name='Rohirrim', is_rohirrim=True)
        self.lord_role = Role(name='Lord', is_lord=True)
        self.dunedain_role = Role(name='Dunedain', is_dunedain=True)
        
        db.session.add_all([self.rohirrim_role, self.lord_role, self.dunedain_role])
        
        # Crea azienda
        self.company = Company(
            name='Test Company',
            vat_number='IT12345678901'
        )
        db.session.add(self.company)
        
        # Crea utenti
        self.rohirrim_user = User(
            username='rohirrim_user',
            email='rohirrim@test.com',
            password_hash='hashed_password',
            role=self.rohirrim_role,
            company=self.company,
            is_active=True
        )
        
        self.lord_user = User(
            username='lord_user',
            email='lord@test.com',
            password_hash='hashed_password',
            role=self.lord_role,
            company=self.company,
            is_active=True
        )
        
        self.dunedain_user = User(
            username='dunedain_user',
            email='dunedain@test.com',
            password_hash='hashed_password',
            role=self.dunedain_role,
            company=self.company,
            is_active=True
        )
        
        db.session.add_all([self.rohirrim_user, self.lord_user, self.dunedain_user])
        
        # Crea categoria
        self.category = Category(
            name='Ufficio',
            description='Spese per ufficio',
            code='OFF',
            is_active=True
        )
        db.session.add(self.category)
        
        # Crea sottocategorie
        self.subcategory1 = Subcategory(
            category_id=self.category.id,
            name='Cancelleria',
            description='Materiale da cancelleria',
            code='CANC',
            is_active=True
        )
        
        self.subcategory2 = Subcategory(
            category_id=self.category.id,
            name='Informatica',
            description='Materiale informatico',
            code='INFO',
            is_active=True
        )
        
        db.session.add_all([self.subcategory1, self.subcategory2])
        db.session.flush()  # Per ottenere gli ID
        
        # Crea minicategorie di test
        self.minicategory1 = Minicategory(
            subcategory_id=self.subcategory1.id,
            name='Penne',
            description='Penne e matite',
            code='PENNE',
            is_active=True
        )
        
        self.minicategory2 = Minicategory(
            subcategory_id=self.subcategory1.id,
            name='Carta',
            description='Carta e quaderni',
            code='CARTA',
            is_active=True
        )
        
        self.minicategory3 = Minicategory(
            subcategory_id=self.subcategory2.id,
            name='Computer',
            description='Computer e laptop',
            code='COMP',
            is_active=False  # Inattiva
        )
        
        db.session.add_all([self.minicategory1, self.minicategory2, self.minicategory3])
        db.session.commit()
    
    def get_auth_headers(self, user):
        """Ottiene headers di autenticazione per un utente."""
        from flask_jwt_extended import create_access_token
        token = create_access_token(identity=user.id)
        return {'Authorization': f'Bearer {token}'}
    
    # Test GET /minicategories
    def test_get_minicategories_rohirrim_success(self):
        """Test recupero lista minicategorie come Rohirrim."""
        headers = self.get_auth_headers(self.rohirrim_user)
        
        response = self.client.get('/api/v1/minicategories', headers=headers)
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert 'minicategories' in data
        assert 'pagination' in data
        assert 'user_permissions' in data
        assert len(data['minicategories']) == 2  # Solo quelle attive
        assert data['user_permissions']['can_edit'] == True
        assert data['user_permissions']['can_create'] == True
    
    def test_get_minicategories_lord_success(self):
        """Test recupero lista minicategorie come Lord."""
        headers = self.get_auth_headers(self.lord_user)
        
        response = self.client.get('/api/v1/minicategories', headers=headers)
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert 'minicategories' in data
        assert data['user_permissions']['can_edit'] == False
        assert data['user_permissions']['can_create'] == False
    
    def test_get_minicategories_with_search(self):
        """Test recupero minicategorie con filtro di ricerca."""
        headers = self.get_auth_headers(self.rohirrim_user)
        
        response = self.client.get('/api/v1/minicategories?search=penne', headers=headers)
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert len(data['minicategories']) == 1
        assert data['minicategories'][0]['name'] == 'Penne'
    
    def test_get_minicategories_by_subcategory(self):
        """Test recupero minicategorie per sottocategoria."""
        headers = self.get_auth_headers(self.rohirrim_user)
        
        response = self.client.get(f'/api/v1/minicategories?subcategory_id={self.subcategory1.id}', headers=headers)
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert len(data['minicategories']) == 2  # Penne e Carta
        for minicategory in data['minicategories']:
            assert minicategory['subcategory_id'] == self.subcategory1.id
    
    def test_get_minicategories_include_inactive(self):
        """Test recupero minicategorie includendo quelle inattive."""
        headers = self.get_auth_headers(self.rohirrim_user)
        
        response = self.client.get('/api/v1/minicategories?is_active=false', headers=headers)
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert len(data['minicategories']) == 1
        assert data['minicategories'][0]['name'] == 'Computer'
    
    # Test GET /minicategories/<id>
    def test_get_minicategory_success(self):
        """Test recupero singola minicategoria."""
        headers = self.get_auth_headers(self.rohirrim_user)
        
        response = self.client.get(f'/api/v1/minicategories/{self.minicategory1.id}', headers=headers)
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert data['id'] == self.minicategory1.id
        assert data['name'] == 'Penne'
        assert data['code'] == 'PENNE'
        assert 'invoices_count' in data
    
    def test_get_minicategory_not_found(self):
        """Test recupero minicategoria non esistente."""
        headers = self.get_auth_headers(self.rohirrim_user)
        
        response = self.client.get('/api/v1/minicategories/99999', headers=headers)
        
        assert response.status_code == 404
    
    # Test GET /minicategories/by-subcategory
    def test_get_minicategories_by_subcategory_endpoint(self):
        """Test endpoint specifico per minicategorie per sottocategoria."""
        headers = self.get_auth_headers(self.rohirrim_user)
        
        response = self.client.get(f'/api/v1/minicategories/by-subcategory?subcategory_id={self.subcategory1.id}', headers=headers)
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert 'subcategory' in data
        assert 'minicategories' in data
        assert 'total' in data
        assert data['subcategory']['id'] == self.subcategory1.id
        assert data['total'] == 2
    
    # Test POST /minicategories
    def test_create_minicategory_rohirrim_success(self):
        """Test creazione minicategoria come Rohirrim."""
        headers = self.get_auth_headers(self.rohirrim_user)
        
        minicategory_data = {
            'subcategory_id': self.subcategory1.id,
            'name': 'Gomme',
            'description': 'Gomme da cancellare',
            'code': 'GOMME'
        }
        
        response = self.client.post(
            '/api/v1/minicategories',
            json=minicategory_data,
            headers=headers
        )
        
        assert response.status_code == 201
        data = response.get_json()
        
        assert 'message' in data
        assert 'minicategory' in data
        assert data['minicategory']['name'] == 'Gomme'
        assert data['minicategory']['code'] == 'GOMME'
        
        # Verifica in database
        minicategory = Minicategory.query.filter_by(name='Gomme').first()
        assert minicategory is not None
        assert minicategory.is_active == True
    
    def test_create_minicategory_lord_forbidden(self):
        """Test creazione minicategoria come Lord (non autorizzato)."""
        headers = self.get_auth_headers(self.lord_user)
        
        minicategory_data = {
            'subcategory_id': self.subcategory1.id,
            'name': 'Test Minicategory',
            'description': 'Test description'
        }
        
        response = self.client.post(
            '/api/v1/minicategories',
            json=minicategory_data,
            headers=headers
        )
        
        assert response.status_code == 403
        data = response.get_json()
        assert 'Solo i Rohirrim possono creare minicategorie' in data['message']
    
    def test_create_minicategory_duplicate_name_same_subcategory(self):
        """Test creazione minicategoria con nome duplicato nella stessa sottocategoria."""
        headers = self.get_auth_headers(self.rohirrim_user)
        
        minicategory_data = {
            'subcategory_id': self.subcategory1.id,
            'name': 'Penne',  # Nome già esistente nella stessa sottocategoria
            'description': 'Altra descrizione'
        }
        
        response = self.client.post(
            '/api/v1/minicategories',
            json=minicategory_data,
            headers=headers
        )
        
        assert response.status_code == 409
        data = response.get_json()
        assert 'Nome minicategoria già esistente' in data['error']
    
    def test_create_minicategory_same_name_different_subcategory(self):
        """Test creazione minicategoria con stesso nome in sottocategoria diversa (permesso)."""
        headers = self.get_auth_headers(self.rohirrim_user)
        
        minicategory_data = {
            'subcategory_id': self.subcategory2.id,  # Sottocategoria diversa
            'name': 'Penne',  # Nome esistente ma in sottocategoria diversa
            'description': 'Penne per informatica'
        }
        
        response = self.client.post(
            '/api/v1/minicategories',
            json=minicategory_data,
            headers=headers
        )
        
        assert response.status_code == 201
        data = response.get_json()
        assert data['minicategory']['name'] == 'Penne'
        assert data['minicategory']['subcategory_id'] == self.subcategory2.id
    
    def test_create_minicategory_duplicate_code(self):
        """Test creazione minicategoria con codice duplicato."""
        headers = self.get_auth_headers(self.rohirrim_user)
        
        minicategory_data = {
            'subcategory_id': self.subcategory2.id,
            'name': 'Altra Minicategoria',
            'code': 'PENNE'  # Codice già esistente
        }
        
        response = self.client.post(
            '/api/v1/minicategories',
            json=minicategory_data,
            headers=headers
        )
        
        assert response.status_code == 409
        data = response.get_json()
        assert 'Codice minicategoria già esistente' in data['error']
    
    def test_create_minicategory_invalid_subcategory(self):
        """Test creazione minicategoria con sottocategoria non esistente."""
        headers = self.get_auth_headers(self.rohirrim_user)
        
        minicategory_data = {
            'subcategory_id': 99999,  # ID non esistente
            'name': 'Test Minicategory'
        }
        
        response = self.client.post(
            '/api/v1/minicategories',
            json=minicategory_data,
            headers=headers
        )
        
        assert response.status_code == 404
        data = response.get_json()
        assert 'Sottocategoria non trovata' in data['error']
    
    # Test PUT /minicategories/<id>
    def test_update_minicategory_rohirrim_success(self):
        """Test aggiornamento minicategoria come Rohirrim."""
        headers = self.get_auth_headers(self.rohirrim_user)
        
        update_data = {
            'description': 'Descrizione aggiornata',
            'code': 'PENNE_NEW'
        }
        
        response = self.client.put(
            f'/api/v1/minicategories/{self.minicategory1.id}',
            json=update_data,
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert 'message' in data
        assert data['minicategory']['description'] == 'Descrizione aggiornata'
        assert data['minicategory']['code'] == 'PENNE_NEW'
        
        # Verifica in database
        db.session.refresh(self.minicategory1)
        assert self.minicategory1.description == 'Descrizione aggiornata'
    
    def test_update_minicategory_move_to_different_subcategory(self):
        """Test spostamento minicategoria in sottocategoria diversa."""
        headers = self.get_auth_headers(self.rohirrim_user)
        
        update_data = {
            'subcategory_id': self.subcategory2.id
        }
        
        response = self.client.put(
            f'/api/v1/minicategories/{self.minicategory1.id}',
            json=update_data,
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert data['minicategory']['subcategory_id'] == self.subcategory2.id
        
        # Verifica in database
        db.session.refresh(self.minicategory1)
        assert self.minicategory1.subcategory_id == self.subcategory2.id
    
    def test_update_minicategory_lord_forbidden(self):
        """Test aggiornamento minicategoria come Lord (non autorizzato)."""
        headers = self.get_auth_headers(self.lord_user)
        
        update_data = {'description': 'Test update'}
        
        response = self.client.put(
            f'/api/v1/minicategories/{self.minicategory1.id}',
            json=update_data,
            headers=headers
        )
        
        assert response.status_code == 403
    
    # Test DELETE /minicategories/<id>
    def test_delete_minicategory_rohirrim_success(self):
        """Test eliminazione minicategoria come Rohirrim."""
        # Crea minicategoria senza dipendenze
        test_minicategory = Minicategory(
            subcategory_id=self.subcategory1.id,
            name='Minicategoria da eliminare',
            description='Test',
            is_active=True
        )
        db.session.add(test_minicategory)
        db.session.commit()
        
        headers = self.get_auth_headers(self.rohirrim_user)
        
        response = self.client.delete(
            f'/api/v1/minicategories/{test_minicategory.id}',
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'eliminata con successo' in data['message']
        
        # Verifica soft delete
        db.session.refresh(test_minicategory)
        assert test_minicategory.is_active == False
    
    def test_delete_minicategory_with_invoices(self):
        """Test eliminazione minicategoria con fatture associate."""
        # Crea fattura associata alla minicategoria
        invoice = Invoice(
            company_id=self.company.id,
            minicategory_id=self.minicategory1.id,
            supplier='Test Supplier',
            invoice_number='TEST001',
            invoice_date=datetime.now().date(),
            total_price_with_vat=Decimal('100.00'),
            is_active=True
        )
        db.session.add(invoice)
        db.session.commit()
        
        headers = self.get_auth_headers(self.rohirrim_user)
        
        response = self.client.delete(
            f'/api/v1/minicategories/{self.minicategory1.id}',
            headers=headers
        )
        
        assert response.status_code == 409
        data = response.get_json()
        assert 'fatture attive' in data['message']
    
    def test_delete_minicategory_lord_forbidden(self):
        """Test eliminazione minicategoria come Lord (non autorizzato)."""
        headers = self.get_auth_headers(self.lord_user)
        
        response = self.client.delete(
            f'/api/v1/minicategories/{self.minicategory1.id}',
            headers=headers
        )
        
        assert response.status_code == 403
    
    # Test POST /minicategories/check-duplicates
    def test_check_minicategory_duplicates_success(self):
        """Test controllo duplicati minicategoria."""
        headers = self.get_auth_headers(self.rohirrim_user)
        
        check_data = {
            'name': 'Penne',
            'subcategory_id': self.subcategory1.id,
            'code': 'PENNE'
        }
        
        response = self.client.post(
            '/api/v1/minicategories/check-duplicates',
            json=check_data,
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert 'potential_duplicates' in data
        assert 'duplicates' in data
        assert data['potential_duplicates'] > 0
    
    def test_check_minicategory_duplicates_none_found(self):
        """Test controllo duplicati con nessun risultato."""
        headers = self.get_auth_headers(self.rohirrim_user)
        
        check_data = {
            'name': 'Minicategoria Unica',
            'subcategory_id': self.subcategory1.id,
            'code': 'UNIQUE'
        }
        
        response = self.client.post(
            '/api/v1/minicategories/check-duplicates',
            json=check_data,
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert data['potential_duplicates'] == 0
        assert len(data['duplicates']) == 0
    
    # Test POST /minicategories/bulk-action
    def test_bulk_action_activate_success(self):
        """Test azione bulk di attivazione."""
        headers = self.get_auth_headers(self.rohirrim_user)
        
        bulk_data = {
            'minicategory_ids': [self.minicategory3.id],  # Minicategoria inattiva
            'action': 'activate'
        }
        
        response = self.client.post(
            '/api/v1/minicategories/bulk-action',
            json=bulk_data,
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert 'results' in data
        assert data['results'][0]['status'] == 'activated'
        
        # Verifica in database
        db.session.refresh(self.minicategory3)
        assert self.minicategory3.is_active == True
    
    def test_bulk_action_move_to_subcategory(self):
        """Test azione bulk di spostamento a sottocategoria diversa."""
        headers = self.get_auth_headers(self.rohirrim_user)
        
        bulk_data = {
            'minicategory_ids': [self.minicategory1.id],
            'action': 'move_to_subcategory',
            'target_subcategory_id': self.subcategory2.id
        }
        
        response = self.client.post(
            '/api/v1/minicategories/bulk-action',
            json=bulk_data,
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert 'results' in data
        assert data['results'][0]['status'] == 'moved'
        
        # Verifica in database
        db.session.refresh(self.minicategory1)
        assert self.minicategory1.subcategory_id == self.subcategory2.id
    
    def test_bulk_action_lord_forbidden(self):
        """Test azione bulk come Lord (non autorizzato)."""
        headers = self.get_auth_headers(self.lord_user)
        
        bulk_data = {
            'minicategory_ids': [self.minicategory1.id],
            'action': 'deactivate'
        }
        
        response = self.client.post(
            '/api/v1/minicategories/bulk-action',
            json=bulk_data,
            headers=headers
        )
        
        assert response.status_code == 403
    
    # Test GET /minicategories/stats
    def test_get_minicategories_stats_success(self):
        """Test recupero statistiche minicategorie."""
        headers = self.get_auth_headers(self.rohirrim_user)
        
        response = self.client.get('/api/v1/minicategories/stats', headers=headers)
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert 'total_minicategories' in data
        assert 'active_minicategories' in data
        assert 'minicategories_with_invoices' in data
        assert 'by_subcategory' in data
        assert 'by_category' in data
        assert 'user_permissions' in data
        assert data['total_minicategories'] == 3
        assert data['active_minicategories'] == 2
    
    def test_get_minicategories_stats_lord_access(self):
        """Test accesso alle statistiche come Lord."""
        headers = self.get_auth_headers(self.lord_user)
        
        response = self.client.get('/api/v1/minicategories/stats', headers=headers)
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert data['user_permissions']['can_manage'] == False
    
    # Test autorizzazioni
    def test_unauthorized_access(self):
        """Test accesso non autorizzato."""
        response = self.client.get('/api/v1/minicategories')
        assert response.status_code == 401
    
    def test_invalid_token(self):
        """Test con token non valido."""
        headers = {'Authorization': 'Bearer invalid_token'}
        response = self.client.get('/api/v1/minicategories', headers=headers)
        assert response.status_code == 422
