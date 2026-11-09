import pytest
from app import create_app
from app.extensions import db
from app.models.user import User

@pytest.fixture
def client():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.session.remove()
        db.drop_all()

def test_user_password_hashing():
    """Verify passwords are salted and hashed."""
    u = User(username="testadmin", email="admin@test.com")
    u.set_password("SuperSecret123")
    assert u.password_hash != "SuperSecret123"
    assert u.check_password("SuperSecret123") is True
    assert u.check_password("WrongPassword") is False

def test_register_user_success(client):
    """POST /api/auth/register creates user and returns JWT token."""
    response = client.post("/api/auth/register", json={
        "username": "inventory_lead",
        "email": "lead@company.com",
        "password": "Password123!",
        "role": "admin"
    })
    assert response.status_code == 201
    data = response.get_json()["data"]
    assert data["user"]["username"] == "inventory_lead"
    assert data["user"]["role"] == "admin"
    assert "token" in data

def test_login_success_and_protected_me_route(client):
    """POST /api/auth/login returns token usable on /api/auth/me."""
    # 1. Register user
    client.post("/api/auth/register", json={
        "username": "sarah_manager",
        "email": "sarah@company.com",
        "password": "SecurePassword1",
        "role": "admin"
    })

    # 2. Login
    login_res = client.post("/api/auth/login", json={
        "identifier": "sarah_manager",
        "password": "SecurePassword1"
    })
    assert login_res.status_code == 200
    token = login_res.get_json()["data"]["token"]

    # 3. Call protected route without token (should fail 401)
    unauth_res = client.get("/api/auth/me")
    assert unauth_res.status_code == 401

    # 4. Call protected route with Bearer token (should succeed 200)
    auth_res = client.get("/api/auth/me", headers={
        "Authorization": f"Bearer {token}"
    })
    assert auth_res.status_code == 200
    user_data = auth_res.get_json()["data"]
    assert user_data["username"] == "sarah_manager"
    assert user_data["role"] == "admin"

def test_login_invalid_credentials_rejected(client):
    """POST /api/auth/login rejects incorrect passwords with 401."""
    client.post("/api/auth/register", json={
        "username": "tom_staff",
        "email": "tom@company.com",
        "password": "CorrectPassword"
    })
    res = client.post("/api/auth/login", json={
        "identifier": "tom_staff",
        "password": "WrongPassword"
    })
    assert res.status_code == 401
    assert res.get_json()["error"]["code"] == "INVALID_CREDENTIALS"