import pytest
from app import create_app
from app.extensions import db
from app.models.inventory import Supplier, Category, Product
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
        admin = User(username="sup_admin", email="admin@sup.com", role="admin")
        admin.set_password("AdminPass123!")
        staff = User(username="sup_staff", email="staff@sup.com", role="staff")
        staff.set_password("StaffPass123!")
        db.session.add_all([admin, staff])
        db.session.commit()

        return {
            "admin": {"Authorization": f"Bearer {generate_token(admin)}"},
            "staff": {"Authorization": f"Bearer {generate_token(staff)}"}
        }

def test_supplier_crud_lifecycle(client, auth_tokens):
    """Full supplier lifecycle: Create -> List -> Update -> Delete."""
    # 1. Create Supplier (Admin required)
    payload = {
        "name": "Global Tech Wholesale",
        "contact_email": "supply@globaltech.com",
        "phone": "+1-555-888-9999",
        "address": "Chicago, IL"
    }

    # Staff rejected (403)
    assert client.post("/api/suppliers", json=payload, headers=auth_tokens["staff"]).status_code == 403

    # Admin accepted (201)
    res = client.post("/api/suppliers", json=payload, headers=auth_tokens["admin"])
    assert res.status_code == 201
    sup_id = res.get_json()["data"]["id"]

    # 2. Get Single Supplier
    get_res = client.get(f"/api/suppliers/{sup_id}")
    assert get_res.status_code == 200
    assert get_res.get_json()["data"]["name"] == "Global Tech Wholesale"
    assert get_res.get_json()["data"]["product_count"] == 0

    # 3. Patch Supplier
    patch_res = client.patch(
        f"/api/suppliers/{sup_id}",
        json={"phone": "+1-000-111-2222"},
        headers=auth_tokens["admin"]
    )
    assert patch_res.status_code == 200
    assert patch_res.get_json()["data"]["phone"] == "+1-000-111-2222"

    # 4. Delete Supplier
    del_res = client.delete(f"/api/suppliers/{sup_id}", headers=auth_tokens["admin"])
    assert del_res.status_code == 200

    # 5. Verify Not Found (404)
    assert client.get(f"/api/suppliers/{sup_id}").status_code == 404