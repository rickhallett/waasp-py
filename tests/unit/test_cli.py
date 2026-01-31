"""CLI command tests for WAASP."""

import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

from waasp.cli import main
from waasp.models import Contact, TrustLevel


@pytest.fixture
def runner():
    """Click test runner."""
    return CliRunner()


@pytest.fixture
def cli_app(app, db):
    """App configured for CLI testing with tables created."""
    with app.app_context():
        db.create_all()
    return app


class TestCheckCommand:
    """Tests for the 'check' command."""

    def test_check_unknown_sender_blocked(self, runner, cli_app):
        """Unknown senders should be blocked."""
        with patch("waasp.app.create_app", return_value=cli_app):
            result = runner.invoke(main, ["check", "+447999999999"])
            assert result.exit_code == 0
            assert "BLOCKED" in result.output
            assert "Unknown sender" in result.output

    def test_check_trusted_sender_allowed(self, runner, cli_app, db):
        """Trusted contacts should be allowed."""
        with cli_app.app_context():
            contact = Contact(
                sender_id="+447123456789",
                name="Test User",
                trust_level=TrustLevel.TRUSTED,
            )
            db.session.add(contact)
            db.session.commit()
            sender_id = contact.sender_id

        with patch("waasp.app.create_app", return_value=cli_app):
            result = runner.invoke(main, ["check", sender_id])
            assert result.exit_code == 0
            assert "ALLOWED" in result.output
            assert "trusted" in result.output

    def test_check_sovereign_sender_allowed(self, runner, cli_app, db):
        """Sovereign contacts should be allowed."""
        with cli_app.app_context():
            contact = Contact(
                sender_id="+440000000000",
                name="Sovereign",
                trust_level=TrustLevel.SOVEREIGN,
            )
            db.session.add(contact)
            db.session.commit()
            sender_id = contact.sender_id

        with patch("waasp.app.create_app", return_value=cli_app):
            result = runner.invoke(main, ["check", sender_id])
            assert result.exit_code == 0
            assert "ALLOWED" in result.output
            assert "sovereign" in result.output

    def test_check_with_channel_scope(self, runner, cli_app, db):
        """Check respects channel scope."""
        with cli_app.app_context():
            contact = Contact(
                sender_id="+447111111111",
                trust_level=TrustLevel.TRUSTED,
                channel="whatsapp",
            )
            db.session.add(contact)
            db.session.commit()
            sender_id = contact.sender_id

        with patch("waasp.app.create_app", return_value=cli_app):
            result = runner.invoke(
                main, ["check", sender_id, "-c", "whatsapp"]
            )
            assert result.exit_code == 0
            assert "ALLOWED" in result.output

    def test_check_blocked_contact(self, runner, cli_app, db):
        """Blocked contacts should be denied."""
        with cli_app.app_context():
            blocked = Contact(
                sender_id="+447111111111",
                name="Bad Actor",
                trust_level=TrustLevel.BLOCKED,
            )
            db.session.add(blocked)
            db.session.commit()
            sender_id = blocked.sender_id

        with patch("waasp.app.create_app", return_value=cli_app):
            result = runner.invoke(main, ["check", sender_id])
            assert result.exit_code == 0
            assert "BLOCKED" in result.output

    def test_check_displays_contact_name(self, runner, cli_app, db):
        """Check should display contact name if available."""
        with cli_app.app_context():
            contact = Contact(
                sender_id="+447222222222",
                name="Named Contact",
                trust_level=TrustLevel.TRUSTED,
            )
            db.session.add(contact)
            db.session.commit()
            sender_id = contact.sender_id

        with patch("waasp.app.create_app", return_value=cli_app):
            result = runner.invoke(main, ["check", sender_id])
            assert "Named Contact" in result.output


class TestAddCommand:
    """Tests for the 'add' command."""

    def test_add_contact_success(self, runner, cli_app, db):
        """Successfully add a new contact."""
        with patch("waasp.app.create_app", return_value=cli_app):
            result = runner.invoke(
                main, 
                ["add", "+447222222222", "-n", "New User", "-t", "trusted"]
            )
            assert result.exit_code == 0
            assert "Added" in result.output
            assert "+447222222222" in result.output

        # Verify in database
        with cli_app.app_context():
            contact = db.session.query(Contact).filter_by(
                sender_id="+447222222222"
            ).first()
            assert contact is not None
            assert contact.name == "New User"
            assert contact.trust_level == TrustLevel.TRUSTED

    def test_add_contact_with_channel(self, runner, cli_app, db):
        """Add contact with channel scope."""
        with patch("waasp.app.create_app", return_value=cli_app):
            result = runner.invoke(
                main,
                ["add", "+447333333333", "-c", "telegram", "-t", "limited"]
            )
            assert result.exit_code == 0

        with cli_app.app_context():
            contact = db.session.query(Contact).filter_by(
                sender_id="+447333333333"
            ).first()
            assert contact.channel == "telegram"
            assert contact.trust_level == TrustLevel.LIMITED

    def test_add_duplicate_contact_fails(self, runner, cli_app, db):
        """Cannot add duplicate contact."""
        with cli_app.app_context():
            contact = Contact(
                sender_id="+447444444444",
                trust_level=TrustLevel.TRUSTED,
                channel="whatsapp",
            )
            db.session.add(contact)
            db.session.commit()
            sender_id = contact.sender_id
            channel = contact.channel

        with patch("waasp.app.create_app", return_value=cli_app):
            result = runner.invoke(
                main, 
                ["add", sender_id, "-c", channel]
            )
            assert result.exit_code == 1
            assert "already exists" in result.output.lower()

    def test_add_sovereign_contact(self, runner, cli_app, db):
        """Add sovereign-level contact."""
        with patch("waasp.app.create_app", return_value=cli_app):
            result = runner.invoke(
                main,
                ["add", "+440001112222", "-n", "Root User", "-t", "sovereign"]
            )
            assert result.exit_code == 0
            assert "sovereign" in result.output

    def test_add_blocked_contact(self, runner, cli_app, db):
        """Add explicitly blocked contact."""
        with patch("waasp.app.create_app", return_value=cli_app):
            result = runner.invoke(
                main,
                ["add", "+449998887777", "-n", "Banned User", "-t", "blocked"]
            )
            assert result.exit_code == 0
            assert "blocked" in result.output


