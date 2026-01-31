"""Audit service - logging all whitelist decisions and actions."""

import json
from typing import Any

import structlog

from waasp.models import db, Contact, AuditLog, AuditAction

logger = structlog.get_logger()


class AuditService:
    """Service for audit logging.
    
    Every whitelist decision and administrative action is logged
    for security analysis and debugging.
    """

    def log_check(
        self,
        sender_id: str,
        action: AuditAction,
        channel: str | None = None,
        contact: Contact | None = None,
        reason: str | None = None,
        message_preview: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditLog:
        """Log a whitelist check decision.
        
        Args:
            sender_id: The sender's identifier
            action: The action/decision taken
            channel: Channel where check occurred
            contact: Related contact if found
            reason: Human-readable reason for decision
            message_preview: Truncated message content (for debugging)
            metadata: Additional context
            
        Returns:
            The created AuditLog entry
        """
        # Truncate message preview for safety
        if message_preview and len(message_preview) > 500:
            message_preview = message_preview[:497] + "..."

        log_entry = AuditLog(
            action=action,
            sender_id=sender_id,
            channel=channel,
            contact_id=contact.id if contact else None,
            message_preview=message_preview,
            decision_reason=reason,
            metadata_json=json.dumps(metadata) if metadata else None,
        )
        
        db.session.add(log_entry)
        db.session.commit()

        logger.info(
            "audit_logged",
            action=action.value,
            sender_id=sender_id,
            channel=channel,
            reason=reason,
        )

        return log_entry

    def log_admin_action(
        self,
        action: AuditAction,
        sender_id: str,
        channel: str | None = None,
        contact: Contact | None = None,
        reason: str | None = None,
        performed_by: str | None = None,
    ) -> AuditLog:
        """Log an administrative action.
        
        Args:
            action: The administrative action taken
            sender_id: The sender_id affected
            channel: Channel scope if applicable
            contact: Related contact if applicable
            reason: Reason for the action
            performed_by: Who performed the action (for admin tracking)
            
        Returns:
            The created AuditLog entry
        """
        metadata = {}
        if performed_by:
            metadata["performed_by"] = performed_by

        log_entry = AuditLog(
            action=action,
            sender_id=sender_id,
            channel=channel,
            contact_id=contact.id if contact else None,
            decision_reason=reason,
            metadata_json=json.dumps(metadata) if metadata else None,
        )
        
        db.session.add(log_entry)
        db.session.commit()

        logger.info(
            "admin_action_logged",
            action=action.value,
            sender_id=sender_id,
            reason=reason,
        )

        return log_entry

    def get_logs(
        self,
        sender_id: str | None = None,
        action: AuditAction | None = None,
        channel: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditLog]:
        """Query audit logs with optional filters.
        
        Args:
            sender_id: Filter by sender
            action: Filter by action type
            channel: Filter by channel
            limit: Maximum results to return
            offset: Pagination offset
            
        Returns:
            List of matching AuditLog entries
        """
        query = db.session.query(AuditLog)
        
        if sender_id:
            query = query.filter(AuditLog.sender_id == sender_id)
        if action:
            query = query.filter(AuditLog.action == action)
        if channel:
            query = query.filter(AuditLog.channel == channel)
            
        return (
            query
            .order_by(AuditLog.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def get_stats(self) -> dict[str, Any]:
        """Get aggregate statistics from audit logs.
        
        Returns:
            Dictionary with audit statistics
        """
        from sqlalchemy import func
        
        total = db.session.query(AuditLog).count()
        
        by_action = (
            db.session.query(AuditLog.action, func.count(AuditLog.id))
            .group_by(AuditLog.action)
            .all()
        )
        
        return {
            "total_entries": total,
            "by_action": {action.value: count for action, count in by_action},
        }
