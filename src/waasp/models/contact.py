"""Contact model - the core of the whitelist system."""

from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from waasp.models.base import Base

if TYPE_CHECKING:
    from waasp.models.audit import AuditLog


class TrustLevel(str, Enum):
    """Trust levels for contacts.
    
    - sovereign: Full access, can modify whitelist (this is you)
    - trusted: Can trigger agent actions (friends, family)
    - limited: Agent sees message but can't trigger dangerous actions
    - blocked: Message never reaches agent, logged and dropped
    """

    SOVEREIGN = "sovereign"
    TRUSTED = "trusted"
    LIMITED = "limited"
    BLOCKED = "blocked"

    @classmethod
    def from_string(cls, value: str) -> "TrustLevel":
        """Parse trust level from string, case-insensitive."""
        try:
            return cls(value.lower())
        except ValueError:
            return cls.BLOCKED  # Safe default


class Contact(Base):
    """A contact in the whitelist.
    
    Contacts are identified by their sender_id (e.g., phone number)
    and optionally scoped to a specific channel.
    """

    __tablename__ = "contacts"

    # Identity
    sender_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        doc="Unique identifier (phone number, user ID, etc.)",
    )
    channel: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
        doc="Channel scope (whatsapp, telegram, etc.). Null = all channels.",
    )
    name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="Human-readable name for this contact",
    )

    # Trust
    trust_level: Mapped[TrustLevel] = mapped_column(
        default=TrustLevel.BLOCKED,
        doc="Trust level determining what actions are allowed",
    )

    # Metadata
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Optional notes about this contact",
    )

    # Relationships
    audit_logs: Mapped[list["AuditLog"]] = relationship(
        "AuditLog",
        back_populates="contact",
        lazy="dynamic",
    )

    # Indexes
    __table_args__ = (
        Index("ix_contacts_sender_channel", "sender_id", "channel", unique=True),
    )

    def __repr__(self) -> str:
        return f"<Contact {self.name or self.sender_id} ({self.trust_level.value})>"

    @property
    def is_allowed(self) -> bool:
        """Check if this contact is allowed to interact with the agent."""
        return self.trust_level != TrustLevel.BLOCKED

    @property
    def can_trigger_actions(self) -> bool:
        """Check if this contact can trigger agent actions."""
        return self.trust_level in (TrustLevel.SOVEREIGN, TrustLevel.TRUSTED)

    @property
    def is_sovereign(self) -> bool:
        """Check if this contact has full administrative access."""
        return self.trust_level == TrustLevel.SOVEREIGN
