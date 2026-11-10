from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.schemas.common import PriorityEnum, TicketStatusEnum


class TicketCreate(BaseModel):
    query_text: str = Field(
        ...,
        min_length=5,
        max_length=2000,
        description="The passenger query, complaint, or request text",
    )
    guest_session_id: Optional[str] = Field(
        None,
        description="UUID of the commuter guest session",
    )
    user_latitude: Optional[float] = Field(
        None,
        description="Latitude of the commuter device for source credibility and emergency dispatch",
    )
    user_longitude: Optional[float] = Field(
        None,
        description="Longitude of the commuter device for source credibility and emergency dispatch",
    )
    location_accuracy: Optional[float] = Field(
        None,
        ge=0,
        description="Accuracy of the GPS coordinate reading in meters",
    )

    @field_validator("query_text")
    @classmethod
    def validate_query_text(cls, v: str) -> str:
        clean = v.strip()
        if len(clean) < 5:
            raise ValueError("Query text must be at least 5 non-whitespace characters.")
        return clean

    @field_validator("user_latitude")
    @classmethod
    def validate_latitude(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and not (-90.0 <= v <= 90.0):
            raise ValueError("Latitude must be between -90.0 and 90.0 degrees.")
        return v

    @field_validator("user_longitude")
    @classmethod
    def validate_longitude(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and not (-180.0 <= v <= 180.0):
            raise ValueError("Longitude must be between -180.0 and 180.0 degrees.")
        return v


class TicketFeedback(BaseModel):
    is_user_satisfied: bool = Field(
        ...,
        description="True if commuter is satisfied with automated resolution, False if human help is needed",
    )
    user_feedback_comment: Optional[str] = Field(
        None,
        max_length=1000,
        description="Optional detailed feedback from the commuter",
    )


class TicketResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    guest_session_id: Optional[str] = None
    query_text: str
    user_latitude: Optional[float] = None
    user_longitude: Optional[float] = None
    location_accuracy: Optional[float] = None

    # AI Pipeline Outputs
    predicted_category: str
    classification_confidence: float
    priority: PriorityEnum
    sla_hours: int
    requires_human_intervention: bool
    ai_response: str
    ai_referenced_docs: Optional[str] = None

    # Status & Feedback
    status: TicketStatusEnum
    is_user_satisfied: Optional[bool] = None
    user_feedback_comment: Optional[str] = None

    # Official Resolution
    official_notes: Optional[str] = None
    official_id: Optional[str] = None
    resolved_at: Optional[datetime] = None

    created_at: datetime
    updated_at: datetime


class TicketListResponse(BaseModel):
    total: int
    items: List[TicketResponse]

