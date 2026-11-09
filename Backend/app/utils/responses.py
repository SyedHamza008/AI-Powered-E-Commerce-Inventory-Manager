from flask import jsonify

def api_response(data=None, message=None, status_code=200):
    """Generate a standardized success JSON response."""
    payload = {
        "success": True,
        "data": data
    }
    if message:
        payload["message"] = message
    return jsonify(payload), status_code

def api_error(message, error_code="BAD_REQUEST", status_code=400, details=None):
    """Generate a standardized error JSON response."""
    payload = {
        "success": False,
        "error": {
            "code": error_code,
            "message": message
        }
    }
    if details:
        payload["error"]["details"] = details
    return jsonify(payload), status_code