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
def auth_headers(client):
    with client.application.app_context():
        admin = User(username="insight_admin", email="admin@insights.com", role="admin")
        admin.set_password("SecurePass123!")
        db.session.add(admin)
        db.session.commit()
        token = generate_token(admin)
        return {"Authorization": f"Bearer {token}"}

def test_get_inventory_insights_requires_auth(client):
    """GET /api/ai/insights rejects unauthenticated requests with 401."""
    res = client.get("/api/ai/insights")
    assert res.status_code == 401

def test_get_inventory_insights_calculates_and_interprets(client, auth_headers):
    """GET /api/ai/insights aggregates SQL facts and returns structured analysis."""
    with client.application.app_context():
        cat = Category(name="Electronics")
        db.session.add(cat)
        db.session.commit()

        # Add 1 healthy product and 1 low-stock product
        p1 = Product(sku="ELEC-HIGH-01", name="Item High", unit_price=10.0, quantity=50, safety_stock_threshold=5, category_id=cat.id)
        p2 = Product(sku="ELEC-LOW-01", name="Item Low", unit_price=20.0, quantity=2, safety_stock_threshold=10, category_id=cat.id)
        db.session.add_all([p1, p2])
        db.session.commit()

    res = client.get("/api/ai/insights", headers=auth_headers)
    assert res.status_code == 200
    data = res.get_json()["data"]

    # Verify deterministic factual metrics
    metrics = data["metrics"]
    assert metrics["total_products"] == 2
    assert metrics["total_units_in_stock"] == 52
    assert metrics["low_stock_count"] == 1
    assert metrics["low_stock_products"][0]["sku"] == "ELEC-LOW-01"

    # Verify AI interpretation
    analysis = data["analysis"]
    assert analysis["risk_level"] == "HIGH"
    assert len(analysis["recommendations"]) == 1
    assert analysis["recommendations"][0]["sku"] == "ELEC-LOW-01"

def test_natural_language_search_filters_category_and_stock(client, auth_headers):
    """POST /api/ai/search converts natural query to safe SQLAlchemy filters."""
    with client.application.app_context():
        cat = Category(name="Electronics")
        db.session.add(cat)
        db.session.commit()

        p1 = Product(sku="ELEC-CHEAP-01", name="Cheap Mouse", unit_price=10.0, quantity=3, safety_stock_threshold=5, category_id=cat.id)
        p2 = Product(sku="ELEC-EXP-01", name="Pro Laptop", unit_price=1200.0, quantity=25, safety_stock_threshold=5, category_id=cat.id)
        db.session.add_all([p1, p2])
        db.session.commit()

    # Query asking for electronics with fewer than 10 units
    res = client.post(
        "/api/ai/search",
        json={"query": "Show electronics with fewer than 10 in stock"},
        headers=auth_headers
    )
    assert res.status_code == 200
    data = res.get_json()["data"]

    assert data["applied_filters"]["category"] == "Electronics"
    assert data["applied_filters"]["max_stock"] == 10
    assert data["count"] == 1
    assert data["items"][0]["sku"] == "ELEC-CHEAP-01"

def test_natural_language_search_sanitizes_injection_attempts(client, auth_headers):
    """POST /api/ai/search ignores malicious injection keys."""
    from app.api.ai import validate_and_sanitize_filters

    malicious_ai_output = {
        "category": "Electronics",
        "drop_table": "products",
        "raw_sql": "SELECT * FROM users",
        "admin_override": True,
        "max_stock": 5
    }

    sanitized = validate_and_sanitize_filters(malicious_ai_output)
    assert "drop_table" not in sanitized
    assert "raw_sql" not in sanitized
    assert "admin_override" not in sanitized
    assert sanitized["category"] == "Electronics"
    assert sanitized["max_stock"] == 5
def test_tool_functions_directly(client):
    """Verify tool functions return accurate dictionary records directly."""
    from app.services.ai_tools import (
        tool_get_low_stock_products,
        tool_get_product_details,
        tool_get_category_summary
    )

    with client.application.app_context():
        cat = Category(name="Monitors")
        db.session.add(cat)
        db.session.commit()

        p = Product(
            sku="MON-4K-01",
            name="4K Monitor",
            unit_price=350.0,
            quantity=1,
            safety_stock_threshold=5,
            category_id=cat.id
        )
        db.session.add(p)
        db.session.commit()

        # Test low stock tool
        low_res = tool_get_low_stock_products(limit=5)
        assert low_res["count"] >= 1

        # Test detail tool
        detail_res = tool_get_product_details("MON-4K-01")
        assert detail_res["name"] == "4K Monitor"
        assert detail_res["quantity"] == 1

        # Test category summary
        cat_res = tool_get_category_summary()
        assert len(cat_res["categories"]) >= 1

def test_chat_endpoint_requires_auth(client):
    """POST /api/ai/chat rejects unauthenticated requests."""
    res = client.post("/api/ai/chat", json={"messages": [{"role": "user", "content": "Hello"}]})
    assert res.status_code == 401

def test_chat_endpoint_mock_workflow(client, auth_headers):
    """POST /api/ai/chat returns mock responses and logs tools used."""
    res = client.post(
        "/api/ai/chat",
        json={"messages": [{"role": "user", "content": "Show me low stock items"}]},
        headers=auth_headers
    )
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert "reply" in data
    assert "get_low_stock_products" in data["tools_used"]