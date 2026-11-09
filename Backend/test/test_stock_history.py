import pytest
from app import create_app
from app.extensions import db
from app.models.inventory import Category, Product, StockHistory
from app.models.user import User
from app.utils.auth import generate_token

@pytest.fixture
def client_and_auth():
    """Configures clean in-memory database test client with authenticated user."""
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        # Seed test user
        user = User(username="audit_tester", email="tester@audit.com", role="staff")
        user.set_password("AuditPass123!")
        
        # Seed category & product
        cat = Category(name="Storage")
        db.session.add_all([user, cat])
        db.session.commit()

        prod = Product(
            sku="SSD-1TB-01",
            name="1TB NVMe SSD",
            unit_price=89.99,
            quantity=20,
            safety_stock_threshold=5,
            category_id=cat.id
        )
        db.session.add(prod)
        db.session.commit()

        token = generate_token(user)
        headers = {"Authorization": f"Bearer {token}"}

        yield app.test_client(), headers, prod.id
        db.session.remove()
        db.drop_all()

def test_stock_adjustment_creates_audit_record(client_and_auth):
    """Adjusting stock must create a matching StockHistory record atomically."""
    client, headers, prod_id = client_and_auth

    response = client.patch(
        f"/api/products/{prod_id}/stock", 
        json={
            "delta": -5,
            "reason": "Damaged in warehouse transit"
        }, 
        headers=headers
    )
    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["new_quantity"] == 15
    assert data["audit_id"] is not None

    history_res = client.get(f"/api/products/{prod_id}/history")
    assert history_res.status_code == 200
    history_data = history_res.get_json()["data"]
    assert history_data["pagination"]["total_count"] == 1

    entry = history_data["items"][0]
    assert entry["previous_quantity"] == 20
    assert entry["new_quantity"] == 15
    assert entry["quantity_change"] == -5
    assert entry["reason"] == "Damaged in warehouse transit"
    assert entry["user_id"] == "audit_tester"

def test_failed_stock_adjustment_creates_no_audit_record(client_and_auth):
    """If stock adjustment fails (e.g. negative stock), no audit record is written."""
    client, headers, prod_id = client_and_auth

    response = client.patch(
        f"/api/products/{prod_id}/stock", 
        json={
            "delta": -100,
            "reason": "Excessive deduction"
        }, 
        headers=headers
    )
    assert response.status_code == 409

    history_res = client.get(f"/api/products/{prod_id}/history")
    assert history_res.status_code == 200
    assert history_res.get_json()["data"]["pagination"]["total_count"] == 0

def test_multiple_adjustments_chronological_ordering(client_and_auth):
    """Multiple stock adjustments are retrieved in newest-first order."""
    client, headers, prod_id = client_and_auth

    client.patch(f"/api/products/{prod_id}/stock", json={"delta": 10, "reason": "Restock A"}, headers=headers)
    client.patch(f"/api/products/{prod_id}/stock", json={"delta": -4, "reason": "Sale B"}, headers=headers)

    history_res = client.get(f"/api/products/{prod_id}/history")
    items = history_res.get_json()["data"]["items"]
    assert len(items) == 2
    assert items[0]["reason"] == "Sale B"
    assert items[0]["previous_quantity"] == 30
    assert items[0]["new_quantity"] == 26

    assert items[1]["reason"] == "Restock A"
    assert items[1]["previous_quantity"] == 20
    assert items[1]["new_quantity"] == 30