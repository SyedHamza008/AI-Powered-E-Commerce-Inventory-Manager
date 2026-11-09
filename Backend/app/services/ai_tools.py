from app.extensions import db
from app.models.inventory import Product, Category, Supplier, StockHistory
from sqlalchemy import func

# 1. Concrete Tool Implementations (Deterministic Python DB queries)

def tool_get_low_stock_products(limit: int = 10) -> dict:
    """Retrieves products currently at or below their safety stock threshold."""
    limit = min(max(int(limit), 1), 25)
    products = (
        Product.query
        .filter(Product.quantity <= Product.safety_stock_threshold)
        .order_by(Product.quantity.asc())
        .limit(limit)
        .all()
    )
    return {
        "count": len(products),
        "products": [
            {
                "id": p.id,
                "sku": p.sku,
                "name": p.name,
                "quantity": p.quantity,
                "safety_threshold": p.safety_stock_threshold,
                "category": p.category.name if p.category else "Unassigned"
            }
            for p in products
        ]
    }

def tool_get_product_details(identifier: str) -> dict:
    """Retrieves detailed product specs, pricing, and suppliers by SKU or ID."""
    clean_id = str(identifier).strip()
    product = None
    if clean_id.isdigit():
        product = db.session.get(Product, int(clean_id))
    if not product:
        product = Product.query.filter(Product.sku.ilike(clean_id)).first()

    if not product:
        return {"error": f"Product '{identifier}' not found in inventory."}

    return {
        "id": product.id,
        "sku": product.sku,
        "name": product.name,
        "unit_price": float(product.unit_price) if product.unit_price else 0.0,
        "quantity": product.quantity,
        "safety_threshold": product.safety_stock_threshold,
        "is_low_stock": product.is_low_stock,
        "category": product.category.name if product.category else None,
        "suppliers": [s.name for s in product.suppliers]
    }

def tool_get_category_summary() -> dict:
    """Summarizes overall stock levels across all departments/categories."""
    stats = (
        db.session.query(
            Category.name,
            func.count(Product.id).label("product_count"),
            func.coalesce(func.sum(Product.quantity), 0).label("total_units")
        )
        .outerjoin(Product, Category.id == Product.category_id)
        .group_by(Category.id, Category.name)
        .all()
    )
    return {
        "categories": [
            {"category": name, "product_count": count, "total_units": int(units)}
            for name, count, units in stats
        ]
    }

def tool_get_recent_stock_history(product_id: int, limit: int = 5) -> dict:
    """Retrieves recent audit logs for a given product ID."""
    limit = min(max(int(limit), 1), 10)
    records = (
        StockHistory.query
        .filter_by(product_id=product_id)
        .order_by(StockHistory.created_at.desc())
        .limit(limit)
        .all()
    )
    return {
        "product_id": product_id,
        "history": [r.to_dict() for r in records]
    }

# 2. Tool Dispatch Map
TOOL_DISPATCH = {
    "get_low_stock_products": tool_get_low_stock_products,
    "get_product_details": tool_get_product_details,
    "get_category_summary": tool_get_category_summary,
    "get_recent_stock_history": tool_get_recent_stock_history
}

# 3. LLM Function Calling Declarations (OpenAI/Gemini standard tool schema)
CHATBOT_TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "get_low_stock_products",
            "description": "Fetch products that are running low on inventory or at/below safety threshold.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Max number of items to return (1-25)."}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_product_details",
            "description": "Lookup inventory details, pricing, and suppliers for a product by its SKU or ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "identifier": {"type": "string", "description": "The SKU code (e.g. ELEC-LAPTOP-01) or integer ID."}
                },
                "required": ["identifier"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_category_summary",
            "description": "Retrieve aggregated unit counts and product totals across all inventory categories.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_recent_stock_history",
            "description": "Retrieve recent immutable audit ledger records and adjustments for a specific product ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "integer", "description": "The product's database ID."},
                    "limit": {"type": "integer", "description": "Number of audit entries (default 5)."}
                },
                "required": ["product_id"]
            }
        }
    }
]

@staticmethod
def chat_with_tools(messages: list) -> dict:
        """
        Executes a multi-turn chat cycle with tool-calling capabilities.
        Evaluates tool calls, queries local database functions, and returns a verified final answer.
        """
        provider = current_app.config.get("AI_PROVIDER", "mock").lower()

        if provider == "mock" or current_app.config.get("TESTING"):
            return AIService._mock_chat_response(messages)

        return AIService._call_remote_chat(messages)

