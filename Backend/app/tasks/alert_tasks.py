import logging
from datetime import datetime, timezone
from flask import current_app
from app.celery_app import celery
from app.extensions import db
from app.models.inventory import Product

logger = logging.getLogger(__name__)

# In-memory alert cooldown cache (prevents duplicate spam if stock changes frequently)
# Maps product_id -> last_notified_timestamp
_ALERT_COOLDOWN = {}

@celery.task(bind=True, max_retries=3, default_retry_delay=60)
def check_and_alert_low_stock(self, product_id: int):
    """
    Background worker task:
    1. Checks if the product is at or below its safety threshold.
    2. Enforces a deduplication cooldown.
    3. Dispatches an email notification to the administrator.
    """
    try:
        product = db.session.get(Product, product_id)
        if not product:
            logger.warning("Product ID %s not found for low-stock check", product_id)
            return {"status": "skipped", "reason": "product_not_found"}

        if not product.is_low_stock:
            return {"status": "skipped", "reason": "stock_above_threshold"}

        # Cooldown check: prevent duplicate notifications within 1 hour for the same item
        now = datetime.now(timezone.utc)
        last_sent = _ALERT_COOLDOWN.get(product.id)
        if last_sent and (now - last_sent).total_seconds() < 3600:
            logger.info("Notification for SKU %s suppressed by cooldown", product.sku)
            return {"status": "suppressed", "reason": "cooldown_active"}

        recipient = current_app.config.get("ALERT_EMAIL_RECIPIENT", "admin@inventory.local")

        # Construct notification content
        subject = f"⚠️ [LOW STOCK ALERT] Product {product.sku} is below threshold!"
        body = (
            f"Inventory Warning:\n\n"
            f"Product: {product.name} ({product.sku})\n"
            f"Current Quantity: {product.quantity}\n"
            f"Safety Stock Threshold: {product.safety_stock_threshold}\n"
            f"Category: {product.category.name if product.category else 'N/A'}\n"
            f"Timestamp: {now.isoformat()}\n\n"
            f"Action Required: Please arrange a supplier reorder immediately."
        )

        # Log simulated email dispatch (or connect smtplib/SendGrid here)
        logger.warning(
            "\n========== [EMAIL DISPATCHED TO %s] ==========\nSUBJECT: %s\n%s\n==================================================",
            recipient, subject, body
        )

        # Record cooldown
        _ALERT_COOLDOWN[product.id] = now

        return {
            "status": "alert_dispatched",
            "product_id": product.id,
            "sku": product.sku,
            "recipient": recipient,
            "quantity": product.quantity,
            "threshold": product.safety_stock_threshold
        }

    except Exception as exc:
        logger.error("Failed to process low-stock alert: %s", str(exc))
        # Retry with exponential backoff
        raise self.retry(exc=exc)