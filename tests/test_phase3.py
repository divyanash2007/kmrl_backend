import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings
from app.database import Base, engine, SessionLocal
from app.schemas.common import TicketStatusEnum, PriorityEnum


@pytest.fixture(scope="module")
def client():
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as test_client:
        yield test_client


def test_create_guest_session(client):
    """Verify commuter guest session is created without friction."""
    response = client.post("/api/v1/sessions/create", json={"guest_identifier": "browser-session-xyz"})
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["guest_identifier"] == "browser-session-xyz"
    assert "created_at" in data


def test_submit_ticket_and_track(client):
    """Verify submitting a ticket triggers AI pipeline and allows tracking by ID."""
    # 1. Create a guest session
    sess_res = client.post("/api/v1/sessions/create", json={})
    assert sess_res.status_code == 201
    session_id = sess_res.json()["id"]

    # 2. Submit query
    payload = {
        "query_text": "The escalator at Edappally station entrance has stopped working and is making strange noise",
        "guest_session_id": session_id,
        "user_latitude": 10.0253,
        "user_longitude": 76.3082,
        "location_accuracy": 15.0,
    }
    submit_res = client.post("/api/v1/tickets/submit", json=payload)
    assert submit_res.status_code == 201
    ticket = submit_res.json()

    assert ticket["id"].startswith("KMRL-")
    assert ticket["predicted_category"] in ["Maintenance", "Operations", "Passenger Grievances"]
    assert ticket["priority"] in ["HIGH", "MEDIUM", "LOW"]
    assert ticket["sla_hours"] > 0
    assert len(ticket["ai_response"]) > 20
    assert ticket["status"] in ["AUTO_RESOLVED", "ESCALATED"]

    # 3. Track query
    ticket_id = ticket["id"]
    track_res = client.get(f"/api/v1/tickets/track/{ticket_id}")
    assert track_res.status_code == 200
    track_data = track_res.json()
    assert track_data["id"] == ticket_id
    assert track_data["query_text"] == payload["query_text"]


def test_commuter_feedback_lifecycle(client):
    """Verify commuter feedback closes ticket or escalates to official triage queue."""
    # Submit ticket
    submit_res = client.post(
        "/api/v1/tickets/submit",
        json={"query_text": "What is the frequency of trains during evening rush hour?"}
    )
    ticket_id = submit_res.json()["id"]

    # 1. Commuter satisfied -> CLOSED
    fb_res = client.post(
        f"/api/v1/tickets/{ticket_id}/feedback",
        json={"is_user_satisfied": True, "user_feedback_comment": "Thank you, very clear information."}
    )
    assert fb_res.status_code == 200
    assert fb_res.json()["status"] == TicketStatusEnum.CLOSED.value
    assert fb_res.json()["is_user_satisfied"] is True

    # Submit second ticket
    submit_res2 = client.post(
        "/api/v1/tickets/submit",
        json={"query_text": "My Kochi-1 card was charged 50 rupees but gate refused to open at JLN Stadium"}
    )
    ticket_id2 = submit_res2.json()["id"]

    # 2. Commuter not satisfied -> ESCALATED
    fb_res2 = client.post(
        f"/api/v1/tickets/{ticket_id2}/feedback",
        json={"is_user_satisfied": False, "user_feedback_comment": "Need station master to verify transaction."}
    )
    assert fb_res2.status_code == 200
    assert fb_res2.json()["status"] == TicketStatusEnum.ESCALATED.value
    assert fb_res2.json()["requires_human_intervention"] is True


def test_official_safe_key_auth(client):
    """Verify Safe Key authentication gate."""
    # Invalid Safe Key
    bad_res = client.post("/api/v1/official/auth", json={"safe_key": "WRONG-KEY"})
    assert bad_res.status_code == 401

    # Valid Safe Key
    good_res = client.post("/api/v1/official/auth", json={"safe_key": settings.SAFE_KEY})
    assert good_res.status_code == 200
    assert good_res.json()["authenticated"] is True
    assert good_res.json()["token"] == settings.SAFE_KEY


def test_official_analytics_and_queue(client):
    """Verify official analytics aggregation and human escalation queue."""
    headers = {"X-Safe-Key": settings.SAFE_KEY}

    # 1. Unauthorized access check
    unauth = client.get("/api/v1/official/analytics")
    assert unauth.status_code == 401

    # 2. Authorized analytics
    analytics_res = client.get("/api/v1/official/analytics", headers=headers)
    assert analytics_res.status_code == 200
    analytics = analytics_res.json()
    assert analytics["total_queries"] >= 2
    assert "category_breakdown" in analytics
    assert "priority_breakdown" in analytics
    assert "status_breakdown" in analytics
    assert 0.0 <= analytics["first_contact_resolution_rate"] <= 100.0

    # 3. Escalation queue
    queue_res = client.get("/api/v1/official/queue", headers=headers)
    assert queue_res.status_code == 200
    queue_data = queue_res.json()
    assert "total" in queue_data
    assert "items" in queue_data


def test_official_resolution_and_audit_log(client):
    """Verify official can record investigation notes, change status, and view audit history."""
    headers = {"X-Safe-Key": settings.SAFE_KEY}

    # Submit an emergency ticket
    submit_res = client.post(
        "/api/v1/tickets/submit",
        json={"query_text": "Emergency! Passenger suffered minor injury on escalator at Platform 2"}
    )
    ticket_id = submit_res.json()["id"]

    # Official resolves ticket
    resolve_payload = {
        "official_id": "KMRL-OFFICER-409",
        "official_notes": "First aid administered by Station Control team. Passenger assisted safely.",
        "outcome": TicketStatusEnum.OFFICIAL_RESOLVED.value,
    }
    resolve_res = client.post(
        f"/api/v1/official/resolve/{ticket_id}",
        json=resolve_payload,
        headers=headers,
    )
    assert resolve_res.status_code == 200
    res_data = resolve_res.json()
    assert res_data["status"] == TicketStatusEnum.OFFICIAL_RESOLVED.value
    assert res_data["official_id"] == "KMRL-OFFICER-409"
    assert res_data["official_notes"] == resolve_payload["official_notes"]
    assert res_data["resolved_at"] is not None

    # Verify audit logs
    audit_res = client.get(f"/api/v1/official/audit-logs/{ticket_id}", headers=headers)
    assert audit_res.status_code == 200
    logs = audit_res.json()
    assert len(logs) >= 1
    assert logs[0]["official_id"] == "KMRL-OFFICER-409"
    assert logs[0]["action"] == "RESOLVED"