@staticmethod
def _mock_chat_response(messages: list) -> dict:
        """Mock chatbot providing deterministic responses and simulating tool invocations."""
        last_message = messages[-1]["content"].lower() if messages else ""
        from app.services.ai_tools import TOOL_DISPATCH

        if "low stock" in last_message or "below safety" in last_message:
            tool_data = TOOL_DISPATCH["get_low_stock_products"](limit=5)
            count = tool_data["count"]
            return {
                "reply": f"According to current database records, there are {count} product(s) at or below safety stock.",
                "tools_used": ["get_low_stock_products"],
                "tool_data": tool_data
            }

        if "laptop" in last_message or "elec-laptop-01" in last_message:
            tool_data = TOOL_DISPATCH["get_product_details"](identifier="ELEC-LAPTOP-01")
            return {
                "reply": f"The {tool_data.get('name', 'Laptop')} ({tool_data.get('sku')}) currently has {tool_data.get('quantity')} units on hand.",
                "tools_used": ["get_product_details"],
                "tool_data": tool_data
            }

        return {
            "reply": "I am your inventory assistant. You can ask me about stock counts, low-stock alerts, suppliers, or recent audit history.",
            "tools_used": [],
            "tool_data": {}
        }

@staticmethod
def _call_remote_chat(messages: list) -> dict:
        """Remote LLM tool-calling orchestrator."""
        from app.services.ai_tools import CHATBOT_TOOLS_SCHEMA, TOOL_DISPATCH

        api_key = current_app.config.get("AI_API_KEY")
        if not api_key:
            raise AIServiceError("AI API key is not configured", error_code="AI_CONFIG_ERROR", status_code=500)

        timeout = current_app.config.get("AI_TIMEOUT_SECONDS", 15)

        system_message = {
            "role": "system",
            "content": (
                "You are an administrative inventory assistant for an e-commerce company. "
                "You have access to read-only tools for querying inventory facts, categories, suppliers, and audit history. "
                "Always call the appropriate tool to retrieve facts before answering questions. "
                "Never invent stock figures, supplier names, or audit timestamps. "
                "Be concise, professional, and clear."
            )
        }

        request_messages = [system_message] + messages

        # Phase 1: Request with available tools
        payload = {
            "model": current_app.config.get("AI_MODEL_NAME", "gemini-1.5-flash"),
            "messages": request_messages,
            "tools": CHATBOT_TOOLS_SCHEMA,
            "tool_choice": "auto",
            "temperature": 0.2
        }

        try:
            res = requests.post(
                "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
                json=payload,
                timeout=timeout
            )
            if not res.ok:
                raise AIServiceError(f"AI provider returned status {res.status_code}", status_code=502)

            data = res.json()
            message_obj = data["choices"][0]["message"]
            tools_used = []
            final_tool_data = {}

            # Phase 2: Check if model invoked tool calls
            if message_obj.get("tool_calls"):
                request_messages.append(message_obj)

                for tool_call in message_obj["tool_calls"]:
                    func_name = tool_call["function"]["name"]
                    func_args = json.loads(tool_call["function"].get("arguments", "{}"))

                    if func_name in TOOL_DISPATCH:
                        tools_used.append(func_name)
                        tool_result = TOOL_DISPATCH[func_name](**func_args)
                        final_tool_data[func_name] = tool_result

                        request_messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "name": func_name,
                            "content": json.dumps(tool_result)
                        })

                # Phase 3: Final synthesis with tool results
                second_payload = {
                    "model": current_app.config.get("AI_MODEL_NAME", "gemini-1.5-flash"),
                    "messages": request_messages,
                    "temperature": 0.2
                }

                second_res = requests.post(
                    "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
                    headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
                    json=second_payload,
                    timeout=timeout
                )
                if not second_res.ok:
                    raise AIServiceError("Failed to synthesize tool response", status_code=502)

                final_reply = second_res.json()["choices"][0]["message"]["content"]
                return {
                    "reply": final_reply,
                    "tools_used": tools_used,
                    "tool_data": final_tool_data
                }

            return {
                "reply": message_obj.get("content", ""),
                "tools_used": [],
                "tool_data": {}
            }

        except Exception as e:
            raise AIServiceError(f"Chatbot failed: {str(e)}", error_code="CHAT_ERROR", status_code=502)