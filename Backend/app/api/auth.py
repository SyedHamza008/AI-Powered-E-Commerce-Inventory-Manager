from functools import wraps
from flask import Blueprint, request, g
from app.extensions import db
from app.models.user import User
from app.utils.responses import api_response, api_error
from app.utils.auth import generate_token, token_required

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

@auth_bp.route("/register", methods=["POST"])
def register():
    """Register a new user account."""
    body = request.get_json(silent=True)
    if not body:
        return api_error("Invalid or missing JSON payload", status_code=400)

    username = str(body.get("username", "")).strip()
    email = str(body.get("email", "")).strip().lower()
    password = str(body.get("password", "")).strip()
    role = str(body.get("role", "staff")).strip().lower()

    if not username or len(username) < 3:
        return api_error("Username must be at least 3 characters long", status_code=400)
    if not email or "@" not in email:
        return api_error("A valid email address is required", status_code=400)
    if not password or len(password) < 6:
        return api_error("Password must be at least 6 characters long", status_code=400)
    if role not in ["admin", "staff"]:
        return api_error("Role must be either 'admin' or 'staff'", status_code=400)

    if User.query.filter_by(username=username).first():
        return api_error(f"Username '{username}' is already registered", error_code="DUPLICATE_USERNAME", status_code=409)
    if User.query.filter_by(email=email).first():
        return api_error(f"Email '{email}' is already registered", error_code="DUPLICATE_EMAIL", status_code=409)

    user = User(username=username, email=email, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    token = generate_token(user)
    return api_response(
        data={"user": user.to_dict(), "token": token},
        message="User registered successfully",
        status_code=201
    )

@auth_bp.route("/login", methods=["POST"])
def login():
    """Authenticate with username/email and password, returning a JWT token."""
    body = request.get_json(silent=True)
    if not body:
        return api_error("Invalid or missing JSON payload", status_code=400)

    identifier = str(body.get("identifier", "")).strip()
    password = str(body.get("password", "")).strip()

    if not identifier or not password:
        return api_error("Identifier (username or email) and password are required", status_code=400)

    # Search by either username or email
    user = User.query.filter(
        (User.username == identifier) | (User.email == identifier.lower())
    ).first()

    if not user or not user.check_password(password):
        # Generic error message prevents username enumeration attacks
        return api_error("Invalid credentials", error_code="INVALID_CREDENTIALS", status_code=401)

    if not user.is_active:
        return api_error("Account is deactivated", error_code="ACCOUNT_DISABLED", status_code=403)

    token = generate_token(user)
    return api_response(
        data={"user": user.to_dict(), "token": token},
        message="Login successful"
    )

@auth_bp.route("/me", methods=["GET"])
@token_required
def get_current_user():
    """Retrieve details of currently authenticated user from token context."""
    return api_response(data=g.current_user.to_dict())