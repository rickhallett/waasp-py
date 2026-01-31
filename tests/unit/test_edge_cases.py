"""Edge case tests for WAASP - security and input validation."""

import pytest
from waasp.models import Contact, TrustLevel
from waasp.services import WhitelistService


class TestMalformedSenderIds:
    """Tests for malformed sender ID inputs."""

    def test_empty_sender_id_blocked(self, app, db):
        """Empty sender_id should be blocked."""
        with app.app_context():
            service = WhitelistService()
            result = service.check("")
            assert result.allowed is False
            assert "Unknown sender" in result.reason

    def test_whitespace_only_sender_id(self, app, db):
        """Whitespace-only sender_id should be blocked."""
        with app.app_context():
            service = WhitelistService()
            result = service.check("   ")
            assert result.allowed is False

    def test_very_short_sender_id(self, app, db):
        """Single character sender_id should be handled."""
        with app.app_context():
            service = WhitelistService()
            # Add a single-char contact
            contact = service.add_contact(
                sender_id="X",
                trust_level=TrustLevel.TRUSTED,
            )
            result = service.check("X")
            assert result.allowed is True

    def test_sender_id_with_newlines(self, app, db):
        """Sender ID with newlines should be handled safely."""
        with app.app_context():
            service = WhitelistService()
            malicious = "+44123\n456789"
            result = service.check(malicious)
            assert result.allowed is False

    def test_sender_id_with_tabs(self, app, db):
        """Sender ID with tabs should be handled safely."""
        with app.app_context():
            service = WhitelistService()
            result = service.check("+44\t123456")
            assert result.allowed is False


class TestUnicodeHandling:
    """Tests for unicode character handling."""

    def test_unicode_in_name(self, app, db):
        """Unicode characters in name should work."""
        with app.app_context():
            service = WhitelistService()
            contact = service.add_contact(
                sender_id="+447999888777",
                name="José García 日本語 🎉",
                trust_level=TrustLevel.TRUSTED,
            )
            assert contact.name == "José García 日本語 🎉"

    def test_emoji_in_sender_id(self, app, db):
        """Emoji in sender_id should be handled (common in social platforms)."""
        with app.app_context():
            service = WhitelistService()
            # Some platforms use emoji identifiers
            contact = service.add_contact(
                sender_id="user🎯123",
                name="Emoji User",
                trust_level=TrustLevel.TRUSTED,
            )
            result = service.check("user🎯123")
            assert result.allowed is True

    def test_rtl_characters(self, app, db):
        """Right-to-left text should be handled safely."""
        with app.app_context():
            service = WhitelistService()
            # Arabic/Hebrew text
            contact = service.add_contact(
                sender_id="+966123456789",
                name="محمد العربي",
                trust_level=TrustLevel.TRUSTED,
            )
            assert contact is not None

    def test_zero_width_characters(self, app, db):
        """Zero-width characters should not cause issues."""
        with app.app_context():
            service = WhitelistService()
            # Zero-width space and joiner
            suspicious = "+44123\u200b\u200c\u200d456"
            result = service.check(suspicious)
            assert result.allowed is False

    def test_combining_characters(self, app, db):
        """Combining characters should be handled."""
        with app.app_context():
            service = WhitelistService()
            # Combining acute accent
            contact = service.add_contact(
                sender_id="+33123456789",
                name="Café",  # Normal é
                trust_level=TrustLevel.TRUSTED,
            )
            assert contact is not None


class TestSqlInjectionPrevention:
    """Tests to verify SQL injection prevention."""

    def test_sql_injection_in_sender_id(self, app, db):
        """SQL injection in sender_id should be safely handled."""
        with app.app_context():
            service = WhitelistService()
            injections = [
                "'; DROP TABLE contacts; --",
                "1' OR '1'='1",
                "1; DELETE FROM contacts WHERE 1=1; --",
                "' UNION SELECT * FROM users --",
                "admin'--",
            ]
            for injection in injections:
                result = service.check(injection)
                # Should safely return blocked, not crash or drop tables
                assert result.allowed is False
                # Verify table still exists
                count = db.session.query(Contact).count()
                assert count >= 0

    def test_sql_injection_in_name(self, app, db):
        """SQL injection in name field should be safely handled."""
        with app.app_context():
            service = WhitelistService()
            contact = service.add_contact(
                sender_id="+447777777777",
                name="Robert'); DROP TABLE contacts; --",
                trust_level=TrustLevel.TRUSTED,
            )
            # Should work without executing SQL
            assert contact is not None
            assert "DROP TABLE" in contact.name

    def test_sql_injection_in_channel(self, app, db):
        """SQL injection in channel field should be safely handled."""
        with app.app_context():
            service = WhitelistService()
            contact = service.add_contact(
                sender_id="+447666666666",
                channel="'; DELETE FROM contacts; --",
                trust_level=TrustLevel.TRUSTED,
            )
            assert contact is not None


