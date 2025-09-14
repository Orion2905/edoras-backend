# Test Health Endpoints

def test_health_check(client):
    """Test health check endpoint."""
    response = client.get('/api/v1/health')
    assert response.status_code == 200
    
    data = response.get_json()
    assert data['status'] == 'healthy'
    assert data['service'] == 'edoras-backend'
    assert 'timestamp' in data


def test_database_health(client):
    """Test database health endpoint."""
    response = client.get('/api/v1/health/db')
    assert response.status_code == 200
    
    data = response.get_json()
    assert data['status'] == 'healthy'
    assert data['database'] == 'connected'
    assert 'timestamp' in data
