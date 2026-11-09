import pytest
from app import create_app
from app.extensions import db
from app.tasks.alert_tasks import check_and_alert_low_stock, _ALERT_COOLDOWN

@pytest.fixture
def client():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        _ALERT_COOLDOWN.clear()
        yield app.test_client()
        db.session.remove()
        db.drop_all()

def test_full_application_e2e_workflow(client):
    """
    End-to-End Integration Lifecycle:
    1. Register Admin and Staff accounts
    2. Admin authenticates and retrieves JWT token
    3. Admin creates Category and Product
    4. Staff adjusts stock downwards
    5. Verify StockHistory attributes adjustment to staff user
    6. Verify Celery low-stock alert triggered
    7. Query Natural-Language Search & AI Chatbot
    """
    # 1. Register Admin
    reg_admin = client.post("/api/auth/register", json={
        "username": "lead_architect",
        "email": "architect@company.com",
        "password": "MasterPassword123!",
        "role": "admin"
    })
    assert reg_admin.status_code == 201
    admin_token = reg_admin.get_json()["data"]["token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Register Staff
    reg_staff = client.post("/api/auth/register", json={
        "username": "warehouse_staff_bob",
        "email": "bob@company.com",
        "password": "StaffPassword123!",
        "role": "staff"
    })
    assert reg_staff.status_code == 201
    staff_token = reg_staff.get_json()["data"]["token"]
    staff_headers = {"Authorization": f"Bearer {staff_token}"}

    # 2. Admin creates Category
    cat_res = client.post("/api/categories", json={
        "name": "Audio Equipment",
        "description": "Studio monitors and microphones"
    })
    assert cat_res.status_code == 201
    cat_id = cat_res.get_json()["data"]["id"]

    # 3. Staff attempts to create Product -> Must be rejected (403 Forbidden)
    prod_payload = {
        "sku": "AUD-MIC-01",
        "name": "Studio Condenser Mic",
        "unit_price": 199.99,
        "quantity": 12,
        "safety_stock_threshold": 5,
        "category_id": cat_id
    }
    forbidden_res = client.post("/api/products", json=prod_payload, headers=staff_headers)
    assert forbidden_res.status_code == 403

    # Admin creates Product -> 201 Created
    prod_res = client.post("/api/products", json=prod_payload, headers=admin_headers)
    assert prod_res.status_code == 201
    prod_id = prod_res.get_json()["data"]["id"]

    # 4. Staff adjusts stock from 12 down to 2 (below safety threshold of 5)
    stock_res = client.patch(
        f"/api/products/{prod_id}/stock",
        json={"delta": -10, "reason": "Sold to recording studio client"},
        headers=staff_headers
    )
    assert stock_res.status_code == 200
    stock_data = stock_res.get_json()["data"]
    assert stock_data["new_quantity"] == 2
    assert stock_data["is_low_stock"] is True
    assert stock_data["user_id"] == "warehouse_staff_bob"

    # 5. Verify immutable audit ledger persistence
    history_res = client.get(f"/api/products/{prod_id}/history")
    assert history_res.status_code == 200
    history_items = history_res.get_json()["data"]["items"]
    assert len(history_items) == 1
    assert history_items[0]["previous_quantity"] == 12
    assert history_items[0]["new_quantity"] == 2
    assert history_items[0]["user_id"] == "warehouse_staff_bob"

    # 6. Verify Celery low-stock detection task
    task_res = check_and_alert_low_stock(prod_id)
    assert task_res["status"] == "alert_dispatched"
    assert task_res["quantity"] == 2

    # 7. AI Natural-Language Search for low stock audio
    search_res = client.post(
        "/api/ai/search",
        json={"query": "Show audio products under 5 units in stock"},
        headers=staff_headers
    )
    assert search_res.status_code == 200
    assert search_res.get_json()["data"]["count"] == 1
    assert search_res.get_json()["data"]["items"][0]["sku"] == "AUD-MIC-01"

    # 8. AI Administrative Chatbot Inquiry
    chat_res = client.post(
        "/api/ai/chat",
        json={"messages": [{"role": "user", "content": "Show me low stock items"}]},
        headers=staff_headers
    )
    assert chat_res.status_code == 200
    assert "get_low_stock_products" in chat_res.get_json()["data"]["tools_used"]