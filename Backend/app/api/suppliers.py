from flask import Blueprint, request
from sqlalchemy import func
from app.extensions import db
from app.models.inventory import Supplier, product_suppliers
from app.utils.responses import api_response, api_error
from app.utils.auth import token_required, roles_required

suppliers_bp = Blueprint("suppliers", __name__, url_prefix="/api/suppliers")

@suppliers_bp.route("", methods=["GET"])
def get_suppliers():
    """List all suppliers sorted alphabetically with supplied product counts."""
    results = (
        db.session.query(
            Supplier,
            func.count(product_suppliers.c.product_id).label("product_count")
        )
        .outerjoin(product_suppliers, Supplier.id == product_suppliers.c.supplier_id)
        .group_by(Supplier.id)
        .order_by(Supplier.name.asc())
        .all()
    )

    data = []
    for sup, count in results:
        sup_dict = sup.to_dict()
        sup_dict["product_count"] = count
        data.append(sup_dict)

    return api_response(data=data)

@suppliers_bp.route("/<int:supplier_id>", methods=["GET"])
def get_supplier(supplier_id):
    """Retrieve single supplier details with product count."""
    supplier = db.session.get(Supplier, supplier_id)
    if not supplier:
        return api_error("Supplier not found", error_code="NOT_FOUND", status_code=404)
    
    count = db.session.query(func.count(product_suppliers.c.product_id)).filter(
        product_suppliers.c.supplier_id == supplier_id
    ).scalar() or 0

    sup_dict = supplier.to_dict()
    sup_dict["product_count"] = count
    return api_response(data=sup_dict)

@suppliers_bp.route("", methods=["POST"])
@token_required
@roles_required("admin")
def create_supplier():
    """Create a new supplier (Admin only)."""
    body = request.get_json(silent=True)
    if not body:
        return api_error("Invalid or missing JSON payload", status_code=400)

    name = body.get("name")
    email = body.get("contact_email")
    phone = body.get("phone", "")
    address = body.get("address", "")

    if not name or not isinstance(name, str) or not name.strip():
        return api_error("Field 'name' is required", status_code=400)
    if not email or not isinstance(email, str) or "@" not in email:
        return api_error("A valid 'contact_email' is required", status_code=400)

    name = name.strip()
    if Supplier.query.filter(Supplier.name.ilike(name)).first():
        return api_error(f"Supplier '{name}' already exists", error_code="DUPLICATE_NAME", status_code=409)

    supplier = Supplier(
        name=name,
        contact_email=email.strip().lower(),
        phone=phone.strip() if isinstance(phone, str) else None,
        address=address.strip() if isinstance(address, str) else None
    )
    db.session.add(supplier)
    db.session.commit()

    sup_dict = supplier.to_dict()
    sup_dict["product_count"] = 0
    return api_response(data=sup_dict, message="Supplier created successfully", status_code=201)

@suppliers_bp.route("/<int:supplier_id>", methods=["PATCH"])
@token_required
@roles_required("admin")
def update_supplier(supplier_id):
    """Partially update supplier details (Admin only)."""
    supplier = db.session.get(Supplier, supplier_id)
    if not supplier:
        return api_error("Supplier not found", error_code="NOT_FOUND", status_code=404)

    body = request.get_json(silent=True)
    if not body:
        return api_error("Invalid or missing JSON payload", status_code=400)

    if "name" in body:
        name = body["name"]
        if not name or not isinstance(name, str) or not name.strip():
            return api_error("Field 'name' cannot be empty", status_code=400)
        name = name.strip()
        existing = Supplier.query.filter(Supplier.name.ilike(name), Supplier.id != supplier_id).first()
        if existing:
            return api_error(f"Supplier '{name}' already exists", error_code="DUPLICATE_NAME", status_code=409)
        supplier.name = name

    if "contact_email" in body:
        email = body["contact_email"]
        if not email or "@" not in email:
            return api_error("Valid 'contact_email' is required", status_code=400)
        supplier.contact_email = email.strip().lower()

    if "phone" in body:
        phone = body["phone"]
        supplier.phone = phone.strip() if isinstance(phone, str) else None

    if "address" in body:
        addr = body["address"]
        supplier.address = addr.strip() if isinstance(addr, str) else None

    db.session.commit()

    count = db.session.query(func.count(product_suppliers.c.product_id)).filter(
        product_suppliers.c.supplier_id == supplier_id
    ).scalar() or 0

    sup_dict = supplier.to_dict()
    sup_dict["product_count"] = count
    return api_response(data=sup_dict, message="Supplier updated successfully")

@suppliers_bp.route("/<int:supplier_id>", methods=["DELETE"])
@token_required
@roles_required("admin")
def delete_supplier(supplier_id):
    """Delete a supplier (Admin only)."""
    supplier = db.session.get(Supplier, supplier_id)
    if not supplier:
        return api_error("Supplier not found", error_code="NOT_FOUND", status_code=404)

    db.session.delete(supplier)
    db.session.commit()
    return api_response(message="Supplier deleted successfully", status_code=200)