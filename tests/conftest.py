# Test Configuration

import pytest
from src.app import create_app
from src.extensions import db
from src.models.user import User


@pytest.fixture
def app():
    """Crea app Flask per testing."""
    app = create_app('testing')
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    """Client di test Flask."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Runner CLI di test."""
    return app.test_cli_runner()


@pytest.fixture
def auth_headers(client):
    """Headers di autenticazione per i test."""
    # Crea utente di test
    user_data = {
        'email': 'test@example.com',
        'username': 'testuser',
        'password': 'testpassword123'
    }
    
    # Registra utente
    response = client.post('/api/v1/auth/register', json=user_data)
    assert response.status_code == 201
    
    data = response.get_json()
    token = data['access_token']
    
    return {'Authorization': f'Bearer {token}'}


@pytest.fixture
def test_user():
    """Utente di test per i test del database."""
    user = User(
        email='test@example.com',
        username='testuser',
        first_name='Test',
        last_name='User'
    )
    user.set_password('testpassword123')
    return user
