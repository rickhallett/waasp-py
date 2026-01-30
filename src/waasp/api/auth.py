"""API authentication utilities."""

from functools import wraps
from typing import Callable

from flask import request, jsonify

from waasp.config import get_settings


def require_api_token(f: Callable) -> Callable:
    """Decorator to require API token authentication.
    
    Checks for Bearer token in Authorization header.
    Bypasses authentication for localhost requests if no token is configured.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        settings = get_settings()
        
        # If no token configured, allow all requests (dev mode)
        if not settings.api_token:
            return f(*args, **kwargs)
        
        # Check if request is from localhost
        if request.remote_addr in ("127.0.0.1", "::1", "localhost"):
            return f(*args, **kwargs)
        
        # Check Authorization header
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid Authorization header"}), 401
        
        token = auth_header[7:]  # Remove "Bearer " prefix
        if token != settings.api_token:
            return jsonify({"error": "Invalid API token"}), 403
        
        return f(*args, **kwargs)
    
    return decorated
