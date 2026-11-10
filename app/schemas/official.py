from datetime import datetime
from typing import Optional, Dict
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.common import TicketStatusEnum, OfficialActionEnum


class OfficialLoginRequest(BaseModel):
    safe_key: str = Field(
        ...,
        min_length=4,
        description="KMRL Official Safe Key authentication passphrase",
    )


class OfficialLoginResponse(BaseModel):
    authenticated: bool
    token: str
    message: str


class OfficialResolveRequest(BaseModel):
    official_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="ID / Badge number of the reviewing KMRL official",
    )
    official_notes: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Detailed official remarks, resolution actions, or operational directives",
    )
    outcome: TicketStatusEnum = Field(
        default=TicketStatusEnum.OFFICIAL_RESOLVED,
        description="Target ticket status",
    )


class OfficialAnalyticsResponse(BaseModel):
    total_queries: int
    auto_resolved_count: int
    escalated_count: int
    official_resolved_count: int
    first_contact_resolution_rate: float
    priority_breakdown: Dict[str, int]
    category_breakdown: Dict[str, int]
    status_breakdown: Dict[str, int]


class OfficialAuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: str
    official_id: str
    action: OfficialActionEnum
    notes: Optional[str] = None
    created_at: datetime

