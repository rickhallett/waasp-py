"""Contacts API endpoints."""

from flask import Blueprint, request, jsonify
from pydantic import ValidationError

from waasp.models import TrustLevel
from waasp.schemas import ContactCreate, ContactUpdate, ContactResponse, ContactListResponse
from waasp.services import WhitelistService
from waasp.api.auth import require_api_token


contacts_bp = Blueprint("contacts", __name__)


@contacts_bp.get("/")
@require_api_token
def list_contacts():
    """List all contacts in the whitelist.
    
    Query params:
        trust_level: Filter by trust level
        channel: Filter by channel
    """
    service = WhitelistService()
    
    trust_level = request.args.get("trust_level")
    channel = request.args.get("channel")
    
    if trust_level:
        try:
            trust_level = TrustLevel(trust_level.lower())
        except ValueError:
            return jsonify({"error": f"Invalid trust level: {trust_level}"}), 400
    
    contacts = service.list_contacts(trust_level=trust_level, channel=channel)
    
    response = ContactListResponse(
        contacts=[ContactResponse.model_validate(c) for c in contacts],
        total=len(contacts),
    )
    return jsonify(response.model_dump())


@contacts_bp.post("/")
@require_api_token
def create_contact():
    """Add a new contact to the whitelist."""
    service = WhitelistService()
    
    try:
        data = ContactCreate.model_validate(request.get_json())
    except ValidationError as e:
        return jsonify({"error": "Validation failed", "details": e.errors()}), 400
    
    try:
        contact = service.add_contact(
            sender_id=data.sender_id,
            trust_level=TrustLevel(data.trust_level),
            channel=data.channel,
            name=data.name,
            notes=data.notes,
        )
    except ValueError as e:
        return jsonify({"error": str(e)}), 409  # Conflict
    
    response = ContactResponse.model_validate(contact)
    return jsonify(response.model_dump()), 201


@contacts_bp.get("/<sender_id>")
@require_api_token
def get_contact(sender_id: str):
    """Get a specific contact by sender_id."""
    service = WhitelistService()
    channel = request.args.get("channel")
    
    contact = service._find_contact(sender_id, channel)
    if not contact:
        return jsonify({"error": "Contact not found"}), 404
    
    response = ContactResponse.model_validate(contact)
    return jsonify(response.model_dump())


@contacts_bp.patch("/<sender_id>")
@require_api_token
def update_contact(sender_id: str):
    """Update an existing contact."""
    service = WhitelistService()
    channel = request.args.get("channel")
    
    try:
        data = ContactUpdate.model_validate(request.get_json())
    except ValidationError as e:
        return jsonify({"error": "Validation failed", "details": e.errors()}), 400
    
    trust_level = None
    if data.trust_level:
        trust_level = TrustLevel(data.trust_level)
    
    try:
        contact = service.update_contact(
            sender_id=sender_id,
            channel=channel,
            trust_level=trust_level,
            name=data.name,
            notes=data.notes,
        )
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    
    response = ContactResponse.model_validate(contact)
    return jsonify(response.model_dump())


@contacts_bp.delete("/<sender_id>")
@require_api_token
def delete_contact(sender_id: str):
    """Remove a contact from the whitelist."""
    service = WhitelistService()
    channel = request.args.get("channel")
    
    removed = service.remove_contact(sender_id, channel)
    if not removed:
        return jsonify({"error": "Contact not found"}), 404
    
    return "", 204
