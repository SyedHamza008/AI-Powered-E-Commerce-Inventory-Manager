from flask import Blueprint, request, g
from sqlalchemy.orm import joinedload
from sqlalchemy import or_
from app.extensions import db
from app.models.inventory import Product, Category, Supplier, StockHistory
from app.utils.responses import api_response, api_error
from app.utils.auth import token_required, roles_required
from app.tasks.alert_tasks import check_and_alert_low_stock

products_bp = Blueprint("products", __name__, url_prefix="/api/products")

@products_bp.route("", methods=["GET"])
def get_products():
    """
    List products with multi-criteria filtering and pagination.
    Query params supported:
      - search: string (matches SKU or Name)
      - category_id: int
      - low_stock: boolean ('true' or '1')
      - min_stock: int
      - max_stock: int
      - page: int (default 1)
      - limit: int (default 20, max 100)
    """
    # 1. Base query with eager loading for Category to avoid N+1 queries
    query = Product.query.options(joinedload(Product.category))

    # 2. Search filter (SKU or Name)
    search = request.args.get("search", "").strip()
    if search:
        query = query.filter(
            or_(
                Product.name.ilike(f"%{search}%"),
                Product.sku.ilike(f"%{search}%")
            )
        )

    # 3. Category filter
    category_id = request.args.get("category_id", type=int)
    if category_id:
        query = query.filter(Product.category_id == category_id)

    # 4. Low stock filter
    low_stock = request.args.get("low_stock", "").lower() in ["true", "1"]
    if low_stock:
        query = query.filter(Product.quantity <= Product.safety_stock_threshold)

    # 5. Min / Max stock range
    min_stock = request.args.get("min_stock", type=int)
    if min_stock is not None:
        query = query.filter(Product.quantity >= min_stock)

    max_stock = request.args.get("max_stock", type=int)
    if max_stock is not None:
        query = query.filter(Product.quantity <= max_stock)

    # 6. Pagination with safety bounds
    page = max(request.args.get("page", 1, type=int), 1)
    limit = min(max(request.args.get("limit", 20, type=int), 1), 100)

    total_count = query.count()
    products = query.order_by(Product.name.asc()).offset((page - 1) * limit).limit(limit).all()

    total_pages = (total_count + limit - 1) // limit if total_count > 0 else 1

    return api_response(data={
        "items": [p.to_dict() for p in products],
        "pagination": {
            "page": page,
            "limit": limit,
            "total_count": total_count,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
    })

@products_bp.route("/<int:product_id>", methods=["GET"])
def get_product(product_id):
    """Retrieve single product details including assigned suppliers."""
    product = Product.query.options(
        joinedload(Product.category),
        joinedload(Product.suppliers)
    ).filter_by(id=product_id).first()

    if not product:
        return api_error("Product not found", error_code="NOT_FOUND", status_code=404)

    return api_response(data=product.to_dict(include_suppliers=True))


#Protected routes for product management (create, update, delete) require admin roless
@products_bp.route("", methods=["POST"])
@token_required
@roles_required("admin")
def create_product():
    """Create a new product with optional supplier linking."""
    body = request.get_json(silent=True)
    if not body:
        return api_error("Invalid or missing JSON payload", status_code=400)

    # Validate required fields
    required = ["sku", "name", "category_id"]
    for field in required:
        if field not in body:
            return api_error(f"Field '{field}' is required", status_code=400)

    sku = str(body["sku"]).strip().upper()
    name = str(body["name"]).strip()
    category_id = body["category_id"]

    if not sku:
        return api_error("Field 'sku' cannot be empty", status_code=400)
    if not name:
        return api_error("Field 'name' cannot be empty", status_code=400)

    # Verify category exists
    if not db.session.get(Category, category_id):
        return api_error(f"Category with id {category_id} does not exist", error_code="INVALID_CATEGORY", status_code=400)

    # Verify SKU uniqueness
    if Product.query.filter_by(sku=sku).first():
        return api_error(f"Product with SKU '{sku}' already exists", error_code="DUPLICATE_SKU", status_code=409)

    # Validate numbers
    try:
        unit_price = float(body.get("unit_price", 0.0))
        quantity = int(body.get("quantity", 0))
        safety_stock = int(body.get("safety_stock_threshold", 5))
        if unit_price < 0 or quantity < 0 or safety_stock < 0:
            return api_error("Price, quantity, and safety threshold must be non-negative", status_code=400)
    except (ValueError, TypeError):
        return api_error("Numeric fields must contain valid numbers", status_code=400)

    product = Product(
        sku=sku,
        name=name,
        description=body.get("description", ""),
        unit_price=unit_price,
        quantity=quantity,
        safety_stock_threshold=safety_stock,
        category_id=category_id
    )

    # Associate suppliers if supplied
    supplier_ids = body.get("supplier_ids", [])
    if supplier_ids:
        suppliers = Supplier.query.filter(Supplier.id.in_(supplier_ids)).all()
        product.suppliers.extend(suppliers)

    db.session.add(product)
    db.session.commit()

    return api_response(data=product.to_dict(include_suppliers=True), message="Product created successfully", status_code=201)

@products_bp.route("/<int:product_id>", methods=["PATCH"])
@token_required
@roles_required("admin", "staff")
def update_product(product_id):
    """Partially update product details."""
    product = db.session.get(Product, product_id)
    if not product:
        return api_error("Product not found", error_code="NOT_FOUND", status_code=404)

    body = request.get_json(silent=True)
    if not body:
        return api_error("Invalid or missing JSON payload", status_code=400)

    if "name" in body:
        name = str(body["name"]).strip()
        if not name:
            return api_error("Field 'name' cannot be empty", status_code=400)
        product.name = name

    if "description" in body:
        product.description = body["description"]

    if "unit_price" in body:
        try:
            price = float(body["unit_price"])
            if price < 0:
                return api_error("Price must be non-negative", status_code=400)
            product.unit_price = price
        except (ValueError, TypeError):
            return api_error("Invalid unit_price value", status_code=400)

    if "safety_stock_threshold" in body:
        try:
            threshold = int(body["safety_stock_threshold"])
            if threshold < 0:
                return api_error("Safety stock threshold must be non-negative", status_code=400)
            product.safety_stock_threshold = threshold
        except (ValueError, TypeError):
            return api_error("Invalid safety_stock_threshold value", status_code=400)

    if "category_id" in body:
        cat_id = body["category_id"]
        if not db.session.get(Category, cat_id):
            return api_error(f"Category with id {cat_id} does not exist", status_code=400)
        product.category_id = cat_id

    if "supplier_ids" in body:
        supplier_ids = body["supplier_ids"]
        suppliers = Supplier.query.filter(Supplier.id.in_(supplier_ids)).all()
        product.suppliers = suppliers

    db.session.commit()
    return api_response(data=product.to_dict(include_suppliers=True), message="Product updated successfully")


# Add db.text or with_for_update to handle pessimistic locking
@products_bp.route("/<int:product_id>/stock", methods=["PATCH"])
@token_required
@roles_required("admin", "staff")
def adjust_product_stock(product_id):
    """
    Safely adjust inventory with concurrency control and attribute the
    audit entry directly to the authenticated user.
    """
    body = request.get_json(silent=True)
    if not body:
        return api_error("Invalid or missing JSON payload", status_code=400)

    reason = body.get("reason")
    if not reason or not isinstance(reason, str) or not reason.strip():
        return api_error("A descriptive 'reason' is required for stock adjustments", status_code=400)
    reason = reason.strip()

    has_delta = "delta" in body
    has_target = "target_quantity" in body

    if not has_delta and not has_target:
        return api_error("Must provide either 'delta' or 'target_quantity'", status_code=400)
    if has_delta and has_target:
        return api_error("Cannot provide both 'delta' and 'target_quantity'", status_code=400)

    try:
        # Build query - use FOR UPDATE only if dialect is not sqlite
        query = Product.query.filter_by(id=product_id)
        if db.engine.dialect.name != "sqlite":
            query = query.with_for_update()

        product = query.first()

        if not product:
            return api_error("Product not found", error_code="NOT_FOUND", status_code=404)

        current_qty = product.quantity

        if has_delta:
            try:
                delta = int(body["delta"])
            except (ValueError, TypeError):
                return api_error("Field 'delta' must be an integer", status_code=400)
            
            if delta == 0:
                return api_error("Delta cannot be 0", status_code=400)
            new_qty = current_qty + delta
        else:
            try:
                target_qty = int(body["target_quantity"])
            except (ValueError, TypeError):
                return api_error("Field 'target_quantity' must be an integer", status_code=400)
            if target_qty < 0:
                return api_error("Target quantity cannot be negative", status_code=400)
            new_qty = target_qty
            delta = new_qty - current_qty

        if new_qty < 0:
            return api_error(
                f"Insufficient stock. Available: {current_qty}, requested reduction: {abs(delta)}",
                error_code="INSUFFICIENT_STOCK",
                status_code=409,
                details={
                    "available_quantity": current_qty,
                    "requested_change": delta,
                    "shortfall": abs(new_qty)
                }
            )

        # Apply stock change
        product.quantity = new_qty

        # Record authenticated identity from g.current_user
        authenticated_username = g.current_user.username if hasattr(g, "current_user") and g.current_user else "system_admin"

        audit_entry = StockHistory(
            product_id=product.id,
            previous_quantity=current_qty,
            new_quantity=new_qty,
            quantity_change=delta,
            reason=reason,
            user_id=authenticated_username
        )
        db.session.add(audit_entry)
        db.session.commit()

        # Trigger low-stock alert asynchronously if needed
        if product.is_low_stock:
            check_and_alert_low_stock.delay(product.id)

        return api_response(
            data={
                "product_id": product.id,
                "sku": product.sku,
                "previous_quantity": current_qty,
                "new_quantity": product.quantity,
                "quantity_changed": delta,
                "reason": reason,
                "user_id": authenticated_username,
                "is_low_stock": product.is_low_stock,
                "audit_id": audit_entry.id
            },
            message="Stock adjusted and audit record logged successfully"
        )

    except Exception as e:
        db.session.rollback()
        # Print actual error to stderr so pytest -s displays it immediately
        import traceback
        traceback.print_exc()
        return api_error(f"Failed to adjust stock: {str(e)}", error_code="DATABASE_ERROR", status_code=500)
@products_bp.route("/<int:product_id>/history", methods=["GET"])
def get_product_history(product_id):
    """
    Retrieve paginated audit history for a specific product,
    ordered newest to oldest.
    """
    product = db.session.get(Product, product_id)
    if not product:
        return api_error("Product not found", error_code="NOT_FOUND", status_code=404)

    page = max(request.args.get("page", 1, type=int), 1)
    limit = min(max(request.args.get("limit", 20, type=int), 1), 100)

    query = StockHistory.query.filter_by(product_id=product_id).order_by(StockHistory.created_at.desc())
    total_count = query.count()
    records = query.offset((page - 1) * limit).limit(limit).all()
    total_pages = (total_count + limit - 1) // limit if total_count > 0 else 1

    return api_response(data={
        "product_id": product.id,
        "sku": product.sku,
        "items": [r.to_dict() for r in records],
        "pagination": {
            "page": page,
            "limit": limit,
            "total_count": total_count,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
    })
    
@products_bp.route("/<int:product_id>", methods=["DELETE"])
@token_required
@roles_required("admin")
def delete_product(product_id):
    """Delete a product."""
    product = db.session.get(Product, product_id)
    if not product:
        return api_error("Product not found", error_code="NOT_FOUND", status_code=404)

    db.session.delete(product)
    db.session.commit()
    return api_response(message="Product deleted successfully")