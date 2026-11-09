from flask import Blueprint, request
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from app.extensions import db
from app.models.inventory import Category, Product
from app.utils.responses import api_response, api_error
from app.utils.auth import token_required, roles_required

categories_bp = Blueprint("categories", __name__, url_prefix="/api/categories")

@categories_bp.route("", methods=["GET"])
def get_categories():
    """Retrieve all categories ordered by name with active product counts."""
    results = (
        db.session.query(
            Category,
            func.count(Product.id).label("product_count")
        )
        .outerjoin(Product, Category.id == Product.category_id)
        .group_by(Category.id)
        .order_by(Category.name.asc())
        .all()
    )

    data = []
    for cat, count in results:
        cat_dict = cat.to_dict()
        cat_dict["product_count"] = count
        data.append(cat_dict)

    return api_response(data=data)

@categories_bp.route("/<int:category_id>", methods=["GET"])
def get_category(category_id):
    """Retrieve a single category by primary key ID with product count."""
    category = db.session.get(Category, category_id)
    if not category:
        return api_error("Category not found", error_code="NOT_FOUND", status_code=404)
    
    count = Product.query.filter_by(category_id=category_id).count()
    cat_dict = category.to_dict()
    cat_dict["product_count"] = count
    return api_response(data=cat_dict)

@categories_bp.route("", methods=["POST"])
@token_required
@roles_required("admin")
def create_category():
    """Create a new category (Admin only)."""
    body = request.get_json(silent=True)
    if not body:
        return api_error("Invalid or missing JSON payload in request body", status_code=400)

    name = body.get("name")
    if not name or not isinstance(name, str) or not name.strip():
        return api_error("Field 'name' is required and cannot be empty", status_code=400)

    name = name.strip()
    description = body.get("description", "")
    if description and isinstance(description, str):
        description = description.strip()

    if Category.query.filter(Category.name.ilike(name)).first():
        return api_error(f"Category with name '{name}' already exists", error_code="DUPLICATE_NAME", status_code=409)

    category = Category(name=name, description=description)
    try:
        db.session.add(category)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return api_error("Database integrity error occurred", error_code="DATABASE_ERROR", status_code=409)

    cat_dict = category.to_dict()
    cat_dict["product_count"] = 0
    return api_response(data=cat_dict, message="Category created successfully", status_code=201)

@categories_bp.route("/<int:category_id>", methods=["PATCH"])
@token_required
@roles_required("admin")
def update_category(category_id):
    """Partially update an existing category (Admin only)."""
    category = db.session.get(Category, category_id)
    if not category:
        return api_error("Category not found", error_code="NOT_FOUND", status_code=404)

    body = request.get_json(silent=True)
    if not body:
        return api_error("Invalid or missing JSON payload in request body", status_code=400)

    if "name" in body:
        new_name = body["name"]
        if not new_name or not isinstance(new_name, str) or not new_name.strip():
            return api_error("Field 'name' cannot be empty", status_code=400)
        
        new_name = new_name.strip()
        existing = Category.query.filter(Category.name.ilike(new_name), Category.id != category_id).first()
        if existing:
            return api_error(f"Category with name '{new_name}' already exists", error_code="DUPLICATE_NAME", status_code=409)
        category.name = new_name

    if "description" in body:
        desc = body["description"]
        category.description = desc.strip() if isinstance(desc, str) else None

    db.session.commit()
    count = Product.query.filter_by(category_id=category_id).count()
    cat_dict = category.to_dict()
    cat_dict["product_count"] = count
    return api_response(data=cat_dict, message="Category updated successfully")

@categories_bp.route("/<int:category_id>", methods=["DELETE"])
@token_required
@roles_required("admin")
def delete_category(category_id):
    """Delete a category if no products are associated with it (Admin only)."""
    category = db.session.get(Category, category_id)
    if not category:
        return api_error("Category not found", error_code="NOT_FOUND", status_code=404)

    # Referential integrity check
    product_count = Product.query.filter_by(category_id=category_id).count()
    if product_count > 0:
        return api_error(
            f"Cannot delete category '{category.name}' because {product_count} product(s) are associated with it.",
            error_code="HAS_DEPENDENT_PRODUCTS",
            status_code=409
        )

    try:
        db.session.delete(category)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return api_error("Cannot delete category due to database constraint violation", error_code="RESTRICT_VIOLATION", status_code=409)

    return api_response(message="Category deleted successfully", status_code=200)