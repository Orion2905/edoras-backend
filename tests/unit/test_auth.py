# Test User Authentication

def test_user_registration(client):
    """Test user registration."""
    user_data = {
        'email': 'newuser@example.com',
        'username': 'newuser',
        'password': 'newpassword123',
        'first_name': 'New',
        'last_name': 'User'
    }
    
    response = client.post('/api/v1/auth/register', json=user_data)
    assert response.status_code == 201
    
    data = response.get_json()
    assert 'access_token' in data
    assert 'user' in data
    assert data['user']['email'] == user_data['email']
    assert data['user']['username'] == user_data['username']


def test_user_login(client):
    """Test user login."""
    # Prima registra un utente
    user_data = {
        'email': 'logintest@example.com',
        'username': 'logintest',
        'password': 'loginpassword123'
    }
    client.post('/api/v1/auth/register', json=user_data)
    
    # Poi prova il login
    login_data = {
        'email': 'logintest@example.com',
        'password': 'loginpassword123'
    }
    
    response = client.post('/api/v1/auth/login', json=login_data)
    assert response.status_code == 200
    
    data = response.get_json()
    assert 'access_token' in data
    assert 'user' in data


def test_invalid_login(client):
    """Test login with invalid credentials."""
    login_data = {
        'email': 'nonexistent@example.com',
        'password': 'wrongpassword'
    }
    
    response = client.post('/api/v1/auth/login', json=login_data)
    assert response.status_code == 401
    
    data = response.get_json()
    assert 'message' in data


def test_get_current_user(client, auth_headers):
    """Test get current user endpoint."""
    response = client.get('/api/v1/auth/me', headers=auth_headers)
    assert response.status_code == 200
    
    data = response.get_json()
    assert 'user' in data
    assert data['user']['email'] == 'test@example.com'
