from datetime import datetime, timezone
from app.extensions import db

# Association Table for Many-to-Many relationship between Product and Supplier
product_suppliers = db.Table(
    "product_suppliers",
    db.Column("product_id", db.Integer, db.ForeignKey("products.id", ondelete="CASCADE"), primary_key=True),
    db.Column("supplier_id", db.Integer, db.ForeignKey("suppliers.id", ondelete="CASCADE"), primary_key=True),
    db.Column("created_at", db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
)


class Category(db.Model):
    """Product Category entity (One-to-Many with Product)."""
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    description = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationship to Products
    products = db.relationship("Product", back_populates="category", cascade="all, delete-orphan", lazy="select")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at.isoformat()
        }


class Supplier(db.Model):
    """Supplier entity (Many-to-Many with Product)."""
    __tablename__ = "suppliers"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), unique=True, nullable=False, index=True)
    contact_email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(30), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Many-to-Many back-reference
    products = db.relationship("Product", secondary=product_suppliers, back_populates="suppliers", lazy="select")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "contact_email": self.contact_email,
            "phone": self.phone,
            "created_at": self.created_at.isoformat()
        }


class Product(db.Model):
    """Product entity representing tracked inventory items."""
    __tablename__ = "products"

    # Enforce non-negative stock and pricing at database level
    __table_args__ = (
        db.CheckConstraint("quantity >= 0", name="check_product_quantity_non_negative"),
        db.CheckConstraint("unit_price >= 0", name="check_product_price_non_negative"),
        db.CheckConstraint("safety_stock_threshold >= 0", name="check_product_safety_threshold_non_negative"),
    )

    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(64), unique=True, nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    
    # Financial and Stock figures (use numeric/decimal for currency in real production)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)
    quantity = db.Column(db.Integer, nullable=False, default=0)
    safety_stock_threshold = db.Column(db.Integer, nullable=False, default=5)

    # Foreign Keys
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False, index=True)

    # Relationships
    category = db.relationship("Category", back_populates="products")
    suppliers = db.relationship("Supplier", secondary=product_suppliers, back_populates="products", lazy="select")

    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    @property
    def is_low_stock(self):
        """Helper property to immediately check stock warning status."""
        return self.quantity <= self.safety_stock_threshold

    def to_dict(self, include_suppliers=False):
        """Serialize model instance to a JSON-compatible dictionary."""
        data = {
            "id": self.id,
            "sku": self.sku,
            "name": self.name,
            "description": self.description,
            "unit_price": float(self.unit_price) if self.unit_price is not None else 0.0,
            "quantity": self.quantity,
            "safety_stock_threshold": self.safety_stock_threshold,
            "is_low_stock": self.is_low_stock,
            "category_id": self.category_id,
            "category_name": self.category.name if self.category else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
        if include_suppliers:
            data["suppliers"] = [s.to_dict() for s in self.suppliers]
        return data
        
class StockHistory(db.Model):
    """
    Immutable audit log tracking all inventory adjustments.
    Records who, when, why, and the exact quantity delta.
    """
    __tablename__ = "stock_history"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    previous_quantity = db.Column(db.Integer, nullable=False)
    new_quantity = db.Column(db.Integer, nullable=False)
    quantity_change = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(255), nullable=False)
    user_id = db.Column(db.String(64), nullable=True, default="system_admin")  # Ready for Phase 7 Auth
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    # Relationship to Product
    product = db.relationship("Product", backref=db.backref("stock_history", lazy="dynamic", cascade="all, delete-orphan"))

    def to_dict(self):
        return {
            "id": self.id,
            "product_id": self.product_id,
            "previous_quantity": self.previous_quantity,
            "new_quantity": self.new_quantity,
            "quantity_change": self.quantity_change,
            "reason": self.reason,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat()
        }