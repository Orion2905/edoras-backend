# Test Categories CRUD API

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from src.app.models.category import Category
from src.app.models.subcategory import Subcategory
from src.app.models.invoice import Invoice
from src.app.models.user import User
from src.app.models.role import Role
from src.app.models.company import Company
from src.app.extensions import db


class TestCategoriesAPI:
    """Test suite per Categories CRUD API"""
    
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
        
        # Crea categorie di test
        self.category1 = Category(
            name='Ufficio',
            description='Spese per ufficio',
            code='OFF',
            is_active=True
        )
        
        self.category2 = Category(
            name='Viaggio',
            description='Spese di viaggio',
            code='TRV',
            is_active=True
        )
        
        self.category3 = Category(
            name='Marketing',
            description='Spese marketing',
            code='MKT',
            is_active=False  # Inattiva
        )
        
        db.session.add_all([self.category1, self.category2, self.category3])
        db.session.commit()
    
    def get_auth_headers(self, user):
        """Ottiene headers di autenticazione per un utente."""
        from flask_jwt_extended import create_access_token
        token = create_access_token(identity=user.id)
        return {'Authorization': f'Bearer {token}'}
    
    # Test GET /categories
    def test_get_categories_rohirrim_success(self):
        """Test recupero lista categorie come Rohirrim."""
        headers = self.get_auth_headers(self.rohirrim_user)
        
        response = self.client.get('/api/v1/categories', headers=headers)
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert 'categories' in data
        assert 'pagination' in data
        assert 'user_permissions' in data
        assert len(data['categories']) == 2  # Solo quelle attive
        assert data['user_permissions']['can_edit'] == True
        assert data['user_permissions']['can_create'] == True
    
    def test_get_categories_lord_success(self):
        """Test recupero lista categorie come Lord."""
        headers = self.get_auth_headers(self.lord_user)
        
        response = self.client.get('/api/v1/categories', headers=headers)
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert 'categories' in data
        assert data['user_permissions']['can_edit'] == False
        assert data['user_permissions']['can_create'] == False
    
    def test_get_categories_dunedain_success(self):
        """Test recupero lista categorie come Dunedain."""
        headers = self.get_auth_headers(self.dunedain_user)
        
        response = self.client.get('/api/v1/categories', headers=headers)
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert 'categories' in data
        assert data['user_permissions']['can_edit'] == False
        assert data['user_permissions']['can_create'] == False
    
    def test_get_categories_with_search(self):
        """Test recupero categorie con filtro di ricerca."""
        headers = self.get_auth_headers(self.rohirrim_user)
        
        response = self.client.get('/api/v1/categories?search=ufficio', headers=headers)
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert len(data['categories']) == 1
        assert data['categories'][0]['name'] == 'Ufficio'
    
    def test_get_categories_include_inactive(self):
        """Test recupero categorie includendo quelle inattive."""
        headers = self.get_auth_headers(self.rohirrim_user)
        
        response = self.client.get('/api/v1/categories?is_active=false', headers=headers)
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert len(data['categories']) == 1
        assert data['categories'][0]['name'] == 'Marketing'
    
    def test_get_categories_pagination(self):
        """Test paginazione lista categorie."""
        headers = self.get_auth_headers(self.rohirrim_user)
        
        response = self.client.get('/api/v1/categories?page=1&per_page=1', headers=headers)
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert data['pagination']['page'] == 1
        assert data['pagination']['per_page'] == 1
        assert data['pagination']['total'] == 2
        assert len(data['categories']) == 1
    
    # Test GET /categories/<id>
    def test_get_category_success(self):
        """Test recupero singola categoria."""
        headers = self.get_auth_headers(self.rohirrim_user)
        
        response = self.client.get(f'/api/v1/categories/{self.category1.id}', headers=headers)
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert data['id'] == self.category1.id
        assert data['name'] == 'Ufficio'
        assert data['code'] == 'OFF'
        assert 'invoices_count' in data
    
    def test_get_category_not_found(self):
        """Test recupero categoria non esistente."""
        headers = self.get_auth_headers(self.rohirrim_user)
        
        response = self.client.get('/api/v1/categories/99999', headers=headers)
        
        assert response.status_code == 404
    
    # Test POST /categories
    def test_create_category_rohirrim_success(self):
        """Test creazione categoria come Rohirrim."""
        headers = self.get_auth_headers(self.rohirrim_user)
        
        category_data = {
            'name': 'Tecnologia',
            'description': 'Spese tecnologiche',
            'code': 'TECH'
        }
        
        response = self.client.post(
            '/api/v1/categories',
            json=category_data,
            headers=headers
        )
        
        assert response.status_code == 201
        data = response.get_json()
        
        assert 'message' in data
        assert 'category' in data
        assert data['category']['name'] == 'Tecnologia'
        assert data['category']['code'] == 'TECH'
        
        # Verifica in database
        category = Category.query.filter_by(name='Tecnologia').first()
        assert category is not None
        assert category.is_active == True
    
    def test_create_category_lord_forbidden(self):
        """Test creazione categoria come Lord (non autorizzato)."""
        headers = self.get_auth_headers(self.lord_user)
        
        category_data = {
            'name': 'Test Category',
            'description': 'Test description'
        }
        
        response = self.client.post(
            '/api/v1/categories',
            json=category_data,
            headers=headers
        )
        
        assert response.status_code == 403
        data = response.get_json()
        assert 'Solo i Rohirrim possono creare categorie' in data['message']
    
    def test_create_category_duplicate_name(self):
        """Test creazione categoria con nome duplicato."""
        headers = self.get_auth_headers(self.rohirrim_user)
        
        category_data = {
            'name': 'Ufficio',  # Nome già esistente
            'description': 'Altra descrizione'
        }
        
        response = self.client.post(
            '/api/v1/categories',
            json=category_data,
            headers=headers
        )
        
        assert response.status_code == 409
        data = response.get_json()
        assert 'Nome categoria già esistente' in data['error']
    
    def test_create_category_duplicate_code(self):
        """Test creazione categoria con codice duplicato."""
        headers = self.get_auth_headers(self.rohirrim_user)
        
        category_data = {
            'name': 'Altra Categoria',
            'code': 'OFF'  # Codice già esistente
        }
        
        response = self.client.post(
            '/api/v1/categories',
            json=category_data,
            headers=headers
        )
        
        assert response.status_code == 409
        data = response.get_json()
        assert 'Codice categoria già esistente' in data['error']
    
    def test_create_category_invalid_data(self):
        """Test creazione categoria con dati non validi."""
        headers = self.get_auth_headers(self.rohirrim_user)
        
        category_data = {
            'name': '',  # Nome vuoto
            'description': 'a' * 300  # Descrizione troppo lunga
        }
        
        response = self.client.post(
            '/api/v1/categories',
            json=category_data,
            headers=headers
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'Dati non validi' in data['error']
    
    # Test PUT /categories/<id>
    def test_update_category_rohirrim_success(self):
        """Test aggiornamento categoria come Rohirrim."""
        headers = self.get_auth_headers(self.rohirrim_user)
        
        update_data = {
            'description': 'Descrizione aggiornata',
            'code': 'OFF_NEW'
        }
        
        response = self.client.put(
            f'/api/v1/categories/{self.category1.id}',
            json=update_data,
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert 'message' in data
        assert data['category']['description'] == 'Descrizione aggiornata'
        assert data['category']['code'] == 'OFF_NEW'
        
        # Verifica in database
        db.session.refresh(self.category1)
        assert self.category1.description == 'Descrizione aggiornata'
    
    def test_update_category_lord_forbidden(self):
        """Test aggiornamento categoria come Lord (non autorizzato)."""
        headers = self.get_auth_headers(self.lord_user)
        
        update_data = {'description': 'Test update'}
        
        response = self.client.put(
            f'/api/v1/categories/{self.category1.id}',
            json=update_data,
            headers=headers
        )
        
        assert response.status_code == 403
    
    # Test DELETE /categories/<id>
    def test_delete_category_rohirrim_success(self):
        """Test eliminazione categoria come Rohirrim."""
        # Crea categoria senza dipendenze
        test_category = Category(
            name='Categoria da eliminare',
            description='Test',
            is_active=True
        )
        db.session.add(test_category)
        db.session.commit()
        
        headers = self.get_auth_headers(self.rohirrim_user)
        
        response = self.client.delete(
            f'/api/v1/categories/{test_category.id}',
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'eliminata con successo' in data['message']
        
        # Verifica soft delete
        db.session.refresh(test_category)
        assert test_category.is_active == False
    
    def test_delete_category_with_invoices(self):
        """Test eliminazione categoria con fatture associate."""
        # Crea fattura associata alla categoria
        invoice = Invoice(
            company_id=self.company.id,
            category_id=self.category1.id,
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
            f'/api/v1/categories/{self.category1.id}',
            headers=headers
        )
        
        assert response.status_code == 409
        data = response.get_json()
        assert 'fatture attive' in data['message']
    
    def test_delete_category_lord_forbidden(self):
        """Test eliminazione categoria come Lord (non autorizzato)."""
        headers = self.get_auth_headers(self.lord_user)
        
        response = self.client.delete(
            f'/api/v1/categories/{self.category1.id}',
            headers=headers
        )
        
        assert response.status_code == 403
    
    # Test POST /categories/check-duplicates
    def test_check_category_duplicates_success(self):
        """Test controllo duplicati categoria."""
        headers = self.get_auth_headers(self.rohirrim_user)
        
        check_data = {
            'name': 'Ufficio',
            'code': 'OFF'
        }
        
        response = self.client.post(
            '/api/v1/categories/check-duplicates',
            json=check_data,
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert 'potential_duplicates' in data
        assert 'duplicates' in data
        assert data['potential_duplicates'] > 0
    
    def test_check_category_duplicates_none_found(self):
        """Test controllo duplicati con nessun risultato."""
        headers = self.get_auth_headers(self.rohirrim_user)
        
        check_data = {
            'name': 'Categoria Unica',
            'code': 'UNIQUE'
        }
        
        response = self.client.post(
            '/api/v1/categories/check-duplicates',
            json=check_data,
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert data['potential_duplicates'] == 0
        assert len(data['duplicates']) == 0
    
    # Test POST /categories/bulk-action
    def test_bulk_action_activate_success(self):
        """Test azione bulk di attivazione."""
        headers = self.get_auth_headers(self.rohirrim_user)
        
        bulk_data = {
            'category_ids': [self.category3.id],  # Categoria inattiva
            'action': 'activate'
        }
        
        response = self.client.post(
            '/api/v1/categories/bulk-action',
            json=bulk_data,
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert 'results' in data
        assert data['results'][0]['status'] == 'activated'
        
        # Verifica in database
        db.session.refresh(self.category3)
        assert self.category3.is_active == True
    
    def test_bulk_action_lord_forbidden(self):
        """Test azione bulk come Lord (non autorizzato)."""
        headers = self.get_auth_headers(self.lord_user)
        
        bulk_data = {
            'category_ids': [self.category1.id],
            'action': 'deactivate'
        }
        
        response = self.client.post(
            '/api/v1/categories/bulk-action',
            json=bulk_data,
            headers=headers
        )
        
        assert response.status_code == 403
    
    # Test GET /categories/stats
    def test_get_categories_stats_success(self):
        """Test recupero statistiche categorie."""
        headers = self.get_auth_headers(self.rohirrim_user)
        
        response = self.client.get('/api/v1/categories/stats', headers=headers)
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert 'total_categories' in data
        assert 'active_categories' in data
        assert 'categories_with_subcategories' in data
        assert 'categories_with_invoices' in data
        assert 'user_permissions' in data
        assert data['total_categories'] == 3
        assert data['active_categories'] == 2
    
    def test_get_categories_stats_lord_access(self):
        """Test accesso alle statistiche come Lord."""
        headers = self.get_auth_headers(self.lord_user)
        
        response = self.client.get('/api/v1/categories/stats', headers=headers)
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert data['user_permissions']['can_manage'] == False
    
    # Test autorizzazioni
    def test_unauthorized_access(self):
        """Test accesso non autorizzato."""
        response = self.client.get('/api/v1/categories')
        assert response.status_code == 401
    
    def test_invalid_token(self):
        """Test con token non valido."""
        headers = {'Authorization': 'Bearer invalid_token'}
        response = self.client.get('/api/v1/categories', headers=headers)
        assert response.status_code == 422
