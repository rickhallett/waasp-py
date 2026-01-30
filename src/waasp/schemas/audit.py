"""Audit log schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AuditLogResponse(BaseModel):
    """Schema for audit log entry response."""

    id: int
    action: str
    sender_id: str
    channel: str | None
    contact_id: int | None
    message_preview: str | None
    decision_reason: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class AuditStatsResponse(BaseModel):
    """Schema for audit statistics response."""

    total_entries: int
    by_action: dict[str, int]
