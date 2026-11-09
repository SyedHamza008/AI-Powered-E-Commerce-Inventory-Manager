import pytest
from app import create_app
from app.extensions import db
from app.models.inventory import Category, Supplier, Product, StockHistory
from app.models.user import User
from app.utils.auth import generate_token

@pytest.fixture
def app():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def auth_tokens(app):
    """Seed admin and staff users and generate valid auth headers."""
    admin = User(username="admin_user", email="admin@test.com", role="admin")
    admin.set_password("AdminPass123!")

    staff = User(username="staff_user", email="staff@test.com", role="staff")
    staff.set_password("StaffPass123!")

    db.session.add_all([admin, staff])
    db.session.commit()

    admin_token = generate_token(admin)
    staff_token = generate_token(staff)

    return {
        "admin_headers": {"Authorization": f"Bearer {admin_token}"},
        "staff_headers": {"Authorization": f"Bearer {staff_token}"}
    }

@pytest.fixture
def seed_data(app):
    cat = Category(name="Electronics")
    sup = Supplier(name="Apex Wholesale", contact_email="orders@apex.com")
    db.session.add_all([cat, sup])
    db.session.commit()

    p1 = Product(sku="ELEC-LAPTOP-01", name="Pro Laptop", unit_price=1200.0, quantity=15, safety_stock_threshold=5, category_id=cat.id)
    p2 = Product(sku="ELEC-MOUSE-01", name="Wireless Mouse", unit_price=25.0, quantity=2, safety_stock_threshold=5, category_id=cat.id)
    p1.suppliers.append(sup)
    db.session.add_all([p1, p2])
    db.session.commit()

    return {"cat_id": cat.id, "sup_id": sup.id, "p1_id": p1.id, "p2_id": p2.id}

# --- READ TESTS ---

def test_filter_products_by_category(client, seed_data):
    response = client.get(f"/api/products?category_id={seed_data['cat_id']}")
    assert response.status_code == 200
    items = response.get_json()["data"]["items"]
    assert len(items) == 2

def test_filter_products_by_low_stock(client, seed_data):
    response = client.get("/api/products?low_stock=true")
    assert response.status_code == 200
    items = response.get_json()["data"]["items"]
    assert len(items) == 1
    assert items[0]["sku"] == "ELEC-MOUSE-01"

def test_search_products_by_term(client, seed_data):
    response = client.get("/api/products?search=laptop")
    assert response.status_code == 200
    items = response.get_json()["data"]["items"]
    assert len(items) == 1
    assert items[0]["name"] == "Pro Laptop"

# --- WRITE & AUTH TESTS ---

def test_create_product_success(client, seed_data, auth_tokens):
    response = client.post("/api/products", json={
        "sku": "ELEC-KEY-01",
        "name": "RGB Keyboard",
        "unit_price": 75.50,
        "quantity": 25,
        "safety_stock_threshold": 5,
        "category_id": seed_data["cat_id"],
        "supplier_ids": [seed_data["sup_id"]]
    }, headers=auth_tokens["admin_headers"])
    assert response.status_code == 201
    data = response.get_json()["data"]
    assert data["sku"] == "ELEC-KEY-01"

def test_create_product_requires_admin_token(client, seed_data, auth_tokens):
    payload = {
        "sku": "ELEC-DISP-01",
        "name": "Display 4K",
        "unit_price": 300.0,
        "quantity": 10,
        "category_id": seed_data["cat_id"]
    }
    unauth = client.post("/api/products", json=payload)
    assert unauth.status_code == 401

    forbidden = client.post("/api/products", json=payload, headers=auth_tokens["staff_headers"])
    assert forbidden.status_code == 403

def test_adjust_stock_delta_increase_success(client, seed_data, auth_tokens):
    response = client.patch(
        f"/api/products/{seed_data['p1_id']}/stock",
        json={"delta": 10, "reason": "Shipment arrived from supplier"},
        headers=auth_tokens["staff_headers"]
    )
    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["previous_quantity"] == 15
    assert data["new_quantity"] == 25

def test_adjust_stock_delta_decrease_success(client, seed_data, auth_tokens):
    response = client.patch(
        f"/api/products/{seed_data['p1_id']}/stock",
        json={"delta": -5, "reason": "Customer purchase order #8841"},
        headers=auth_tokens["staff_headers"]
    )
    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["previous_quantity"] == 15
    assert data["new_quantity"] == 10

def test_adjust_stock_rejects_insufficient_inventory(client, seed_data, auth_tokens):
    response = client.patch(
        f"/api/products/{seed_data['p2_id']}/stock",
        json={"delta": -5, "reason": "Bulk order attempt"},
        headers=auth_tokens["staff_headers"]
    )
    assert response.status_code == 409
    data = response.get_json()
    assert data["error"]["code"] == "INSUFFICIENT_STOCK"

def test_adjust_stock_requires_reason(client, seed_data, auth_tokens):
    response = client.patch(
        f"/api/products/{seed_data['p1_id']}/stock",
        json={"delta": 5},
        headers=auth_tokens["staff_headers"]
    )
    assert response.status_code == 400

def test_adjust_stock_target_quantity_override(client, seed_data, auth_tokens):
    response = client.patch(
        f"/api/products/{seed_data['p1_id']}/stock",
        json={
            "target_quantity": 50,
            "reason": "Annual warehouse physical inventory count reconciliation"
        },
        headers=auth_tokens["staff_headers"]
    )
    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["previous_quantity"] == 15
    assert data["new_quantity"] == 50

def test_adjust_stock_records_authenticated_user(client, seed_data, auth_tokens):
    response = client.patch(
        f"/api/products/{seed_data['p1_id']}/stock",
        json={"delta": 5, "reason": "Restocked shipment"},
        headers=auth_tokens["staff_headers"]
    )
    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["user_id"] == "staff_user"

def test_delete_product_restricted_to_admin(client, seed_data, auth_tokens):
    staff_res = client.delete(f"/api/products/{seed_data['p2_id']}", headers=auth_tokens["staff_headers"])
    assert staff_res.status_code == 403

    admin_res = client.delete(f"/api/products/{seed_data['p2_id']}", headers=auth_tokens["admin_headers"])
    assert admin_res.status_code == 200