class TestListCommand:
    """Tests for the 'list' command."""

    def test_list_empty(self, runner, cli_app, db):
        """List with no contacts."""
        with patch("waasp.app.create_app", return_value=cli_app):
            result = runner.invoke(main, ["list"])
            assert result.exit_code == 0
            assert "No contacts found" in result.output

    def test_list_all_contacts(self, runner, cli_app, db):
        """List all contacts."""
        with cli_app.app_context():
            trusted = Contact(
                sender_id="+447111111111",
                name="Trusted",
                trust_level=TrustLevel.TRUSTED,
            )
            sovereign = Contact(
                sender_id="+447222222222",
                name="Sovereign",
                trust_level=TrustLevel.SOVEREIGN,
            )
            db.session.add_all([trusted, sovereign])
            db.session.commit()

        with patch("waasp.app.create_app", return_value=cli_app):
            result = runner.invoke(main, ["list"])
            assert result.exit_code == 0
            assert "+447111111111" in result.output
            assert "+447222222222" in result.output

    def test_list_filter_by_trust(self, runner, cli_app, db):
        """Filter by trust level."""
        with cli_app.app_context():
            trusted = Contact(
                sender_id="+447111111111",
                trust_level=TrustLevel.TRUSTED,
            )
            sovereign = Contact(
                sender_id="+447222222222",
                trust_level=TrustLevel.SOVEREIGN,
            )
            db.session.add_all([trusted, sovereign])
            db.session.commit()

        with patch("waasp.app.create_app", return_value=cli_app):
            result = runner.invoke(main, ["list", "-t", "trusted"])
            assert result.exit_code == 0
            assert "+447111111111" in result.output
            assert "+447222222222" not in result.output

    def test_list_filter_by_channel(self, runner, cli_app, db):
        """Filter by channel."""
        with cli_app.app_context():
            contact = Contact(
                sender_id="+447333333333",
                trust_level=TrustLevel.TRUSTED,
                channel="whatsapp",
            )
            db.session.add(contact)
            db.session.commit()

        with patch("waasp.app.create_app", return_value=cli_app):
            result = runner.invoke(main, ["list", "-c", "whatsapp"])
            assert result.exit_code == 0
            assert "+447333333333" in result.output

    def test_list_shows_names(self, runner, cli_app, db):
        """List shows contact names."""
        with cli_app.app_context():
            contact = Contact(
                sender_id="+447444444444",
                name="Test User",
                trust_level=TrustLevel.TRUSTED,
            )
            db.session.add(contact)
            db.session.commit()

        with patch("waasp.app.create_app", return_value=cli_app):
            result = runner.invoke(main, ["list"])
            assert "Test User" in result.output


class TestRemoveCommand:
    """Tests for the 'remove' command."""

    def test_remove_contact_success(self, runner, cli_app, db):
        """Successfully remove a contact."""
        with cli_app.app_context():
            contact = Contact(
                sender_id="+447555555555",
                trust_level=TrustLevel.TRUSTED,
            )
            db.session.add(contact)
            db.session.commit()
            sender_id = contact.sender_id

        with patch("waasp.app.create_app", return_value=cli_app):
            result = runner.invoke(main, ["remove", sender_id])
            assert result.exit_code == 0
            assert "Removed" in result.output

        # Verify removed from database
        with cli_app.app_context():
            contact = db.session.query(Contact).filter_by(
                sender_id=sender_id
            ).first()
            assert contact is None

    def test_remove_nonexistent_contact(self, runner, cli_app, db):
        """Cannot remove non-existent contact."""
        with patch("waasp.app.create_app", return_value=cli_app):
            result = runner.invoke(main, ["remove", "+440000000001"])
            assert result.exit_code == 1
            assert "not found" in result.output.lower()

    def test_remove_with_channel_scope(self, runner, cli_app, db):
        """Remove contact with channel scope."""
        with cli_app.app_context():
            contact = Contact(
                sender_id="+447666666666",
                trust_level=TrustLevel.TRUSTED,
                channel="signal",
            )
            db.session.add(contact)
            db.session.commit()

        with patch("waasp.app.create_app", return_value=cli_app):
            result = runner.invoke(
                main, ["remove", "+447666666666", "-c", "signal"]
            )
            assert result.exit_code == 0
            assert "Removed" in result.output


class TestMainGroup:
    """Tests for the main CLI group."""

    def test_help_displays(self, runner):
        """Main help text displays."""
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "WAASP" in result.output
        assert "check" in result.output
        assert "add" in result.output
        assert "list" in result.output
        assert "remove" in result.output
        assert "serve" in result.output

    def test_invalid_command(self, runner):
        """Invalid command shows error."""
        result = runner.invoke(main, ["invalid"])
        assert result.exit_code != 0

    def test_check_help(self, runner):
        """Check command help."""
        result = runner.invoke(main, ["check", "--help"])
        assert result.exit_code == 0
        assert "sender_id" in result.output.lower()

    def test_add_help(self, runner):
        """Add command help."""
        result = runner.invoke(main, ["add", "--help"])
        assert result.exit_code == 0
        assert "--trust" in result.output or "-t" in result.output
