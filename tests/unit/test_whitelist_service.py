"""Unit tests for WhitelistService."""

import pytest

from waasp.models import Contact, TrustLevel
from waasp.services import WhitelistService


class TestWhitelistCheck:
    """Tests for the check() method."""

    def test_unknown_sender_is_blocked(self, app, db):
        """Unknown senders should be blocked by default."""
        with app.app_context():
            service = WhitelistService()
            result = service.check(sender_id="+449999999999")
            
            assert result.allowed is False
            assert result.trust_level == TrustLevel.BLOCKED
            assert result.contact is None
            assert "not in whitelist" in result.reason.lower()

    def test_trusted_sender_is_allowed(self, app, db, sample_contact):
        """Trusted contacts should be allowed."""
        with app.app_context():
            service = WhitelistService()
            result = service.check(
                sender_id=sample_contact.sender_id,
                channel=sample_contact.channel,
            )
            
            assert result.allowed is True
            assert result.trust_level == TrustLevel.TRUSTED
            assert result.contact is not None
            assert result.contact.name == "Test User"

    def test_sovereign_sender_is_allowed(self, app, db, sovereign_contact):
        """Sovereign contacts should be allowed."""
        with app.app_context():
            service = WhitelistService()
            result = service.check(sender_id=sovereign_contact.sender_id)
            
            assert result.allowed is True
            assert result.trust_level == TrustLevel.SOVEREIGN

    def test_blocked_contact_is_blocked(self, app, db):
        """Explicitly blocked contacts should be blocked."""
        with app.app_context():
            contact = Contact(
                sender_id="+441111111111",
                trust_level=TrustLevel.BLOCKED,
            )
            db.session.add(contact)
            db.session.commit()
            
            service = WhitelistService()
            result = service.check(sender_id="+441111111111")
            
            assert result.allowed is False
            assert result.trust_level == TrustLevel.BLOCKED
            assert result.contact is not None  # Contact exists but is blocked

    def test_limited_contact_is_allowed_but_limited(self, app, db):
        """Limited contacts should be allowed but flagged."""
        with app.app_context():
            contact = Contact(
                sender_id="+442222222222",
                trust_level=TrustLevel.LIMITED,
            )
            db.session.add(contact)
            db.session.commit()
            
            service = WhitelistService()
            result = service.check(sender_id="+442222222222")
            
            assert result.allowed is True  # Still allowed to message
            assert result.trust_level == TrustLevel.LIMITED

    def test_channel_specific_lookup(self, app, db):
        """Channel-specific contacts should take priority."""
        with app.app_context():
            # Create global contact (blocked)
            global_contact = Contact(
                sender_id="+443333333333",
                trust_level=TrustLevel.BLOCKED,
                channel=None,
            )
            # Create channel-specific contact (trusted)
            channel_contact = Contact(
                sender_id="+443333333333",
                trust_level=TrustLevel.TRUSTED,
                channel="telegram",
            )
            db.session.add_all([global_contact, channel_contact])
            db.session.commit()
            
            service = WhitelistService()
            
            # Without channel, should use global (blocked)
            result = service.check(sender_id="+443333333333")
            assert result.trust_level == TrustLevel.BLOCKED
            
            # With channel, should use channel-specific (trusted)
            result = service.check(sender_id="+443333333333", channel="telegram")
            assert result.trust_level == TrustLevel.TRUSTED


class TestWhitelistAddContact:
    """Tests for the add_contact() method."""

    def test_add_contact_success(self, app, db):
        """Should successfully add a new contact."""
        with app.app_context():
            service = WhitelistService()
            contact = service.add_contact(
                sender_id="+445555555555",
                name="New Contact",
                trust_level=TrustLevel.TRUSTED,
            )
            
            assert contact.id is not None
            assert contact.sender_id == "+445555555555"
            assert contact.name == "New Contact"
            assert contact.trust_level == TrustLevel.TRUSTED

    def test_add_duplicate_contact_fails(self, app, db, sample_contact):
        """Should fail when adding a duplicate contact."""
        with app.app_context():
            service = WhitelistService()
            
            with pytest.raises(ValueError) as exc:
                service.add_contact(
                    sender_id=sample_contact.sender_id,
                    channel=sample_contact.channel,
                )
            
            assert "already exists" in str(exc.value).lower()


class TestWhitelistUpdateContact:
    """Tests for the update_contact() method."""

    def test_update_trust_level(self, app, db, sample_contact):
        """Should update contact trust level."""
        with app.app_context():
            service = WhitelistService()
            contact = service.update_contact(
                sender_id=sample_contact.sender_id,
                channel=sample_contact.channel,
                trust_level=TrustLevel.SOVEREIGN,
            )
            
            assert contact.trust_level == TrustLevel.SOVEREIGN

    def test_update_nonexistent_contact_fails(self, app, db):
        """Should fail when updating nonexistent contact."""
        with app.app_context():
            service = WhitelistService()
            
            with pytest.raises(ValueError) as exc:
                service.update_contact(
                    sender_id="+449999999999",
                    trust_level=TrustLevel.TRUSTED,
                )
            
            assert "not found" in str(exc.value).lower()


class TestWhitelistRemoveContact:
    """Tests for the remove_contact() method."""

    def test_remove_contact_success(self, app, db, sample_contact):
        """Should successfully remove a contact."""
        with app.app_context():
            service = WhitelistService()
            result = service.remove_contact(
                sender_id=sample_contact.sender_id,
                channel=sample_contact.channel,
            )
            
            assert result is True
            
            # Verify contact is gone
            check_result = service.check(
                sender_id=sample_contact.sender_id,
                channel=sample_contact.channel,
            )
            assert check_result.contact is None

    def test_remove_nonexistent_contact(self, app, db):
        """Should return False when removing nonexistent contact."""
        with app.app_context():
            service = WhitelistService()
            result = service.remove_contact(sender_id="+449999999999")
            
            assert result is False
