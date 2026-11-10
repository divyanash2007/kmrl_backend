from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine, SessionLocal
from app.models.ticket import Ticket
from app.schemas.common import TicketStatusEnum


def test_resolve_ticket_with_json_and_raw_content():
    Base.metadata.create_all(bind=engine)
    client = TestClient(app)
    db = SessionLocal()

    # Create ticket for resolve test
    ticket = db.query(Ticket).filter(Ticket.id == "KMRL-TEST-RESOLVE-99").first()
    if not ticket:
        ticket = Ticket(
            id="KMRL-TEST-RESOLVE-99",
            query_text="Testing resolve endpoint fix",
            predicted_category="Operations",
            classification_confidence=0.95,
            priority="HIGH",
            sla_hours=4,
            requires_human_intervention=True,
            ai_response="Guidance note",
            status=TicketStatusEnum.ESCALATED.value,
        )
        db.add(ticket)
        db.commit()

    headers_auth = {"X-Safe-Key": "KMRL-SECURE-2026"}

    # Case 1: Standard JSON (Content-Type: application/json)
    res1 = client.post(
        "/api/v1/official/resolve/KMRL-TEST-RESOLVE-99",
        json={
            "official_id": "OFFICER-A",
            "official_notes": "First test notes",
            "outcome": "OFFICIAL_RESOLVED",
        },
        headers=headers_auth,
    )
    assert res1.status_code == 200
    assert res1.json()["official_id"] == "OFFICER-A"
    assert res1.json()["status"] == "OFFICIAL_RESOLVED"

    # Case 2: Raw bytes WITHOUT Content-Type header (the bug reproduction)
    raw_payload = b'{"official_id": "OFFICER-B", "official_notes": "Second test notes without header"}'
    res2 = client.post(
        "/api/v1/official/resolve/KMRL-TEST-RESOLVE-99",
        content=raw_payload,
        headers=headers_auth,
    )
    print("RES2 RESPONSE:", res2.status_code, res2.json())
    assert res2.status_code == 200
    assert res2.json()["official_id"] == "OFFICER-B"
    assert res2.json()["status"] == "OFFICIAL_RESOLVED"
