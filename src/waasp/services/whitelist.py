"""Whitelist service - core business logic for contact management."""

from dataclasses import dataclass
from typing import Optional

import structlog

from waasp.models import db, Contact, TrustLevel, AuditLog, AuditAction

logger = structlog.get_logger()


@dataclass
class CheckResult:
    """Result of a whitelist check."""

    allowed: bool
    trust_level: TrustLevel
    contact: Contact | None
    reason: str

    def to_dict(self) -> dict:
        return {
            "allowed": self.allowed,
            "trust": self.trust_level.value,
            "name": self.contact.name if self.contact else None,
            "reason": self.reason,
        }


class WhitelistService:
    """Service for managing the contact whitelist.
    
    This is the core of WAASP - all whitelist decisions flow through here.
    """

    def __init__(self, audit_service: "AuditService | None" = None):
        """Initialize the whitelist service.
        
        Args:
            audit_service: Optional audit service for logging decisions
        """
        from waasp.services.audit import AuditService
        self.audit = audit_service or AuditService()

    def check(
        self,
        sender_id: str,
        channel: str | None = None,
        message_preview: str | None = None,
    ) -> CheckResult:
        """Check if a sender is allowed to interact with the agent.
        
        Args:
            sender_id: The sender's identifier (phone number, user ID, etc.)
            channel: Optional channel scope (whatsapp, telegram, etc.)
            message_preview: Optional message preview for audit logging
            
        Returns:
            CheckResult with the decision and details
        """
        log = logger.bind(sender_id=sender_id, channel=channel)
        
        # Look up contact - first try channel-specific, then global
        contact = self._find_contact(sender_id, channel)
        
        if contact is None:
            # Unknown sender - default to blocked
            log.info("unknown_sender_blocked")
            result = CheckResult(
                allowed=False,
                trust_level=TrustLevel.BLOCKED,
                contact=None,
                reason="Unknown sender - not in whitelist",
            )
            self.audit.log_check(
                sender_id=sender_id,
                channel=channel,
                action=AuditAction.BLOCKED,
                reason=result.reason,
                message_preview=message_preview,
            )
            return result

        # Contact exists - check trust level
        if contact.trust_level == TrustLevel.BLOCKED:
            log.info("sender_explicitly_blocked", contact_id=contact.id)
            result = CheckResult(
                allowed=False,
                trust_level=TrustLevel.BLOCKED,
                contact=contact,
                reason="Sender is explicitly blocked",
            )
        elif contact.trust_level == TrustLevel.LIMITED:
            log.info("sender_limited", contact_id=contact.id)
            result = CheckResult(
                allowed=True,  # Limited still sees messages
                trust_level=TrustLevel.LIMITED,
                contact=contact,
                reason="Sender has limited access",
            )
        else:
            log.info("sender_allowed", contact_id=contact.id, trust=contact.trust_level.value)
            result = CheckResult(
                allowed=True,
                trust_level=contact.trust_level,
                contact=contact,
                reason=f"Sender is {contact.trust_level.value}",
            )

        # Log the decision
        action = AuditAction.ALLOWED if result.allowed else AuditAction.BLOCKED
        if result.trust_level == TrustLevel.LIMITED:
            action = AuditAction.LIMITED
            
        self.audit.log_check(
            sender_id=sender_id,
            channel=channel,
            contact=contact,
            action=action,
            reason=result.reason,
            message_preview=message_preview,
        )

        return result

    def add_contact(
        self,
        sender_id: str,
        trust_level: TrustLevel = TrustLevel.TRUSTED,
        channel: str | None = None,
        name: str | None = None,
        notes: str | None = None,
    ) -> Contact:
        """Add a new contact to the whitelist.
        
        Args:
            sender_id: The sender's identifier
            trust_level: Trust level to assign
            channel: Optional channel scope
            name: Optional human-readable name
            notes: Optional notes about this contact
            
        Returns:
            The created Contact
            
        Raises:
            ValueError: If contact already exists
        """
        # Check if contact already exists
        existing = self._find_contact(sender_id, channel)
        if existing:
            raise ValueError(f"Contact {sender_id} already exists")

        contact = Contact(
            sender_id=sender_id,
            channel=channel,
            name=name,
            trust_level=trust_level,
            notes=notes,
        )
        db.session.add(contact)
        db.session.commit()

        logger.info(
            "contact_added",
            sender_id=sender_id,
            trust_level=trust_level.value,
            contact_id=contact.id,
        )
        
        self.audit.log_admin_action(
            action=AuditAction.CONTACT_ADDED,
            sender_id=sender_id,
            channel=channel,
            contact=contact,
            reason=f"Added with trust level {trust_level.value}",
        )

        return contact

    def update_contact(
        self,
        sender_id: str,
        channel: str | None = None,
        trust_level: TrustLevel | None = None,
        name: str | None = None,
        notes: str | None = None,
    ) -> Contact:
        """Update an existing contact.
        
        Args:
            sender_id: The sender's identifier
            channel: Optional channel scope
            trust_level: New trust level (if changing)
            name: New name (if changing)
            notes: New notes (if changing)
            
        Returns:
            The updated Contact
            
        Raises:
            ValueError: If contact doesn't exist
        """
        contact = self._find_contact(sender_id, channel)
        if not contact:
            raise ValueError(f"Contact {sender_id} not found")

        old_trust = contact.trust_level
        
        if trust_level is not None:
            contact.trust_level = trust_level
        if name is not None:
            contact.name = name
        if notes is not None:
            contact.notes = notes

        db.session.commit()

        logger.info(
            "contact_updated",
            sender_id=sender_id,
            contact_id=contact.id,
        )

        # Log trust level changes specifically
        if trust_level is not None and trust_level != old_trust:
            self.audit.log_admin_action(
                action=AuditAction.TRUST_CHANGED,
                sender_id=sender_id,
                channel=channel,
                contact=contact,
                reason=f"Trust changed from {old_trust.value} to {trust_level.value}",
            )
        else:
            self.audit.log_admin_action(
                action=AuditAction.CONTACT_UPDATED,
                sender_id=sender_id,
                channel=channel,
                contact=contact,
                reason="Contact details updated",
            )

        return contact

    def remove_contact(self, sender_id: str, channel: str | None = None) -> bool:
        """Remove a contact from the whitelist.
        
        Args:
            sender_id: The sender's identifier
            channel: Optional channel scope
            
        Returns:
            True if contact was removed, False if not found
        """
        contact = self._find_contact(sender_id, channel)
        if not contact:
            return False

        contact_id = contact.id
        db.session.delete(contact)
        db.session.commit()

        logger.info(
            "contact_removed",
            sender_id=sender_id,
            contact_id=contact_id,
        )
        
        self.audit.log_admin_action(
            action=AuditAction.CONTACT_REMOVED,
            sender_id=sender_id,
            channel=channel,
            reason="Contact removed from whitelist",
        )

        return True

    def list_contacts(
        self,
        trust_level: TrustLevel | None = None,
        channel: str | None = None,
    ) -> list[Contact]:
        """List all contacts, optionally filtered.
        
        Args:
            trust_level: Filter by trust level
            channel: Filter by channel
            
        Returns:
            List of matching contacts
        """
        query = Contact.query
        
        if trust_level:
            query = query.filter(Contact.trust_level == trust_level)
        if channel:
            query = query.filter(
                (Contact.channel == channel) | (Contact.channel.is_(None))
            )
            
        return query.order_by(Contact.created_at.desc()).all()

    def _find_contact(
        self,
        sender_id: str,
        channel: str | None = None,
    ) -> Contact | None:
        """Find a contact by sender_id and optional channel.
        
        Lookup priority:
        1. Exact match (sender_id + channel)
        2. Global match (sender_id + channel=None)
        """
        # Try channel-specific first
        if channel:
            contact = Contact.query.filter_by(
                sender_id=sender_id,
                channel=channel,
            ).first()
            if contact:
                return contact

        # Fall back to global (channel=None)
        return Contact.query.filter_by(
            sender_id=sender_id,
            channel=None,
        ).first()
