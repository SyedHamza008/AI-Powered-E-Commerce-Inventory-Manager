import os
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()

class Config:
    """Base configuration."""
    SECRET_KEY = os.getenv("SECRET_KEY", "default-fallback-key")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEBUG = False
    TESTING = False
    ENV = os.getenv("FLASK_ENV", "production")

    # AI Service Settings
    AI_PROVIDER = os.getenv("AI_PROVIDER", "mock")
    AI_API_KEY = os.getenv("AI_API_KEY", "")
    AI_MODEL_NAME = os.getenv("AI_MODEL_NAME", "gemini-1.5-flash")
    AI_TIMEOUT_SECONDS = int(os.getenv("AI_TIMEOUT_SECONDS", "10"))
    
    # Celery & Redis Settings
    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
    ALERT_EMAIL_RECIPIENT = os.getenv("ALERT_EMAIL_RECIPIENT", "admin@inventory.local")
class DevelopmentConfig(Config):
    """Local development configuration."""
    DEBUG = True
    ENV = "development"
    # Use PostgreSQL database URL from .env, or fallback to local SQLite for rapid prototyping
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", 
        "sqlite:///inventory_dev.db"
    )

class TestingConfig(Config):
    """Isolated configuration for automated testing."""
    TESTING = True
    DEBUG = True
    ENV = "testing"
    # Use fast in-memory SQLite for automated tests so tests run instantly without external dependencies
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    # celery tasks should execute synchronously during tests to simplify assertions
    CELERY_TASK_ALWAYS_EAGER = True

config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": Config
}