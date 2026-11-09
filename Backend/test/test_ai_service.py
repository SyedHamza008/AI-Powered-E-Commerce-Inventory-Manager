import pytest
from app import create_app
from app.services.ai_service import AIService, AIServiceError

@pytest.fixture
def app():
    app = create_app("testing")
    return app

def test_mock_inventory_insights_generation(app):
    """Verify that the AI service mock returns structured risk metrics."""
    with app.app_context():
        sample_facts = {
            "total_products": 20,
            "total_stock_units": 150,
            "low_stock_products": [
                {
                    "id": 1,
                    "sku": "ELEC-MOUSE-01",
                    "name": "Wireless Mouse",
                    "quantity": 2,
                    "safety_stock_threshold": 5
                }
            ]
        }

        insights = AIService.generate_inventory_insights(sample_facts)

        assert insights["risk_level"] == "HIGH"
        assert "1 item(s) below safety stock" in insights["summary"]
        assert len(insights["recommendations"]) == 1
        assert insights["recommendations"][0]["sku"] == "ELEC-MOUSE-01"
        assert insights["recommendations"][0]["urgency"] == "HIGH"
        assert insights["provider_used"] == "mock-adapter"

def test_mock_inventory_insights_healthy_stock(app):
    """Verify that healthy stock returns LOW risk level."""
    with app.app_context():
        sample_facts = {
            "total_products": 10,
            "total_stock_units": 200,
            "low_stock_products": []
        }

        insights = AIService.generate_inventory_insights(sample_facts)
        assert insights["risk_level"] == "LOW"
        assert len(insights["recommendations"]) == 0