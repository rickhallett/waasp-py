"""API blueprints and endpoints."""

from flask import Blueprint
from flask_smorest import Api

from waasp.api.contacts import contacts_bp
from waasp.api.check import check_bp
from waasp.api.audit import audit_bp


# Create main API blueprint
api_bp = Blueprint("api", __name__)


def register_api(app):
    """Register API with smorest for OpenAPI docs."""
    app.config.update({
        "API_TITLE": "WAASP API",
        "API_VERSION": "v1",
        "OPENAPI_VERSION": "3.0.3",
        "OPENAPI_URL_PREFIX": "/",
        "OPENAPI_SWAGGER_UI_PATH": "/docs",
        "OPENAPI_SWAGGER_UI_URL": "https://cdn.jsdelivr.net/npm/swagger-ui-dist/",
    })
    
    api = Api(app)
    api.register_blueprint(contacts_bp)
    api.register_blueprint(check_bp)
    api.register_blueprint(audit_bp)
    
    return api


# Simple registration without smorest for now
api_bp.register_blueprint(contacts_bp, url_prefix="/contacts")
api_bp.register_blueprint(check_bp, url_prefix="/check")
api_bp.register_blueprint(audit_bp, url_prefix="/audit")

__all__ = ["api_bp", "register_api"]
