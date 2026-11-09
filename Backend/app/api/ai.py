from flask import Blueprint, g, request
from sqlalchemy import func
from app.extensions import db
from app.models.inventory import Product, Category, StockHistory
from app.services.ai_service import AIService, AIServiceError
from app.utils.responses import api_response, api_error
from app.utils.auth import token_required, roles_required
from sqlalchemy import or_
from sqlalchemy.orm import joinedload


ai_bp = Blueprint("ai", __name__, url_prefix="/api/ai")

# ALLOWLIST of valid filter keys and expected types
ALLOWED_FILTERS = {
    "category": str,
    "search": str,
    "min_stock": int,
    "max_stock": int,
    "min_price": (int, float),
    "max_price": (int, float),
    "low_stock_only": bool
}

def validate_and_sanitize_filters(raw_filters: dict) -> dict:
    """
    Enforces strict allowlist validation against AI-generated filters.
    Strips unknown keys and verifies data types.
    """
    sanitized = {}
    if not isinstance(raw_filters, dict):
        return sanitized

    for key, expected_type in ALLOWED_FILTERS.items():
        if key in raw_filters:
            val = raw_filters[key]
            # Type check and conversion
            if isinstance(val, expected_type):
                if isinstance(val, str):
                    val = val.strip()
                    if val:
                        sanitized[key] = val
                elif isinstance(val, (int, float)):
                    if val >= 0:
                        sanitized[key] = val
                elif isinstance(val, bool):
                    sanitized[key] = val

    return sanitized

@ai_bp.route("/insights", methods=["GET"])
@token_required
@roles_required("admin", "staff")
def get_inventory_insights():
    """
    Computes factual inventory metrics deterministically from SQL,
    then uses AIService to interpret risks and summarize actionable insights.
    """
    try:
        # 1. Deterministic Aggregates via SQLAlchemy
        total_products = db.session.query(func.count(Product.id)).scalar() or 0
        total_units = db.session.query(func.sum(Product.quantity)).scalar() or 0

        # Category distribution
        category_stats = (
            db.session.query(
                Category.name,
                func.count(Product.id).label("product_count"),
                func.coalesce(func.sum(Product.quantity), 0).label("total_stock")
            )
            .outerjoin(Product, Category.id == Product.category_id)
            .group_by(Category.id, Category.name)
            .all()
        )

        categories_summary = [
            {"category": cat_name, "product_count": p_count, "total_stock": int(t_stock)}
            for cat_name, p_count, t_stock in category_stats
        ]

        # 2. Identify products at or below safety threshold
        low_stock_records = (
            Product.query
            .filter(Product.quantity <= Product.safety_stock_threshold)
            .order_by(Product.quantity.asc())
            .limit(10)
            .all()
        )

        low_stock_payload = [
            {
                "id": p.id,
                "sku": p.sku,
                "name": p.name,
                "quantity": p.quantity,
                "safety_stock_threshold": p.safety_stock_threshold,
                "unit_price": float(p.unit_price) if p.unit_price else 0.0
            }
            for p in low_stock_records
        ]

        # 3. Assemble Grounded Facts Payload
        factual_metrics = {
            "total_products": total_products,
            "total_units_in_stock": int(total_units),
            "low_stock_count": len(low_stock_records),
            "categories": categories_summary,
            "low_stock_products": low_stock_payload
        }

        # 4. Generate AI Interpretation
        ai_analysis = AIService.generate_inventory_insights(factual_metrics)

        # 5. Return both factual metrics and AI interpretation clearly demarcated
        return api_response(data={
            "metrics": factual_metrics,
            "analysis": ai_analysis
        })

    except AIServiceError as e:
        return api_error(e.args[0], error_code=e.error_code, status_code=e.status_code)
    except Exception as e:
        return api_error(f"Failed to generate inventory insights: {str(e)}", error_code="SERVER_ERROR", status_code=500)
@ai_bp.route("/search", methods=["POST"])
@token_required
@roles_required("admin", "staff")
def natural_language_search():
    """
    Translates an everyday phrase into validated database filters
    and executes a safe, parameterized SQLAlchemy query.
    """
    body = request.get_json(silent=True)
    if not body or not body.get("query"):
        return api_error("Field 'query' is required", status_code=400)

    user_query = str(body["query"]).strip()
    if len(user_query) > 300:
        return api_error("Search query exceeds maximum length of 300 characters", status_code=400)

    try:
        # 1. AI Intent Parsing
        parsed_result = AIService.parse_natural_language_search(user_query)
        raw_filters = parsed_result.get("filters", {})
        explanation = parsed_result.get("explanation", "Search query applied")

        # 2. Strict Backend Validation against Allowlist
        valid_filters = validate_and_sanitize_filters(raw_filters)

        # 3. Construct Parameterized SQLAlchemy Query
        query = Product.query.options(joinedload(Product.category))

        if "category" in valid_filters:
            # Case-insensitive category match
            query = query.join(Category).filter(Category.name.ilike(f"%{valid_filters['category']}%"))

        if "search" in valid_filters:
            term = valid_filters["search"]
            query = query.filter(
                or_(
                    Product.name.ilike(f"%{term}%"),
                    Product.sku.ilike(f"%{term}%")
                )
            )

        if "min_stock" in valid_filters:
            query = query.filter(Product.quantity >= valid_filters["min_stock"])

        if "max_stock" in valid_filters:
            query = query.filter(Product.quantity <= valid_filters["max_stock"])

        if "min_price" in valid_filters:
            query = query.filter(Product.unit_price >= valid_filters["min_price"])

        if "max_price" in valid_filters:
            query = query.filter(Product.unit_price <= valid_filters["max_price"])

        if valid_filters.get("low_stock_only"):
            query = query.filter(Product.quantity <= Product.safety_stock_threshold)

        # Bound results to maximum 50 records
        products = query.order_by(Product.name.asc()).limit(50).all()

        return api_response(data={
            "query": user_query,
            "explanation": explanation,
            "applied_filters": valid_filters,
            "count": len(products),
            "items": [p.to_dict() for p in products]
        })

    except AIServiceError as e:
        return api_error(e.args[0], error_code=e.error_code, status_code=e.status_code)
    except Exception as e:
        return api_error(f"Search failed: {str(e)}", error_code="SEARCH_ERROR", status_code=500)
@ai_bp.route("/chat", methods=["POST"])
@token_required
@roles_required("admin", "staff")
def inventory_chat():
    """
    Administrative inventory chatbot with allowlisted read-only tool calling.
    Expects JSON payload with 'messages': [{'role': 'user', 'content': '...'}]
    """
    body = request.get_json(silent=True)
    if not body or "messages" not in body or not isinstance(body["messages"], list):
        return api_error("Field 'messages' must be a non-empty list of chat message objects", status_code=400)

    messages = body["messages"]
    if not messages:
        return api_error("Chat history cannot be empty", status_code=400)

    # Sanitize message payload
    sanitized_messages = []
    for m in messages[-8:]:  # Bound conversation window to last 8 turns
        role = m.get("role")
        content = str(m.get("content", "")).strip()
        if role in ["user", "assistant"] and content:
            sanitized_messages.append({"role": role, "content": content[:1000]})

    if not sanitized_messages:
        return api_error("No valid message content provided", status_code=400)

    try:
        response_data = AIService.chat_with_tools(sanitized_messages)
        return api_response(data=response_data)
    except AIServiceError as e:
        return api_error(e.args[0], error_code=e.error_code, status_code=e.status_code)
    except Exception as e:
        return api_error(f"Chat failed: {str(e)}", error_code="CHAT_ERROR", status_code=500)    