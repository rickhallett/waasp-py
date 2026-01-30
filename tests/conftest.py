"""Pytest fixtures and configuration."""

import pytest
from flask import Flask
from flask.testing import FlaskClient

from waasp.app import create_app
from waasp.models import db as _db, Contact, TrustLevel


@pytest.fixture(scope="session")
def app() -> Flask:
    """Create application for testing."""
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SECRET_KEY": "test-secret-key",
    })
    
    # Ensure app context and create tables
    with app.app_context():
        _db.create_all()
    
    yield app
    
    # Cleanup
    with app.app_context():
        _db.drop_all()


@pytest.fixture
def db(app: Flask):
    """Database fixture with transaction rollback."""
    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.rollback()
        _db.drop_all()


@pytest.fixture
def client(app: Flask, db) -> FlaskClient:
    """Test client fixture."""
    return app.test_client()


@pytest.fixture
def sample_contact(db) -> Contact:
    """Create a sample contact for testing."""
    contact = Contact(
        sender_id="+447375862225",
        name="Test User",
        trust_level=TrustLevel.TRUSTED,
        channel="whatsapp",
    )
    db.session.add(contact)
    db.session.commit()
    return contact


@pytest.fixture
def sovereign_contact(db) -> Contact:
    """Create a sovereign contact for testing."""
    contact = Contact(
        sender_id="+440000000000",
        name="Sovereign",
        trust_level=TrustLevel.SOVEREIGN,
    )
    db.session.add(contact)
    db.session.commit()
    return contact
