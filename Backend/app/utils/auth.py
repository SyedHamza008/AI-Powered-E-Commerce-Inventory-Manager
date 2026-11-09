from functools import wraps
from datetime import datetime, timezone, timedelta
import jwt
from flask import request, current_app, g
from app.extensions import db
from app.models.user import User
from app.utils.responses import api_error

def generate_token(user: User, expires_in_hours: int = 24) -> str:
    """Generate a signed JWT token containing user identity and role."""
    payload = {
        "sub": str(user.id),
        "username": user.username,
        "role": user.role,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)
    }
    return jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm="HS256")

def decode_token(token: str) -> dict:
    """Decode and verify signature and expiration of JWT token."""
    return jwt.decode(token, current_app.config["SECRET_KEY"], algorithms=["HS256"])

def token_required(f):
    """Decorator to require a valid Bearer JWT token in Authorization header."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return api_error("Missing or malformed Authorization header (Bearer token required)", error_code="UNAUTHORIZED", status_code=401)

        token = auth_header.split(" ")[1].strip()
        try:
            payload = decode_token(token)
            user_id = int(payload["sub"])
            user = db.session.get(User, user_id)
            if not user or not user.is_active:
                return api_error("User associated with this token does not exist or is inactive", error_code="UNAUTHORIZED", status_code=401)
            # Attach authenticated user to Flask's request context 'g'
            g.current_user = user
        except jwt.ExpiredSignatureError:
            return api_error("Token has expired. Please log in again.", error_code="TOKEN_EXPIRED", status_code=401)
        except (jwt.InvalidTokenError, ValueError, KeyError):
            return api_error("Invalid authentication token", error_code="INVALID_TOKEN", status_code=401)

        return f(*args, **kwargs)
    return decorated

def roles_required(*allowed_roles):
    """Decorator to enforce role-based access control (must follow @token_required)."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(g, "current_user") or not g.current_user:
                return api_error("Authentication required", error_code="UNAUTHORIZED", status_code=401)
            if g.current_user.role not in allowed_roles:
                return api_error(
                    f"Access forbidden: requires one of the following roles: {', '.join(allowed_roles)}",
                    error_code="FORBIDDEN",
                    status_code=403
                )
            return f(*args, **kwargs)
        return decorated_function
    return decorator