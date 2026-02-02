"""Error handling and recovery tests for WAASP."""

import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy.exc import OperationalError, IntegrityError

from waasp.models import Contact, TrustLevel, AuditAction, db
from waasp.services import WhitelistService, AuditService


class TestDatabaseErrors:
    """Tests for database error handling."""

    def test_check_handles_contact_gracefully(self, app, db):
        """Check operation should complete for known contacts."""
        with app.app_context():
            # Add a contact
            contact = Contact(
                sender_id="+447123456789",
                trust_level=TrustLevel.TRUSTED,
            )
            db.session.add(contact)
            db.session.commit()

            service = WhitelistService()
            result = service.check("+447123456789")
            assert result is not None
            assert result.allowed is True

    def test_add_contact_rollback_on_failure(self, app, db):
        """Failed add should rollback transaction cleanly."""
        with app.app_context():
            service = WhitelistService()
            
            # Add a contact
            service.add_contact(
                sender_id="+447111111111",
                trust_level=TrustLevel.TRUSTED,
            )
            
            # Try to add duplicate - should fail and rollback
            with pytest.raises(ValueError):
                service.add_contact(
                    sender_id="+447111111111",
                    trust_level=TrustLevel.TRUSTED,
                )
            
            # Database should still be usable
            result = service.check("+447111111111")
            assert result.allowed is True


