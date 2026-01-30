"""Check schemas for whitelist verification."""

from typing import Literal

from pydantic import BaseModel, Field


TrustLevelStr = Literal["sovereign", "trusted", "limited", "blocked"]


class CheckRequest(BaseModel):
    """Schema for whitelist check request."""

    sender_id: str = Field(
        ...,
        min_length=1,
        description="Sender identifier to check",
        examples=["+447375862225"],
    )
    channel: str | None = Field(
        default=None,
        description="Channel context",
        examples=["whatsapp"],
    )
    message_preview: str | None = Field(
        default=None,
        max_length=500,
        description="Optional message preview for audit logging",
    )


class CheckResponse(BaseModel):
    """Schema for whitelist check response."""

    allowed: bool = Field(
        ...,
        description="Whether the sender is allowed to interact",
    )
    trust: TrustLevelStr = Field(
        ...,
        description="Trust level of the sender",
    )
    name: str | None = Field(
        default=None,
        description="Name of the contact if known",
    )
    reason: str = Field(
        ...,
        description="Human-readable reason for the decision",
    )
