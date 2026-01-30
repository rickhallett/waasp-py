"""Integration tests for API endpoints."""

import pytest


class TestHealthEndpoint:
    """Tests for the health check endpoint."""

    def test_health_returns_200(self, client):
        """Health endpoint should return 200."""
        response = client.get("/health")
        
        assert response.status_code == 200
        assert response.json["status"] == "healthy"


class TestCheckEndpoint:
    """Tests for the check endpoint."""

    def test_check_unknown_sender(self, client):
        """Check endpoint should block unknown senders."""
        response = client.post("/api/v1/check/", json={
            "sender_id": "+449999999999",
        })
        
        assert response.status_code == 200
        assert response.json["allowed"] is False
        assert response.json["trust"] == "blocked"

    def test_check_with_channel(self, client, sample_contact):
        """Check endpoint should handle channel parameter."""
        response = client.post("/api/v1/check/", json={
            "sender_id": sample_contact.sender_id,
            "channel": sample_contact.channel,
        })
        
        assert response.status_code == 200
        assert response.json["allowed"] is True
        assert response.json["trust"] == "trusted"

    def test_check_get_endpoint(self, client, sample_contact):
        """GET check endpoint should work."""
        response = client.get(
            f"/api/v1/check/{sample_contact.sender_id}?channel={sample_contact.channel}"
        )
        
        assert response.status_code == 200
        assert response.json["allowed"] is True


class TestContactsEndpoint:
    """Tests for the contacts endpoints."""

    def test_list_contacts(self, client, sample_contact):
        """Should list all contacts."""
        response = client.get("/api/v1/contacts/")
        
        assert response.status_code == 200
        assert response.json["total"] >= 1
        assert len(response.json["contacts"]) >= 1

    def test_create_contact(self, client):
        """Should create a new contact."""
        response = client.post("/api/v1/contacts/", json={
            "sender_id": "+447777777777",
            "name": "New Contact",
            "trust_level": "trusted",
        })
        
        assert response.status_code == 201
        assert response.json["sender_id"] == "+447777777777"
        assert response.json["name"] == "New Contact"

    def test_create_duplicate_contact_fails(self, client, sample_contact):
        """Should fail when creating duplicate contact."""
        response = client.post("/api/v1/contacts/", json={
            "sender_id": sample_contact.sender_id,
            "channel": sample_contact.channel,
        })
        
        assert response.status_code == 409  # Conflict

    def test_update_contact(self, client, sample_contact):
        """Should update a contact."""
        response = client.patch(
            f"/api/v1/contacts/{sample_contact.sender_id}?channel={sample_contact.channel}",
            json={"trust_level": "sovereign"},
        )
        
        assert response.status_code == 200
        assert response.json["trust_level"] == "sovereign"

    def test_delete_contact(self, client, sample_contact):
        """Should delete a contact."""
        response = client.delete(
            f"/api/v1/contacts/{sample_contact.sender_id}?channel={sample_contact.channel}"
        )
        
        assert response.status_code == 204


class TestAuditEndpoint:
    """Tests for the audit endpoints."""

    def test_list_audit_logs(self, client, sample_contact):
        """Should list audit logs after check."""
        # First, trigger a check to create an audit log
        client.post("/api/v1/check/", json={
            "sender_id": sample_contact.sender_id,
            "channel": sample_contact.channel,
        })
        
        # Then list audit logs
        response = client.get("/api/v1/audit/")
        
        assert response.status_code == 200
        assert response.json["count"] >= 1

    def test_get_audit_stats(self, client):
        """Should return audit statistics."""
        response = client.get("/api/v1/audit/stats")
        
        assert response.status_code == 200
        assert "total_entries" in response.json
        assert "by_action" in response.json
