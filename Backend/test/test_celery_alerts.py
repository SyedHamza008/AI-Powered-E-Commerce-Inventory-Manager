import pytest
from app import create_app
from app.extensions import db
from app.models.inventory import Category, Product
from app.models.user import User
from app.utils.auth import generate_token
from app.tasks.alert_tasks import check_and_alert_low_stock, _ALERT_COOLDOWN

@pytest.fixture
def client():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        _ALERT_COOLDOWN.clear()  # Reset cooldown state between tests
        yield app.test_client()
        db.session.remove()
        db.drop_all()

@pytest.fixture
def auth_headers(client):
    with client.application.app_context():
        admin = User(username="worker_admin", email="admin@worker.com", role="admin")
        admin.set_password("AdminPass123!")
        db.session.add(admin)
        db.session.commit()
        token = generate_token(admin)
        return {"Authorization": f"Bearer {token}"}

def test_celery_alert_triggers_when_stock_drops_below_threshold(client, auth_headers):
    """Adjusting stock below threshold triggers Celery low-stock alert."""
    with client.application.app_context():
        cat = Category(name="Peripherals")
        db.session.add(cat)
        db.session.commit()

        prod = Product(
            sku="PER-CABLE-01",
            name="USB-C Cable",
            unit_price=15.0,
            quantity=10,
            safety_stock_threshold=5,
            category_id=cat.id
        )
        db.session.add(prod)
        db.session.commit()
        prod_id = prod.id

    # Reduce stock from 10 to 3 (below safety threshold of 5)
    res = client.patch(
        f"/api/products/{prod_id}/stock",
        json={"delta": -7, "reason": "Customer purchases"},
        headers=auth_headers
    )
    assert res.status_code == 200
    assert res.get_json()["data"]["is_low_stock"] is True

    # Test Celery task directly in eager mode
    task_result = check_and_alert_low_stock(prod_id)
    assert task_result["status"] == "alert_dispatched"
    assert task_result["sku"] == "PER-CABLE-01"
    assert task_result["quantity"] == 3

def test_celery_alert_suppressed_by_cooldown(client):
    """Second alert within cooldown period is safely suppressed."""
    with client.application.app_context():
        cat = Category(name="Cables")
        db.session.add(cat)
        db.session.commit()

        prod = Product(
            sku="PER-HDMI-01",
            name="HDMI 2.1 Cable",
            unit_price=20.0,
            quantity=2,
            safety_stock_threshold=5,
            category_id=cat.id
        )
        db.session.add(prod)
        db.session.commit()

        # First alert fires
        first_call = check_and_alert_low_stock(prod.id)
        assert first_call["status"] == "alert_dispatched"

        # Second alert immediately after should be suppressed
        second_call = check_and_alert_low_stock(prod.id)
        assert second_call["status"] == "suppressed"