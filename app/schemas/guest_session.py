from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class GuestSessionCreate(BaseModel):
    guest_identifier: Optional[str] = Field(
        None,
        description="Optional custom device identifier or client-generated token",
        max_length=100,
    )


class GuestSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    guest_identifier: str
    created_at: datetime
    last_active: datetime

