import pytest
from app import app, User
from flask import url_for
import os
import shutil
import tempfile
from io import BytesIO
import pickle
import json
from passlib.hash import sha512_crypt

@pytest.fixture
def client():
    # Create a test client
    app.config['TESTING'] = True
    with app.test_client() as client:
        # Create necessary directories
        os.makedirs('db/contents', exist_ok=True)
        
        # Create test database with hashed passwords
        test_db = {
            'testuser': sha512_crypt.hash('password'),
            'otheruser': sha512_crypt.hash('password')
        }
        with open('db/db.pickle', 'wb') as f:
            pickle.dump(test_db, f)
        
        # Create test content log
        with open('db/content-log.log', 'w') as f:
            f.write('test_image.jpg???:???Wed Mar 20 10:00:00 2024???:???testuser???:???Test caption\n')
        
        # Create test image
        with open('db/contents/test_image.jpg', 'wb') as f:
            f.write(b'fake image content')
            
        yield client
        
        # Cleanup after tests
        if os.path.exists('db/contents/test_image.jpg'):
            os.remove('db/contents/test_image.jpg')
        if os.path.exists('db/content-log.log'):
            os.remove('db/content-log.log')
        if os.path.exists('db/db.pickle'):
            os.remove('db/db.pickle')
        if os.path.exists('db/contents'):
            shutil.rmtree('db/contents')
        if os.path.exists('db'):
            shutil.rmtree('db')

@pytest.fixture
def auth_headers(client):
    """Fixture to get authenticated headers"""
    response = client.post('/login', data={
        'username': 'testuser',
        'password': 'password'
    })
    return {'Authorization': f'Bearer {response.headers.get("Set-Cookie")}'}

# API Tests - Positive Cases
def test_api_get_posts_success(client, auth_headers):
    """Test successful GET /api/posts with pagination"""
    response = client.get('/api/posts')
    assert response.status_code == 200
    data = json.loads(response.data)
    
    # Verify response structure
    assert 'posts' in data
    assert 'pagination' in data
    assert '_links' in data
    assert isinstance(data['posts'], list)
    
    # Verify pagination
    pagination = data['pagination']
    assert pagination['current_page'] == 1
    assert pagination['per_page'] == 10
    assert pagination['total_items'] >= 0
    
    # Verify HATEOAS
    links = data['_links']
    assert all(key in links for key in ['self', 'first', 'last'])

def test_api_get_posts_pagination(client, auth_headers):
    """Test pagination parameters"""
    response = client.get('/api/posts?page=2&per_page=5')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['pagination']['current_page'] == 2
    assert data['pagination']['per_page'] == 5

def test_api_create_post_success(client, auth_headers):
    """Test successful post creation"""
    test_file = (BytesIO(b'test content'), 'test.jpg')
    response = client.post('/api/posts',
        data={
            'file': test_file,
            'caption': 'Test caption'
        },
        content_type='multipart/form-data',
        headers=auth_headers
    )
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['filename'] == 'test.jpg'
    assert os.path.exists('db/contents/test.jpg')

# API Tests - Negative Cases
def test_api_get_nonexistent_post(client):
    """Test getting a non-existent post"""
    response = client.get('/api/posts/nonexistent.jpg')
    assert response.status_code == 404
    data = json.loads(response.data)
    assert 'error' in data

def test_api_create_post_invalid_file(client, auth_headers):
    """Test post creation with invalid file type"""
    test_file = (BytesIO(b'test content'), 'test.txt')
    response = client.post('/api/posts',
        data={
            'file': test_file,
            'caption': 'Test caption'
        },
        content_type='multipart/form-data',
        headers=auth_headers
    )
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data

def test_api_update_nonexistent_post(client, auth_headers):
    """Test updating a non-existent post"""
    response = client.patch('/api/posts/nonexistent.jpg',
        data=json.dumps({'caption': 'New caption'}),
        content_type='application/json',
        headers=auth_headers
    )
    assert response.status_code == 404

def test_api_delete_nonexistent_post(client, auth_headers):
    """Test deleting a non-existent post"""
    response = client.delete('/api/posts/nonexistent.jpg', headers=auth_headers)
    assert response.status_code == 404

def test_api_update_post_invalid_json(client, auth_headers):
    """Test updating post with invalid JSON"""
    response = client.patch('/api/posts/test_image.jpg',
        data='invalid json',
        content_type='application/json',
        headers=auth_headers
    )
    assert response.status_code == 400

def test_api_create_post_no_file(client, auth_headers):
    """Test post creation without file"""
    response = client.post('/api/posts',
        data={'caption': 'Test caption'},
        content_type='multipart/form-data',
        headers=auth_headers
    )
    assert response.status_code == 400

# Authorization Tests
def test_api_unauthorized_access_all_endpoints(client):
    """Test all endpoints without authentication"""
    endpoints = [
        ('GET', '/api/posts'),
        ('GET', '/api/posts/test_image.jpg'),
        ('POST', '/api/posts'),
        ('PATCH', '/api/posts/test_image.jpg'),
        ('DELETE', '/api/posts/test_image.jpg')
    ]
    
    for method, endpoint in endpoints:
        response = client.open(endpoint, method=method)
        assert response.status_code in [401, 403]

def test_api_post_ownership(client, auth_headers):
    """Test post operations with non-owner user"""
    # Login as different user
    client.post('/login', data={
        'username': 'otheruser',
        'password': 'password'
    })
    
    # Try to modify another user's post
    response = client.patch('/api/posts/test_image.jpg',
        data=json.dumps({'caption': 'Unauthorized update'}),
        content_type='application/json'
    )
    assert response.status_code == 403

# Edge Cases
def test_api_malformed_requests(client, auth_headers):
    """Test handling of malformed requests"""
    # Invalid content type
    response = client.post('/api/posts',
        data='not multipart',
        content_type='text/plain',
        headers=auth_headers
    )
    assert response.status_code == 400
    
    # Missing required fields
    response = client.patch('/api/posts/test_image.jpg',
        data=json.dumps({}),
        content_type='application/json',
        headers=auth_headers
    )
    assert response.status_code == 400

if __name__ == '__main__':
    pytest.main(['-v', '--cov=app', 'test_app.py']) 