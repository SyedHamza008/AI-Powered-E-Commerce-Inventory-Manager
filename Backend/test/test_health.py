import pytest
from app import create_app
from app.extensions import db

@pytest.fixture
def app():
    """Create and configure a clean testing app instance."""
    app = create_app("testing")
    with app.app_context():
        # Create all tables (in memory)
        db.create_all()
        yield app
        # Drop all tables after test finishes
        db.drop_all()

@pytest.fixture
def client(app):
    """Configure test client."""
    return app.test_client()

def test_health_check_verifies_database_connectivity(client):
    """
    Given an initialized application with an in-memory database
    When GET /api/health is requested
    Then it should return 200 OK and report the database as 'connected'
    """
    response = client.get("/api/health")
    assert response.status_code == 200
    
    json_data = response.get_json()
    assert json_data["status"] == "healthy"
    assert json_data["database"] == "connected"
    assert json_data["environment"] == "testing"