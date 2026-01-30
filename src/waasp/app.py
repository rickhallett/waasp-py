"""Flask application factory."""

from flask import Flask
from flask_migrate import Migrate

from waasp.config import get_settings
from waasp.models import db


migrate = Migrate()


def create_app(config_override: dict | None = None) -> Flask:
    """Create and configure the Flask application.
    
    Args:
        config_override: Optional config values for testing
        
    Returns:
        Configured Flask application
    """
    settings = get_settings()
    
    app = Flask(__name__)
    
    # Core configuration
    app.config.update(
        SECRET_KEY=settings.secret_key,
        SQLALCHEMY_DATABASE_URI=settings.database_url,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ENGINE_OPTIONS={
            "pool_pre_ping": True,
        },
    )
    
    # Apply any test overrides
    if config_override:
        app.config.update(config_override)
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Register blueprints
    from waasp.api import api_bp
    app.register_blueprint(api_bp, url_prefix=settings.api_prefix)
    
    # Health check endpoint
    @app.get("/health")
    def health_check():
        return {"status": "healthy", "version": "0.1.0"}
    
    return app
