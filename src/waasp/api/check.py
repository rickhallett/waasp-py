"""Check API endpoint - the core whitelist verification."""

from flask import Blueprint, request, jsonify
from pydantic import ValidationError

from waasp.schemas import CheckRequest, CheckResponse
from waasp.services import WhitelistService


check_bp = Blueprint("check", __name__)


@check_bp.post("/")
def check_sender():
    """Check if a sender is allowed to interact with the agent.
    
    This is the main endpoint that external systems call to verify
    whether a message should reach the AI agent.
    
    No authentication required - this endpoint is designed to be
    called by messaging gateways that may not have credentials.
    """
    service = WhitelistService()
    
    try:
        data = CheckRequest.model_validate(request.get_json())
    except ValidationError as e:
        return jsonify({"error": "Validation failed", "details": e.errors()}), 400
    
    result = service.check(
        sender_id=data.sender_id,
        channel=data.channel,
        message_preview=data.message_preview,
    )
    
    response = CheckResponse(
        allowed=result.allowed,
        trust=result.trust_level.value,
        name=result.contact.name if result.contact else None,
        reason=result.reason,
    )
    
    return jsonify(response.model_dump())


@check_bp.get("/<sender_id>")
def check_sender_get(sender_id: str):
    """Quick check endpoint (GET for convenience).
    
    Query params:
        channel: Optional channel context
    """
    service = WhitelistService()
    channel = request.args.get("channel")
    
    result = service.check(sender_id=sender_id, channel=channel)
    
    response = CheckResponse(
        allowed=result.allowed,
        trust=result.trust_level.value,
        name=result.contact.name if result.contact else None,
        reason=result.reason,
    )
    
    return jsonify(response.model_dump())
