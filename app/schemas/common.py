from enum import Enum
from pydantic import BaseModel


class PriorityEnum(str, Enum):
    CRITICAL = "CRITICAL"
    EMERGENCY = "EMERGENCY"  # Retained as alias for backward compatibility
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class TicketStatusEnum(str, Enum):
    AUTO_RESOLVED = "AUTO_RESOLVED"
    ESCALATED = "ESCALATED"
    IN_PROGRESS = "IN_PROGRESS"
    OFFICIAL_RESOLVED = "OFFICIAL_RESOLVED"
    CLOSED = "CLOSED"


class OfficialActionEnum(str, Enum):
    RESOLVED = "RESOLVED"
    ESCALATED = "ESCALATED"
    NOTE_ADDED = "NOTE_ADDED"
    STATUS_CHANGE = "STATUS_CHANGE"


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    database: str

