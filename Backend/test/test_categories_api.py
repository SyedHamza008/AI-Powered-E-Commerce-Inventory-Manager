import pytest
from app import create_app
from app.extensions import db
from app.models.inventory import Category, Product
from app.models.user import User
from app.utils.auth import generate_token

@pytest.fixture
def client():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.session.remove()
        db.drop_all()

@pytest.fixture
def auth_tokens(client):
    with client.application.app_context():
        admin = User(username="cat_admin", email="admin@cat.com", role="admin")
        admin.set_password("AdminPass123!")
        staff = User(username="cat_staff", email="staff@cat.com", role="staff")
        staff.set_password("StaffPass123!")
        db.session.add_all([admin, staff])
        db.session.commit()

        return {
            "admin": {"Authorization": f"Bearer {generate_token(admin)}"},
            "staff": {"Authorization": f"Bearer {generate_token(staff)}"}
        }

def test_get_categories_empty_and_populated(client, auth_tokens):
    """GET /api/categories returns empty list, then categories with product counts."""
    res = client.get("/api/categories")
    assert res.status_code == 200
    assert res.get_json()["data"] == []

    # Create category with admin token
    client.post("/api/categories", json={"name": "Audio", "description": "Microphones"}, headers=auth_tokens["admin"])

    res2 = client.get("/api/categories")
    assert res2.status_code == 200
    items = res2.get_json()["data"]
    assert len(items) == 1
    assert items[0]["name"] == "Audio"
    assert items[0]["product_count"] == 0

def test_create_category_role_permissions(client, auth_tokens):
    """POST /api/categories requires admin role."""
    payload = {"name": "Laptops"}

    # No token -> 401
    unauth = client.post("/api/categories", json=payload)
    assert unauth.status_code == 401

    # Staff token -> 403
    forbidden = client.post("/api/categories", json=payload, headers=auth_tokens["staff"])
    assert forbidden.status_code == 403

    # Admin token -> 201
    created = client.post("/api/categories", json=payload, headers=auth_tokens["admin"])
    assert created.status_code == 201
    assert created.get_json()["data"]["name"] == "Laptops"

def test_category_deletion_blocked_by_dependent_products(client, auth_tokens):
    """DELETE /api/categories/<id> returns 409 if active products reference it."""
    with client.application.app_context():
        cat = Category(name="Storage")
        db.session.add(cat)
        db.session.commit()

        prod = Product(
            sku="SSD-500GB",
            name="NVMe SSD 500GB",
            unit_price=45.0,
            quantity=10,
            safety_stock_threshold=2,
            category_id=cat.id
        )
        db.session.add(prod)
        db.session.commit()
        cat_id = cat.id

    # Attempt deletion with admin token
    del_res = client.delete(f"/api/categories/{cat_id}", headers=auth_tokens["admin"])
    assert del_res.status_code == 409
    assert del_res.get_json()["error"]["code"] == "HAS_DEPENDENT_PRODUCTS"

def test_category_deletion_succeeds_when_empty(client, auth_tokens):
    """DELETE /api/categories/<id> succeeds if no products reference it."""
    create_res = client.post("/api/categories", json={"name": "Office Supplies"}, headers=auth_tokens["admin"])
    cat_id = create_res.get_json()["data"]["id"]

    del_res = client.delete(f"/api/categories/{cat_id}", headers=auth_tokens["admin"])
    assert del_res.status_code == 200

    # Verify category is gone
    get_res = client.get(f"/api/categories/{cat_id}")
    assert get_res.status_code == 404