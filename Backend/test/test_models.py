import pytest
from sqlalchemy.exc import IntegrityError
from app import create_app
from app.extensions import db
from app.models import Category, Supplier, Product

@pytest.fixture
def app_ctx():
    """Provides an isolated database context for each test."""
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

def test_create_category_and_product_relationship(app_ctx):
    """Verify that a category links to a product and to_dict reflects it."""
    category = Category(name="Electronics", description="Gadgets and devices")
    db.session.add(category)
    db.session.commit()

    product = Product(
        sku="ELEC-001",
        name="Noise Cancelling Headphones",
        unit_price=149.99,
        quantity=20,
        safety_stock_threshold=5,
        category_id=category.id
    )
    db.session.add(product)
    db.session.commit()

    # Verify query and relationship
    fetched_product = Product.query.filter_by(sku="ELEC-001").first()
    assert fetched_product is not None
    assert fetched_product.category.name == "Electronics"
    assert fetched_product.is_low_stock is False
    assert fetched_product.to_dict()["category_name"] == "Electronics"

def test_product_many_to_many_suppliers(app_ctx):
    """Verify linking multiple suppliers to a single product."""
    cat = Category(name="Peripherals")
    sup1 = Supplier(name="Global Logistics Corp", contact_email="sales@globallogistics.com")
    sup2 = Supplier(name="Apex Tech Supplies", contact_email="orders@apextech.com")
    db.session.add_all([cat, sup1, sup2])
    db.session.commit()

    product = Product(
        sku="PERIPH-KEY-01",
        name="Mechanical Keyboard",
        unit_price=89.50,
        quantity=15,
        category_id=cat.id
    )
    product.suppliers.extend([sup1, sup2])
    db.session.add(product)
    db.session.commit()

    saved_product = Product.query.filter_by(sku="PERIPH-KEY-01").first()
    assert len(saved_product.suppliers) == 2
    supplier_names = [s.name for s in saved_product.suppliers]
    assert "Global Logistics Corp" in supplier_names
    assert "Apex Tech Supplies" in supplier_names

def test_database_enforces_non_negative_quantity(app_ctx):
    """Verify that the database rejects attempts to save negative inventory."""
    cat = Category(name="Storage")
    db.session.add(cat)
    db.session.commit()

    invalid_product = Product(
        sku="STOR-DRIVE-01",
        name="1TB SSD",
        unit_price=79.99,
        quantity=-10,  # Violates CHECK (quantity >= 0)
        category_id=cat.id
    )
    db.session.add(invalid_product)
    
    with pytest.raises(IntegrityError):
        db.session.commit()
    
    db.session.rollback()