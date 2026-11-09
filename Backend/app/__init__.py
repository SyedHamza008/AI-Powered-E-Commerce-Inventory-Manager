from flask import Flask, jsonify
from app.config import config_by_name
from app.extensions import db, migrate
from app import models  # Ensure models are imported for SQLAlchemy to recognize them
from app.api.categories import categories_bp
from app.api.products import products_bp
from app.api.suppliers import suppliers_bp
from app.api.auth import auth_bp  # Import the auth blueprint
from app.api.ai import ai_bp  # Import the AI blueprint
from app.celery_app import make_celery, celery

def create_app(config_name="development"):
    """
    Application factory for initializing the Flask app, database, and migrations.
    """
    app = Flask(__name__)
    
    # Initialize Celery with the Flask app context
    global celery
    celery = make_celery(app)
    
    # Load configuration
    app.config.from_object(config_by_name.get(config_name, config_by_name["development"]))

    # Initialize extensions with this app instance
    db.init_app(app)
    migrate.init_app(app, db)

    # Register blueprints
    app.register_blueprint(categories_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(suppliers_bp)
    app.register_blueprint(auth_bp)  # Register the auth blueprint
    app.register_blueprint(ai_bp)  # Register the AI blueprint

    # Health-check route
    @app.route("/api/health", methods=["GET"])
    def health_check():
        # Check if database connection is alive
        db_status = "connected"
        try:
            # Run a lightweight ping check
            db.session.execute(db.text("SELECT 1"))
        except Exception as e:
            db_status = f"unreachable: {str(e)}"

        return jsonify({
            "status": "healthy" if "unreachable" not in db_status else "degraded",
            "environment": app.config.get("ENV"),
            "service": "inventory-backend",
            "database": db_status
        }), (200 if "unreachable" not in db_status else 503)

    return app