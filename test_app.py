import os
import tempfile
import pytest
from app import app, init_db

@pytest.fixture
def client():
    # Create temp DB and close file descriptor to avoid Windows lock
    db_fd, db_path = tempfile.mkstemp()
    os.close(db_fd)

    app.config['TESTING'] = True
    app.config['DATABASE'] = db_path

    with app.test_client() as client:
        with app.app_context():
            init_db()
        yield client

    os.unlink(db_path)

def test_index_redirect(client):
    """Test that index redirects to login when not logged in."""
    response = client.get('/', follow_redirects=False)
    assert response.status_code == 302
    assert '/login' in response.location

def test_login_page(client):
    """Test that login page loads correctly."""
    response = client.get('/login')
    assert response.status_code == 200
    assert b'Login' in response.data
    
def test_register_page(client):
    """Test that register page loads correctly."""
    response = client.get('/register')
    assert response.status_code == 200
    assert b'Register' in response.data

def test_valid_registration(client):
    """Test user registration with valid credentials."""
    response = client.post('/register', data={
        'username': 'testuser',
        'email': 'test@example.com',
        'phone': '1234567890',
        'password': 'testpassword'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Login' in response.data

def test_valid_login(client):
    """Test login with valid credentials."""
    # First register a user
    client.post('/register', data={
        'username': 'testuser',
        'email': 'test@example.com',
        'phone': '1234567890',
        'password': 'testpassword'
    })
    
    # Then try to log in
    response = client.post('/login', data={
        'username': 'testuser',
        'password': 'testpassword'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b'Dashboard' in response.data or b'Welcome' in response.data
