"""Unit tests for models."""

import pytest

from waasp.models import Contact, TrustLevel


class TestContactModel:
    """Tests for the Contact model."""

    def test_is_allowed_property(self, app, db):
        """Test is_allowed property."""
        with app.app_context():
            blocked = Contact(sender_id="1", trust_level=TrustLevel.BLOCKED)
            limited = Contact(sender_id="2", trust_level=TrustLevel.LIMITED)
            trusted = Contact(sender_id="3", trust_level=TrustLevel.TRUSTED)
            sovereign = Contact(sender_id="4", trust_level=TrustLevel.SOVEREIGN)
            
            assert blocked.is_allowed is False
            assert limited.is_allowed is True
            assert trusted.is_allowed is True
            assert sovereign.is_allowed is True

    def test_can_trigger_actions_property(self, app, db):
        """Test can_trigger_actions property."""
        with app.app_context():
            blocked = Contact(sender_id="1", trust_level=TrustLevel.BLOCKED)
            limited = Contact(sender_id="2", trust_level=TrustLevel.LIMITED)
            trusted = Contact(sender_id="3", trust_level=TrustLevel.TRUSTED)
            sovereign = Contact(sender_id="4", trust_level=TrustLevel.SOVEREIGN)
            
            assert blocked.can_trigger_actions is False
            assert limited.can_trigger_actions is False
            assert trusted.can_trigger_actions is True
            assert sovereign.can_trigger_actions is True

    def test_is_sovereign_property(self, app, db):
        """Test is_sovereign property."""
        with app.app_context():
            trusted = Contact(sender_id="1", trust_level=TrustLevel.TRUSTED)
            sovereign = Contact(sender_id="2", trust_level=TrustLevel.SOVEREIGN)
            
            assert trusted.is_sovereign is False
            assert sovereign.is_sovereign is True


class TestTrustLevel:
    """Tests for TrustLevel enum."""

    def test_from_string_valid(self):
        """Test parsing valid trust levels."""
        assert TrustLevel.from_string("sovereign") == TrustLevel.SOVEREIGN
        assert TrustLevel.from_string("TRUSTED") == TrustLevel.TRUSTED
        assert TrustLevel.from_string("Limited") == TrustLevel.LIMITED
        assert TrustLevel.from_string("blocked") == TrustLevel.BLOCKED

    def test_from_string_invalid_defaults_to_blocked(self):
        """Test that invalid strings default to blocked."""
        assert TrustLevel.from_string("invalid") == TrustLevel.BLOCKED
        assert TrustLevel.from_string("") == TrustLevel.BLOCKED
