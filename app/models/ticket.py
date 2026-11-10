from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Float, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(String(32), primary_key=True, index=True)  # e.g. KMRL-2026-8741
    guest_session_id = Column(String(36), ForeignKey("guest_sessions.id", ondelete="SET NULL"), nullable=True)
    query_text = Column(Text, nullable=False)

    # GPS Coordinates (Solely for source authenticity & rapid emergency reach)
    user_latitude = Column(Float, nullable=True)
    user_longitude = Column(Float, nullable=True)
    location_accuracy = Column(Float, nullable=True)

    # AI Pipeline Outputs
    predicted_category = Column(String(100), nullable=False, index=True)
    classification_confidence = Column(Float, nullable=False)
    priority = Column(String(20), nullable=False, index=True)  # EMERGENCY, HIGH, MEDIUM, LOW
    sla_hours = Column(Integer, nullable=False)
    requires_human_intervention = Column(Boolean, default=False)
    ai_response = Column(Text, nullable=False)
    ai_referenced_docs = Column(Text, nullable=True)  # JSON-encoded string of referenced docs

    # Status & Lifecycle
    # Statuses: AUTO_RESOLVED, ESCALATED, IN_PROGRESS, OFFICIAL_RESOLVED, CLOSED
    status = Column(String(30), nullable=False, default="AUTO_RESOLVED", index=True)

    # Commuter Satisfaction Feedback
    is_user_satisfied = Column(Boolean, nullable=True)
    user_feedback_comment = Column(Text, nullable=True)

    # Official Resolution
    official_notes = Column(Text, nullable=True)
    official_id = Column(String(50), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    guest_session = relationship("GuestSession", back_populates="tickets")
    audit_logs = relationship("OfficialAuditLog", back_populates="ticket", cascade="all, delete-orphan")

