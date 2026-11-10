from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class OfficialAuditLog(Base):
    __tablename__ = "official_audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticket_id = Column(String(32), ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    official_id = Column(String(50), nullable=False)
    action = Column(String(50), nullable=False)  # RESOLVED, ESCALATED, NOTE_ADDED, STATUS_CHANGE
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationship
    ticket = relationship("Ticket", back_populates="audit_logs")

