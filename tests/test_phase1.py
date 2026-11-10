import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.database import Base, engine, SessionLocal
from app.models import GuestSession, Ticket, OfficialAuditLog
from app.schemas.ticket import TicketCreate, TicketFeedback
from app.schemas.common import PriorityEnum, TicketStatusEnum


@pytest.fixture(scope="module")
def client():
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="function")
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def test_health_check_with_db(client):
    """Test health check verifies both API and live PostgreSQL database."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
    assert "KMRL" in data["service"]


def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert data["docs"] == "/docs"


def test_pydantic_ticket_create_validation():
    """Verify Pydantic validates input boundaries and cleans strings."""
    # Valid input
    valid_payload = {
        "query_text": "  Train delayed at Edappally station today  ",
        "user_latitude": 10.0245,
        "user_longitude": 76.3078,
        "location_accuracy": 12.5,
    }
    ticket_in = TicketCreate(**valid_payload)
    assert ticket_in.query_text == "Train delayed at Edappally station today"
    assert ticket_in.user_latitude == 10.0245
    assert ticket_in.user_longitude == 76.3078

    # Too short / whitespace
    with pytest.raises(ValidationError):
        TicketCreate(query_text="   a   ")

    # Invalid latitude
    with pytest.raises(ValidationError):
        TicketCreate(query_text="Valid text query", user_latitude=95.0)

    # Invalid longitude
    with pytest.raises(ValidationError):
        TicketCreate(query_text="Valid text query", user_longitude=-195.0)

    # Negative location accuracy
    with pytest.raises(ValidationError):
        TicketCreate(query_text="Valid text query", location_accuracy=-5.0)


def test_ticket_model_persistence(db_session):
    """Test full database lifecycle for guest session, ticket, and audit log."""
    # 1. Create Guest Session
    session_obj = GuestSession(guest_identifier="test-device-uuid-1234")
    db_session.add(session_obj)
    db_session.commit()
    db_session.refresh(session_obj)
    assert session_obj.id is not None

    # 2. Create Ticket
    ticket_obj = Ticket(
        id="KMRL-TEST-0001",
        guest_session_id=session_obj.id,
        query_text="My bag was left on the seat near door B",
        user_latitude=9.9816,
        user_longitude=76.2999,
        location_accuracy=8.0,
        predicted_category="Lost & Found",
        classification_confidence=0.94,
        priority=PriorityEnum.HIGH.value,
        sla_hours=2,
        requires_human_intervention=False,
        ai_response="Please contact the Station Master immediately.",
        status=TicketStatusEnum.AUTO_RESOLVED.value,
    )
    db_session.add(ticket_obj)
    db_session.commit()
    db_session.refresh(ticket_obj)

    assert ticket_obj.id == "KMRL-TEST-0001"
    assert ticket_obj.guest_session.guest_identifier == "test-device-uuid-1234"

    # 3. Add Audit Log
    log = OfficialAuditLog(
        ticket_id=ticket_obj.id,
        official_id="KMRL-OFFICER-7",
        action="NOTE_ADDED",
        notes="Passenger recovered bag at MG Road customer desk.",
    )
    db_session.add(log)
    db_session.commit()
    db_session.refresh(log)
    assert log.id is not None
    assert log.action == "NOTE_ADDED"

    # Cleanup test record
    db_session.delete(session_obj)
    db_session.commit()
