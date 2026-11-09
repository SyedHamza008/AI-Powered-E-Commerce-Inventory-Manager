import json
import logging
import requests
from flask import current_app

logger = logging.getLogger(__name__)

class AIServiceError(Exception):
    """Custom exception raised when an AI provider fails or returns malformed data."""
    def __init__(self, message, error_code="AI_SERVICE_ERROR", status_code=502):
        super().__init__(message)
        self.error_code = error_code
        self.status_code = status_code


class AIService:
    """
    Service layer providing an isolated, resilient interface to LLMs.
    Enforces structured outputs, response validation, timeouts, and mock adapters.
    """

    @staticmethod
    def generate_inventory_insights(facts_payload: dict) -> dict:
        """
        Takes factual, pre-calculated inventory metrics from the backend
        and prompts the LLM to interpret risks and summarize trends.
        """
        provider = current_app.config.get("AI_PROVIDER", "mock").lower()

        # 1. Route to Mock adapter during tests or local offline development
        if provider == "mock" or current_app.config.get("TESTING"):
            return AIService._mock_inventory_insights(facts_payload)

        # 2. Production provider integration (e.g. Gemini / OpenAI / Compatible endpoint)
        return AIService._call_remote_provider(facts_payload)

    @staticmethod
    def _mock_inventory_insights(facts: dict) -> dict:
        """Deterministic mock response for automated testing and offline dev."""
        low_stock_count = len(facts.get("low_stock_products", []))
        total_products = facts.get("total_products", 0)

        risk_level = "HIGH" if low_stock_count > 0 else "LOW"
        summary = (
            f"Inventory audit completed. Found {low_stock_count} item(s) below safety stock thresholds "
            f"out of {total_products} tracked product lines."
        )

        recommendations = []
        for p in facts.get("low_stock_products", []):
            recommendations.append({
                "product_id": p.get("id"),
                "sku": p.get("sku"),
                "suggested_action": f"Reorder immediately. Current balance ({p.get('quantity')}) is below safety threshold ({p.get('safety_stock_threshold')}).",
                "urgency": "HIGH"
            })

        return {
            "risk_level": risk_level,
            "summary": summary,
            "recommendations": recommendations,
            "provider_used": "mock-adapter"
        }

    @staticmethod
    def _call_remote_provider(facts: dict) -> dict:
        """
        Sends pre-aggregated inventory metrics to the remote LLM API
        with strict system instructions to return JSON only.
        """
        api_key = current_app.config.get("AI_API_KEY")
        if not api_key:
            raise AIServiceError("AI API key is not configured on the server", error_code="AI_CONFIG_ERROR", status_code=500)

        timeout = current_app.config.get("AI_TIMEOUT_SECONDS", 10)
        
        system_prompt = (
            "You are an expert E-commerce Inventory Risk Analyst. "
            "Analyze the provided factual inventory metrics and return ONLY a valid JSON object matching this schema:\n"
            "{\n"
            '  "risk_level": "LOW" | "MEDIUM" | "HIGH",\n'
            '  "summary": "concise executive summary string",\n'
            '  "recommendations": [\n'
            '    {\n'
            '      "product_id": integer,\n'
            '      "sku": "string",\n'
            '      "suggested_action": "string",\n'
            '      "urgency": "LOW" | "MEDIUM" | "HIGH"\n'
            "    }\n"
            "  ]\n"
            "}\n"
            "Do NOT include Markdown fences (```json), conversational pleasantries, or speculative facts."
        )

        user_content = f"Factual Inventory Metrics: {json.dumps(facts)}"

        # Example endpoint payload structure (generic standard REST/OpenAI/Gemini proxy format)
        payload = {
            "model": current_app.config.get("AI_MODEL_NAME", "gemini-1.5-flash"),
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            "temperature": 0.2
        }

        try:
            # Pings provider with timeout safeguard
            response = requests.post(
                "[https://generativelanguage.googleapis.com/v1beta/openai/chat/completions](https://generativelanguage.googleapis.com/v1beta/openai/chat/completions)",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}"
                },
                json=payload,
                timeout=timeout
            )

            if response.status_code == 429:
                raise AIServiceError("AI provider rate limit exceeded. Please try again shortly.", error_code="RATE_LIMIT", status_code=429)

            if not response.ok:
                raise AIServiceError(f"AI provider returned error {response.status_code}: {response.text}", error_code="PROVIDER_ERROR", status_code=502)

            data = response.json()
            raw_text = data["choices"][0]["message"]["content"].strip()

            # Clean unexpected formatting fences if returned
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]

            parsed_json = json.loads(raw_text.strip())
            parsed_json["provider_used"] = current_app.config.get("AI_MODEL_NAME")
            return parsed_json

        except requests.Timeout:
            raise AIServiceError("AI service request timed out. Continuing with factual metrics.", error_code="TIMEOUT", status_code=504)
        except requests.RequestException as e:
            raise AIServiceError(f"Network error contacting AI provider: {str(e)}", error_code="NETWORK_ERROR", status_code=502)
        except (json.JSONDecodeError, KeyError) as e:
            logger.error("Failed to parse LLM structured output: %s", str(e))
            raise AIServiceError("AI provider returned invalid structured JSON", error_code="MALFORMED_OUTPUT", status_code=502)
    
    @staticmethod
    def parse_natural_language_search(query_text: str) -> dict:
        """
        Parses a freeform natural-language search query into a structured,
        allowlisted filter specification.
        """
        provider = current_app.config.get("AI_PROVIDER", "mock").lower()

        if provider == "mock" or current_app.config.get("TESTING"):
            return AIService._mock_parse_search_query(query_text)

        return AIService._call_remote_search_parser(query_text)

    @staticmethod
    def _mock_parse_search_query(text: str) -> dict:
        """Deterministic mock parser matching common patterns for tests and offline dev."""
        t = text.lower()
        filters = {}

        if "electronic" in t:
            filters["category"] = "Electronics"
        elif "apparel" in t:
            filters["category"] = "Apparel"
        elif "storage" in t:
            filters["category"] = "Storage"

        if "fewer than" in t or "less than" in t or "under" in t:
            # Simple extraction for phrases like "fewer than 10"
            import re
            match = re.search(r'(?:fewer than|less than|under)\s+(\d+)', t)
            if match:
                filters["max_stock"] = int(match.group(1))

        if "low stock" in t or "below safety" in t or "threshold" in t:
            filters["low_stock_only"] = True

        if "out of stock" in t or "zero stock" in t:
            filters["max_stock"] = 0

        # General search keyword
        if "mouse" in t:
            filters["search"] = "mouse"
        elif "laptop" in t:
            filters["search"] = "laptop"

        return {
            "filters": filters,
            "explanation": f"Filtered by natural-language query: '{text}'"
        }

    @staticmethod
    def _call_remote_search_parser(query_text: str) -> dict:
        """Calls remote model to translate query text into structured JSON filters."""
        api_key = current_app.config.get("AI_API_KEY")
        if not api_key:
            raise AIServiceError("AI API key is not configured", error_code="AI_CONFIG_ERROR", status_code=500)

        timeout = current_app.config.get("AI_TIMEOUT_SECONDS", 10)

        system_prompt = (
            "You are a natural-language search query parser for an e-commerce inventory database. "
            "Convert the user's search phrase into a valid JSON object matching this schema ONLY:\n"
            "{\n"
            '  "filters": {\n'
            '    "category": string (optional),\n'
            '    "search": string (optional, product name or sku keywords),\n'
            '    "min_stock": integer (optional),\n'
            '    "max_stock": integer (optional),\n'
            '    "min_price": number (optional),\n'
            '    "max_price": number (optional),\n'
            '    "low_stock_only": boolean (optional)\n'
            "  },\n"
            '  "explanation": "concise description of what filters were extracted"\n'
            "}\n"
            "Rules:\n"
            "1. Output ONLY pure JSON. No markdown fences, no conversational text.\n"
            "2. Do NOT invent fields outside this schema.\n"
            "3. If a request is ambiguous or contains no filters, return an empty filters object."
        )

        payload = {
            "model": current_app.config.get("AI_MODEL_NAME", "gemini-1.5-flash"),
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query_text}
            ],
            "temperature": 0.0
        }

        try:
            response = requests.post(
                "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}"
                },
                json=payload,
                timeout=timeout
            )
            if not response.ok:
                raise AIServiceError(f"Provider returned error {response.status_code}", status_code=502)

            data = response.json()
            raw_text = data["choices"][0]["message"]["content"].strip()
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]

            return json.loads(raw_text.strip())
        except Exception as e:
            raise AIServiceError(f"Failed to parse search query: {str(e)}", error_code="PARSER_ERROR", status_code=502)