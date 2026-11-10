import random
import string
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models.guest_session import GuestSession
from app.models.ticket import Ticket
from app.schemas.guest_session import GuestSessionCreate, GuestSessionResponse
from app.schemas.ticket import TicketCreate, TicketResponse, TicketFeedback, TicketListResponse
from app.schemas.common import TicketStatusEnum
from app.ml.pipeline import process_ticket_ai

router = APIRouter(prefix="", tags=["Citizen Portal"])


def generate_unique_ticket_id(db: Session) -> str:
    """Generates a memorable, unique KMRL ticket ID: e.g. KMRL-2026-X8F2"""
    current_year = datetime.now().year
    chars = string.ascii_uppercase + string.digits
    for _ in range(10):
        suffix = "".join(random.choices(chars, k=4))
        candidate_id = f"KMRL-{current_year}-{suffix}"
        existing = db.query(Ticket).filter(Ticket.id == candidate_id).first()
        if not existing:
            return candidate_id
    # Fallback with 6 characters
    suffix = "".join(random.choices(chars, k=6))
    return f"KMRL-{current_year}-{suffix}"


@router.post(
    "/sessions/create",
    response_model=GuestSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Guest Session",
    description="Initializes a friction-free guest session for a commuter without requiring passwords or sign-in.",
)
def create_guest_session(
    payload: GuestSessionCreate = None,
    db: Session = Depends(get_db),
):
    import uuid
    guest_id_str = (
        payload.guest_identifier 
        if (payload and payload.guest_identifier and payload.guest_identifier.strip()) 
        else f"guest_{uuid.uuid4().hex[:12]}"
    )
    session_obj = GuestSession(guest_identifier=guest_id_str)
    db.add(session_obj)
    db.commit()
    db.refresh(session_obj)
    return session_obj


@router.post(
    "/tickets/submit",
    response_model=TicketResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit Grievance / Query",
    description=(
        "Submits a commuter query or grievance. Optional GPS coordinates are recorded strictly for source "
        "credibility and rapid incident dispatch reach. Automatically triggers the Tri-Tier KMRL AI Pipeline."
    ),
)
def submit_ticket(
    ticket_in: TicketCreate,
    db: Session = Depends(get_db),
):
    # 1. Verify guest session if provided
    if ticket_in.guest_session_id:
        guest_sess = db.query(GuestSession).filter(GuestSession.id == ticket_in.guest_session_id).first()
        if guest_sess:
            guest_sess.last_active = datetime.now(timezone.utc)
            db.add(guest_sess)

    # 2. Process query via KMRL AI/ML pipeline
    ai_result = process_ticket_ai(ticket_in.query_text)

    # 3. Create Ticket record
    ticket_id = generate_unique_ticket_id(db)
    ticket_obj = Ticket(
        id=ticket_id,
        guest_session_id=ticket_in.guest_session_id,
        query_text=ticket_in.query_text,
        user_latitude=ticket_in.user_latitude,
        user_longitude=ticket_in.user_longitude,
        location_accuracy=ticket_in.location_accuracy,
        predicted_category=ai_result.predicted_category,
        classification_confidence=ai_result.classification_confidence,
        priority=ai_result.priority.value,
        sla_hours=ai_result.sla_hours,
        requires_human_intervention=ai_result.requires_human_intervention,
        ai_response=ai_result.ai_response,
        ai_referenced_docs=ai_result.ai_referenced_docs,
        status=ai_result.initial_status.value,
    )

    db.add(ticket_obj)
    db.commit()
    db.refresh(ticket_obj)

    return ticket_obj


@router.get(
    "/tickets/track/{ticket_id}",
    response_model=TicketResponse,
    summary="Track Ticket by ID",
    description="Retrieves real-time ticket resolution status, AI guidance, and official actions.",
)
def track_ticket(
    ticket_id: str,
    db: Session = Depends(get_db),
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id.strip()).first()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket '{ticket_id}' not found. Please verify the ticket reference number.",
        )
    return ticket


@router.post(
    "/tickets/{ticket_id}/feedback",
    response_model=TicketResponse,
    summary="Submit Commuter Feedback",
    description=(
        "Commuter feedback on automated AI resolution. Marking Satisfied auto-closes the ticket. "
        "Marking 'Need Human Help' instantly escalates the ticket to the KMRL official triage queue."
    ),
)
def submit_ticket_feedback(
    ticket_id: str,
    feedback: TicketFeedback,
    db: Session = Depends(get_db),
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id.strip()).first()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket '{ticket_id}' not found.",
        )

    ticket.is_user_satisfied = feedback.is_user_satisfied
    ticket.user_feedback_comment = feedback.user_feedback_comment
    ticket.updated_at = datetime.now(timezone.utc)

    if feedback.is_user_satisfied:
        ticket.status = TicketStatusEnum.CLOSED.value
    else:
        ticket.status = TicketStatusEnum.ESCALATED.value
        ticket.requires_human_intervention = True

    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


@router.get(
    "/tickets/session/{guest_session_id}",
    response_model=TicketListResponse,
    summary="Get All Tickets for Guest Session",
    description="Returns all tickets previously submitted within a specific browser guest session.",
)
def get_session_tickets(
    guest_session_id: str,
    db: Session = Depends(get_db),
):
    tickets = (
        db.query(Ticket)
        .filter(Ticket.guest_session_id == guest_session_id)
        .order_by(desc(Ticket.created_at))
        .all()
    )
    return TicketListResponse(total=len(tickets), items=tickets)

