"""Audit log model - tracking all whitelist decisions."""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from waasp.models.base import Base

if TYPE_CHECKING:
    from waasp.models.contact import Contact


class AuditAction(str, Enum):
    """Types of audited actions."""

    # Decision actions
    ALLOWED = "allowed"
    BLOCKED = "blocked"
    LIMITED = "limited"

    # Administrative actions
    CONTACT_ADDED = "contact_added"
    CONTACT_UPDATED = "contact_updated"
    CONTACT_REMOVED = "contact_removed"
    TRUST_CHANGED = "trust_changed"

    # System events
    CHECK_PERFORMED = "check_performed"
    API_ACCESS = "api_access"


class AuditLog(Base):
    """Audit trail for all whitelist operations.
    
    Every check, decision, and administrative action is logged
    for security analysis and debugging.
    """

    __tablename__ = "audit_logs"

    # What happened
    action: Mapped[AuditAction] = mapped_column(
        nullable=False,
        index=True,
        doc="Type of action that was performed",
    )

    # Who was involved
    sender_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        doc="Sender ID that triggered this log entry",
    )
    channel: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        doc="Channel where the action occurred",
    )
    contact_id: Mapped[int | None] = mapped_column(
        ForeignKey("contacts.id", ondelete="SET NULL"),
        nullable=True,
        doc="Related contact if one exists",
    )

    # Context
    message_preview: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        doc="Truncated preview of the message (for debugging)",
    )
    metadata_json: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Additional context as JSON",
    )

    # Decision details
    decision_reason: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="Why this decision was made",
    )

    # Relationships
    contact: Mapped["Contact | None"] = relationship(
        "Contact",
        back_populates="audit_logs",
    )

    # Indexes for common queries
    __table_args__ = (
        Index("ix_audit_logs_sender_created", "sender_id", "created_at"),
        Index("ix_audit_logs_action_created", "action", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<AuditLog {self.action.value} {self.sender_id} @ {self.created_at}>"