class TestMalformedApiRequests:
    """Tests for malformed API request handling."""

    def test_check_missing_sender_id(self, client, db):
        """Check endpoint without sender_id should return 400 or 422."""
        response = client.post("/api/v1/check/", json={})
        assert response.status_code in (400, 422)

    def test_check_null_sender_id(self, client, db):
        """Check endpoint with null sender_id should be handled."""
        response = client.post("/api/v1/check/", json={"sender_id": None})
        assert response.status_code in (400, 422)

    def test_check_invalid_json(self, client, db):
        """Check endpoint with invalid JSON should return 400."""
        response = client.post(
            "/api/v1/check/",
            data="not valid json",
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_check_wrong_content_type(self, client, db):
        """Check endpoint with wrong content type should handle gracefully."""
        response = client.post(
            "/api/v1/check/",
            data="sender_id=test",
            content_type="application/x-www-form-urlencoded",
        )
        # Should either parse form data or return error
        assert response.status_code in (200, 400, 415)

    def test_contacts_add_missing_fields(self, client, db):
        """Add contact without required fields should fail cleanly."""
        response = client.post("/api/v1/contacts/", json={})
        assert response.status_code in (400, 422)

    def test_contacts_add_invalid_trust_level(self, client, db):
        """Add contact with invalid trust level should fail cleanly."""
        response = client.post("/api/v1/contacts/", json={
            "sender_id": "+447222222222",
            "trust_level": "invalid_level",
        })
        assert response.status_code in (400, 422)

    def test_contacts_list_negative_limit(self, client, db):
        """List contacts with negative limit should be handled."""
        response = client.get("/api/v1/contacts/?limit=-1")
        # Should either ignore, clamp, or return error
        assert response.status_code in (200, 400)

    def test_contacts_list_non_numeric_limit(self, client, db):
        """List contacts with non-numeric limit should be handled."""
        response = client.get("/api/v1/contacts/?limit=abc")
        assert response.status_code in (200, 400)


class TestServiceErrors:
    """Tests for service layer error handling."""

    def test_whitelist_service_with_no_app_context(self):
        """WhitelistService outside app context should fail gracefully."""
        service = WhitelistService()
        # Operations without app context should fail with clear error
        with pytest.raises(RuntimeError):
            service.check("+447123456789")

    def test_audit_service_with_no_app_context(self):
        """AuditService outside app context should fail gracefully."""
        service = AuditService()
        with pytest.raises(RuntimeError):
            service.log_check(
                sender_id="+447123456789",
                action=AuditAction.MESSAGE_ALLOWED,
            )


class TestGracefulDegradation:
    """Tests for graceful degradation scenarios."""

    def test_check_unknown_sender_is_blocked_not_error(self, app, db):
        """Unknown senders should be blocked, not cause errors."""
        with app.app_context():
            service = WhitelistService()
            result = service.check("+449999999999")
            
            assert result.allowed is False
            assert result.trust_level == TrustLevel.BLOCKED
            assert "Unknown sender" in result.reason

    def test_check_returns_consistent_result_format(self, app, db):
        """Check should always return consistent result format."""
        with app.app_context():
            service = WhitelistService()
            
            # Unknown sender
            result1 = service.check("+449999999998")
            assert hasattr(result1, 'allowed')
            assert hasattr(result1, 'trust_level')
            assert hasattr(result1, 'reason')
            
            # Add a contact
            service.add_contact(
                sender_id="+447555555555",
                trust_level=TrustLevel.TRUSTED,
            )
            
            # Known sender
            result2 = service.check("+447555555555")
            assert hasattr(result2, 'allowed')
            assert hasattr(result2, 'trust_level')
            assert hasattr(result2, 'reason')


class TestErrorMessages:
    """Tests for clear and helpful error messages."""

    def test_duplicate_contact_error_message(self, app, db):
        """Duplicate contact error should have clear message."""
        with app.app_context():
            service = WhitelistService()
            
            service.add_contact(
                sender_id="+447333333333",
                trust_level=TrustLevel.TRUSTED,
            )
            
            with pytest.raises(ValueError) as exc_info:
                service.add_contact(
                    sender_id="+447333333333",
                    trust_level=TrustLevel.TRUSTED,
                )
            
            error_message = str(exc_info.value).lower()
            assert "already exists" in error_message or "duplicate" in error_message

    def test_contact_not_found_on_update_raises(self, app, db):
        """Updating non-existent contact should raise ValueError."""
        with app.app_context():
            service = WhitelistService()
            
            with pytest.raises(ValueError) as exc_info:
                service.update_contact(
                    sender_id="+440000000000",
                    trust_level=TrustLevel.BLOCKED,
                )
            
            assert "not found" in str(exc_info.value).lower()

    def test_api_error_response_format(self, client, db):
        """API errors should have consistent format."""
        response = client.post("/api/v1/contacts/", json={})
        
        assert response.status_code in (400, 422)
        data = response.get_json()
        
        # Should have some error field
        assert 'error' in data or 'message' in data or 'detail' in data


class TestRecoveryScenarios:
    """Tests for recovery from error states."""

    def test_service_usable_after_error(self, app, db):
        """Service should remain usable after an error."""
        with app.app_context():
            service = WhitelistService()
            
            # Add contact then try duplicate to cause an error
            service.add_contact(
                sender_id="+447666666666",
                trust_level=TrustLevel.TRUSTED,
            )
            
            with pytest.raises(ValueError):
                service.add_contact(
                    sender_id="+447666666666",
                    trust_level=TrustLevel.TRUSTED,
                )
            
            # Service should still work
            service.add_contact(
                sender_id="+447777777777",
                trust_level=TrustLevel.TRUSTED,
            )
            
            result = service.check("+447777777777")
            assert result.allowed is True

    def test_session_usable_after_rollback(self, app, db):
        """Database session should be usable after rollback."""
        with app.app_context():
            service = WhitelistService()
            
            # Add contact
            service.add_contact(
                sender_id="+447888888888",
                trust_level=TrustLevel.TRUSTED,
            )
            
            # Try invalid operation that causes rollback
            try:
                service.add_contact(
                    sender_id="+447888888888",
                    trust_level=TrustLevel.TRUSTED,
                )
            except ValueError:
                pass
            
            # Should still be able to query
            result = service.check("+447888888888")
            assert result.allowed is True


class TestInputSanitization:
    """Tests for input sanitization on errors."""

    def test_error_doesnt_expose_sql(self, app, db):
        """Error messages shouldn't expose SQL details."""
        with app.app_context():
            service = WhitelistService()
            
            # Add contact
            service.add_contact(
                sender_id="+447999999999",
                trust_level=TrustLevel.TRUSTED,
            )
            
            # Try to add duplicate
            try:
                service.add_contact(
                    sender_id="+447999999999",
                    trust_level=TrustLevel.TRUSTED,
                )
            except ValueError as e:
                error_msg = str(e).lower()
                # Should not contain SQL keywords
                assert "insert into" not in error_msg
                assert "select" not in error_msg

    def test_error_doesnt_expose_paths(self, client, db):
        """Error responses shouldn't expose filesystem paths."""
        # Trigger an error
        response = client.post("/api/v1/contacts/", json={})
        
        if response.status_code >= 400:
            data = response.get_json() or {}
            error_text = str(data).lower()
            
            # Should not contain paths
            assert "/home/" not in error_text
            assert "/var/" not in error_text
