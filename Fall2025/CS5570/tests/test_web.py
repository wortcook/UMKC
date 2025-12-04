"""
Tests for OpenGenome2 Web UI
"""

import pytest
from opengenome.web.app import app


@pytest.fixture
def client():
    """Create test client."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def test_home_page(client):
    """Test home page loads."""
    response = client.get('/')
    assert response.status_code == 200
    assert b'OpenGenome2' in response.data


def test_ingest_page(client):
    """Test ingest page loads."""
    response = client.get('/ingest')
    assert response.status_code == 200
    assert b'Data Ingestion' in response.data


def test_analyze_page(client):
    """Test analyze page loads."""
    response = client.get('/analyze')
    assert response.status_code == 200
    assert b'Sequence Analysis' in response.data


def test_results_page(client):
    """Test results page loads."""
    response = client.get('/results')
    assert response.status_code == 200
    assert b'Analysis Results' in response.data


def test_health_endpoint(client):
    """Test health check endpoint."""
    response = client.get('/api/health')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'healthy'
    assert 'timestamp' in data


def test_datasets_endpoint(client):
    """Test datasets listing endpoint."""
    response = client.get('/api/datasets')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'success'
    assert 'datasets' in data


def test_results_endpoint(client):
    """Test results listing endpoint."""
    response = client.get('/api/results')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'success'
    assert 'results' in data


def test_missing_file_upload(client):
    """Test local ingest without file."""
    response = client.post('/api/ingest/local', data={})
    assert response.status_code == 400
    data = response.get_json()
    assert data['status'] == 'error'


def test_kmer_missing_input(client):
    """Test k-mer analysis without input."""
    response = client.post('/api/analyze/kmer',
                           json={},
                           content_type='application/json')
    assert response.status_code == 400
    data = response.get_json()
    assert data['status'] == 'error'


def test_codon_missing_input(client):
    """Test codon analysis without input."""
    response = client.post('/api/analyze/codon',
                           json={},
                           content_type='application/json')
    assert response.status_code == 400
    data = response.get_json()
    assert data['status'] == 'error'
