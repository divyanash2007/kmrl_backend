import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings
from app.database import Base, engine
from app.schemas.common import TicketStatusEnum, PriorityEnum


@pytest.fixture(scope="module")
def client():
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as test_client:
        yield test_client


def test_full_system_lifecycle_e2e(client):
    """
    Complete End-to-End Civic Redressal Journey:
    1. Commuter creates frictionless guest session.
    2. Commuter submits high-urgency safety grievance with GPS coordinates.
    3. AI pipeline classifies, scores urgency (CRITICAL), and auto-escalates to officials.
    4. Commuter tracks ticket and reads instant AI guidance.
    5. Official logs in with Safe Key.
    6. Official checks escalation queue and views GPS coordinates for dispatch.
    7. Official records formal resolution directive.
    8. Commuter tracks ticket again and reviews official resolution notes.
    9. Commuter submits feedback marking 'Satisfied', auto-closing the ticket.
    10. Official analytics reflect updated metrics and resolution rates.
    """
    headers = {"X-Safe-Key": settings.SAFE_KEY}

    # Step 1: Commuter creates guest session
    sess_res = client.post("/api/v1/sessions/create", json={"guest_identifier": "mobile-commuter-789"})
    assert sess_res.status_code == 201
    guest_session_id = sess_res.json()["id"]

    # Step 2: Commuter submits query with credibility GPS
    submit_payload = {
        "query_text": "Emergency! Smoke detected near Platform 2 emergency exit stairs at MG Road station",
        "guest_session_id": guest_session_id,
        "user_latitude": 9.9816,
        "user_longitude": 76.2999,
        "location_accuracy": 8.5,
    }
    submit_res = client.post("/api/v1/tickets/submit", json=submit_payload)
    assert submit_res.status_code == 201
    ticket_data = submit_res.json()
    ticket_id = ticket_data["id"]

    # Step 3: Verify AI pipeline outputs
    assert ticket_id.startswith("KMRL-")
    assert ticket_data["predicted_category"] == "Safety"
    assert ticket_data["priority"] == PriorityEnum.CRITICAL.value
    assert ticket_data["requires_human_intervention"] is True
    assert ticket_data["status"] == TicketStatusEnum.ESCALATED.value
    assert ticket_data["sla_hours"] == 1
    assert len(ticket_data["ai_response"]) > 30

    # Step 4: Commuter tracks query
    track_res = client.get(f"/api/v1/tickets/track/{ticket_id}")
    assert track_res.status_code == 200
    assert track_res.json()["status"] == TicketStatusEnum.ESCALATED.value

    # Step 5: Official authenticates with Safe Key
    auth_res = client.post("/api/v1/official/auth", json={"safe_key": settings.SAFE_KEY})
    assert auth_res.status_code == 200
    assert auth_res.json()["authenticated"] is True

    # Step 6: Official reviews escalation queue and locates ticket
    queue_res = client.get("/api/v1/official/queue?requires_human_only=true", headers=headers)
    assert queue_res.status_code == 200
    queue_items = queue_res.json()["items"]
    matched = [item for item in queue_items if item["id"] == ticket_id]
    assert len(matched) == 1
    assert matched[0]["user_latitude"] == 9.9816
    assert matched[0]["user_longitude"] == 76.2999

    # Step 7: Official records formal resolution
    resolve_payload = {
        "official_id": "KMRL-STATION-CONTROLLER-12",
        "official_notes": "Station security deployed to Platform 2. Minor exhaust duct heat sensor tripped. Area fully secured.",
        "outcome": TicketStatusEnum.OFFICIAL_RESOLVED.value,
    }
    resolve_res = client.post(
        f"/api/v1/official/resolve/{ticket_id}",
        json=resolve_payload,
        headers=headers,
    )
    assert resolve_res.status_code == 200
    assert resolve_res.json()["status"] == TicketStatusEnum.OFFICIAL_RESOLVED.value

    # Step 8: Commuter tracks ticket to see resolution
    updated_track = client.get(f"/api/v1/tickets/track/{ticket_id}")
    assert updated_track.status_code == 200
    assert updated_track.json()["status"] == TicketStatusEnum.OFFICIAL_RESOLVED.value
    assert updated_track.json()["official_notes"] == resolve_payload["official_notes"]

    # Step 9: Commuter provides satisfaction feedback -> marks CLOSED
    fb_res = client.post(
        f"/api/v1/tickets/{ticket_id}/feedback",
        json={"is_user_satisfied": True, "user_feedback_comment": "Thank you for the rapid response and clarification!"}
    )
    assert fb_res.status_code == 200
    assert fb_res.json()["status"] == TicketStatusEnum.CLOSED.value
    assert fb_res.json()["is_user_satisfied"] is True

    # Step 10: Official analytics reflects resolution
    analytics_res = client.get("/api/v1/official/analytics", headers=headers)
    assert analytics_res.status_code == 200
    analytics = analytics_res.json()
    assert analytics["total_queries"] >= 1
    assert analytics["category_breakdown"].get("Safety", 0) >= 1

