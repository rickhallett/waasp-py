"""Contact schemas for API validation."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


TrustLevelStr = Literal["sovereign", "trusted", "limited", "blocked"]


class ContactBase(BaseModel):
    """Base contact fields."""

    sender_id: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Unique identifier (phone number, user ID, etc.)",
        examples=["+447375862225"],
    )
    channel: str | None = Field(
        default=None,
        max_length=50,
        description="Channel scope (whatsapp, telegram, etc.)",
        examples=["whatsapp"],
    )
    name: str | None = Field(
        default=None,
        max_length=255,
        description="Human-readable name",
        examples=["Kai"],
    )
    notes: str | None = Field(
        default=None,
        description="Optional notes about this contact",
    )


class ContactCreate(ContactBase):
    """Schema for creating a new contact."""

    trust_level: TrustLevelStr = Field(
        default="trusted",
        description="Trust level to assign",
    )

    @field_validator("sender_id")
    @classmethod
    def normalize_sender_id(cls, v: str) -> str:
        """Normalize sender_id (strip whitespace)."""
        return v.strip()


class ContactUpdate(BaseModel):
    """Schema for updating a contact."""

    trust_level: TrustLevelStr | None = Field(
        default=None,
        description="New trust level",
    )
    name: str | None = Field(
        default=None,
        max_length=255,
        description="New name",
    )
    notes: str | None = Field(
        default=None,
        description="New notes",
    )


class ContactResponse(BaseModel):
    """Schema for contact response."""

    id: int
    sender_id: str
    channel: str | None
    name: str | None
    trust_level: TrustLevelStr
    notes: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ContactListResponse(BaseModel):
    """Schema for list contacts response."""

    contacts: list[ContactResponse]
    total: int
