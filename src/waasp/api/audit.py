"""Audit API endpoints."""

from flask import Blueprint, request, jsonify

from waasp.models import AuditAction
from waasp.schemas import AuditLogResponse, AuditStatsResponse
from waasp.services import AuditService
from waasp.api.auth import require_api_token


audit_bp = Blueprint("audit", __name__)


@audit_bp.get("/")
@require_api_token
def list_audit_logs():
    """List audit log entries.
    
    Query params:
        sender_id: Filter by sender
        action: Filter by action type
        channel: Filter by channel
        limit: Maximum results (default 100)
        offset: Pagination offset
    """
    service = AuditService()
    
    sender_id = request.args.get("sender_id")
    action_str = request.args.get("action")
    channel = request.args.get("channel")
    limit = request.args.get("limit", 100, type=int)
    offset = request.args.get("offset", 0, type=int)
    
    action = None
    if action_str:
        try:
            action = AuditAction(action_str.lower())
        except ValueError:
            return jsonify({"error": f"Invalid action: {action_str}"}), 400
    
    logs = service.get_logs(
        sender_id=sender_id,
        action=action,
        channel=channel,
        limit=min(limit, 1000),  # Cap at 1000
        offset=offset,
    )
    
    return jsonify({
        "logs": [AuditLogResponse.model_validate(log).model_dump() for log in logs],
        "count": len(logs),
        "limit": limit,
        "offset": offset,
    })


@audit_bp.get("/stats")
@require_api_token
def get_audit_stats():
    """Get aggregate audit statistics."""
    service = AuditService()
    stats = service.get_stats()
    
    response = AuditStatsResponse(**stats)
    return jsonify(response.model_dump())