class TestVeryLongStrings:
    """Tests for handling very long input strings."""

    def test_very_long_sender_id(self, app, db):
        """Very long sender_id should be handled."""
        with app.app_context():
            service = WhitelistService()
            long_id = "+" + "1" * 10000
            result = service.check(long_id)
            assert result.allowed is False

    def test_very_long_name(self, app, db):
        """Very long name should be handled."""
        with app.app_context():
            service = WhitelistService()
            long_name = "A" * 10000
            contact = service.add_contact(
                sender_id="+447555555555",
                name=long_name,
                trust_level=TrustLevel.TRUSTED,
            )
            # Should either truncate or store full name
            assert contact is not None

    def test_very_long_channel(self, app, db):
        """Very long channel name should be handled."""
        with app.app_context():
            service = WhitelistService()
            long_channel = "x" * 10000
            contact = service.add_contact(
                sender_id="+447444444444",
                channel=long_channel,
                trust_level=TrustLevel.TRUSTED,
            )
            assert contact is not None


class TestSpecialCharacters:
    """Tests for special character handling."""

    def test_null_bytes(self, app, db):
        """Null bytes should be handled safely."""
        with app.app_context():
            service = WhitelistService()
            with_null = "+44123\x00456"
            result = service.check(with_null)
            assert result.allowed is False

    def test_backslashes(self, app, db):
        """Backslashes should be handled safely."""
        with app.app_context():
            service = WhitelistService()
            contact = service.add_contact(
                sender_id="+447333333333",
                name="User\\nName\\x00",
                trust_level=TrustLevel.TRUSTED,
            )
            assert contact is not None

    def test_quotes(self, app, db):
        """Various quote types should be handled safely."""
        with app.app_context():
            service = WhitelistService()
            contact = service.add_contact(
                sender_id="+447222222222",
                name="O'Reilly \"Books\" `test`",
                trust_level=TrustLevel.TRUSTED,
            )
            assert contact is not None
            assert "'" in contact.name
            assert '"' in contact.name

    def test_html_special_chars(self, app, db):
        """HTML special characters should be stored safely."""
        with app.app_context():
            service = WhitelistService()
            contact = service.add_contact(
                sender_id="+447111111111",
                name="<script>alert('xss')</script>",
                trust_level=TrustLevel.TRUSTED,
            )
            assert contact is not None
            assert "<script>" in contact.name


class TestBoundaryConditions:
    """Tests for boundary conditions."""

    def test_trust_level_boundaries(self, app, db):
        """All trust levels should work correctly."""
        with app.app_context():
            service = WhitelistService()
            
            for level in TrustLevel:
                contact = service.add_contact(
                    sender_id=f"+44{level.value}00000",
                    trust_level=level,
                )
                result = service.check(contact.sender_id)
                
                if level == TrustLevel.BLOCKED:
                    assert result.allowed is False
                else:
                    assert result.allowed is True

    def test_channel_none_vs_empty(self, app, db):
        """None channel vs empty string channel should be distinct."""
        with app.app_context():
            service = WhitelistService()
            
            # None channel (global)
            global_contact = service.add_contact(
                sender_id="+447000000001",
                trust_level=TrustLevel.TRUSTED,
                channel=None,
            )
            
            # Ensure we can check both with and without channel
            result1 = service.check("+447000000001")
            assert result1.allowed is True
            
            result2 = service.check("+447000000001", channel="whatsapp")
            assert result2.allowed is True  # Falls back to global

    def test_case_sensitivity(self, app, db):
        """Channel names should be case-sensitive or case-insensitive consistently."""
        with app.app_context():
            service = WhitelistService()
            
            contact = service.add_contact(
                sender_id="+447000000002",
                trust_level=TrustLevel.TRUSTED,
                channel="WhatsApp",
            )
            
            # Check with same case
            result = service.check("+447000000002", channel="WhatsApp")
            assert result.allowed is True
            
            # Check with different case (depends on implementation)
            result_lower = service.check("+447000000002", channel="whatsapp")
            # Either should work or fall back to global


class TestNullAndNoneHandling:
    """Tests for None/null value handling."""

    def test_none_name(self, app, db):
        """None name should be handled."""
        with app.app_context():
            service = WhitelistService()
            contact = service.add_contact(
                sender_id="+447888888888",
                name=None,
                trust_level=TrustLevel.TRUSTED,
            )
            assert contact.name is None

    def test_none_notes(self, app, db):
        """None notes should be handled."""
        with app.app_context():
            service = WhitelistService()
            contact = service.add_contact(
                sender_id="+447999999999",
                trust_level=TrustLevel.TRUSTED,
            )
            assert contact.notes is None


class TestConcurrentModification:
    """Tests for concurrent modification edge cases."""

    def test_double_add_same_contact(self, app, db):
        """Adding same contact twice should fail gracefully."""
        with app.app_context():
            service = WhitelistService()
            
            service.add_contact(
                sender_id="+447000000003",
                trust_level=TrustLevel.TRUSTED,
            )
            
            with pytest.raises(ValueError, match="already exists"):
                service.add_contact(
                    sender_id="+447000000003",
                    trust_level=TrustLevel.TRUSTED,
                )

    def test_remove_after_remove(self, app, db):
        """Removing an already removed contact should be safe."""
        with app.app_context():
            service = WhitelistService()
            
            service.add_contact(
                sender_id="+447000000004",
                trust_level=TrustLevel.TRUSTED,
            )
            
            # First remove
            assert service.remove_contact("+447000000004") is True
            
            # Second remove - should return False, not crash
            assert service.remove_contact("+447000000004") is False
