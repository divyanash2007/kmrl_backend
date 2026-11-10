from datetime import datetime, timezone
import json
from typing import Optional, List, Dict
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, case

from app.config import settings
from app.database import get_db
from app.models.ticket import Ticket
from app.models.audit_log import OfficialAuditLog
from app.schemas.official import (
    OfficialLoginRequest,
    OfficialLoginResponse,
    OfficialResolveRequest,
    OfficialAnalyticsResponse,
    OfficialAuditLogResponse,
)
from app.schemas.ticket import TicketResponse, TicketListResponse
from app.schemas.common import TicketStatusEnum, OfficialActionEnum, PriorityEnum
from app.api.deps import verify_safe_key

router = APIRouter(prefix="/official", tags=["Officials Safe-Key Portal"])


@router.post(
    "/auth",
    response_model=OfficialLoginResponse,
    summary="Official Safe-Key Authentication",
    description="Authenticates authorized KMRL metro officials using a high-security Safe Key passphrase.",
)
def official_login(payload: OfficialLoginRequest):
    if payload.safe_key.strip() != settings.SAFE_KEY.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid KMRL Official Safe Key.",
        )
    return OfficialLoginResponse(
        authenticated=True,
        token=settings.SAFE_KEY,
        message="KMRL Official Safe Key verified successfully.",
    )


@router.get(
    "/analytics",
    response_model=OfficialAnalyticsResponse,
    summary="Grievance Analytics & KPI Metrics",
    description="Aggregates system-wide volume, first-contact auto-resolution rates, and category/priority breakdowns.",
)
def get_official_analytics(
    db: Session = Depends(get_db),
    _safe_key: str = Depends(verify_safe_key),
):
    total = db.query(Ticket).count()

    auto_resolved = (
        db.query(Ticket)
        .filter(Ticket.status.in_([TicketStatusEnum.AUTO_RESOLVED.value, TicketStatusEnum.CLOSED.value]))
        .count()
    )
    escalated = (
        db.query(Ticket)
        .filter(Ticket.status == TicketStatusEnum.ESCALATED.value)
        .count()
    )
    official_resolved = (
        db.query(Ticket)
        .filter(Ticket.status == TicketStatusEnum.OFFICIAL_RESOLVED.value)
        .count()
    )

    fcr_rate = round((auto_resolved / total * 100), 2) if total > 0 else 100.0

    # Priority counts
    priority_rows = db.query(Ticket.priority, func.count(Ticket.id)).group_by(Ticket.priority).all()
    priority_breakdown = {p.value: 0 for p in [PriorityEnum.CRITICAL, PriorityEnum.HIGH, PriorityEnum.MEDIUM, PriorityEnum.LOW]}
    for p_name, cnt in priority_rows:
        priority_breakdown[p_name] = cnt

    # Category counts
    category_rows = db.query(Ticket.predicted_category, func.count(Ticket.id)).group_by(Ticket.predicted_category).all()
    category_breakdown = {cat: cnt for cat, cnt in category_rows}

    # Status counts
    status_rows = db.query(Ticket.status, func.count(Ticket.id)).group_by(Ticket.status).all()
    status_breakdown = {s.value: 0 for s in TicketStatusEnum}
    for s_name, cnt in status_rows:
        status_breakdown[s_name] = cnt

    return OfficialAnalyticsResponse(
        total_queries=total,
        auto_resolved_count=auto_resolved,
        escalated_count=escalated,
        official_resolved_count=official_resolved,
        first_contact_resolution_rate=fcr_rate,
        priority_breakdown=priority_breakdown,
        category_breakdown=category_breakdown,
        status_breakdown=status_breakdown,
    )


@router.get(
    "/queue",
    response_model=TicketListResponse,
    summary="Human Intervention & Escalation Queue",
    description=(
        "Retrieves the live queue of tickets flagged for official review or emergency dispatch. "
        "Includes incident GPS coordinates for credible dispatch reach."
    ),
)
def get_escalation_queue(
    status_filter: Optional[TicketStatusEnum] = Query(None, alias="status"),
    category: Optional[str] = Query(None),
    priority: Optional[PriorityEnum] = Query(None),
    requires_human_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _safe_key: str = Depends(verify_safe_key),
):
    query = db.query(Ticket)

    if status_filter:
        query = query.filter(Ticket.status == status_filter.value)
    if category:
        query = query.filter(Ticket.predicted_category == category)
    if priority:
        query = query.filter(Ticket.priority == priority.value)
    if requires_human_only:
        query = query.filter(Ticket.requires_human_intervention.is_(True))

    # Priority sort: CRITICAL first, then HIGH, MEDIUM, LOW, then newest
    priority_order = case(
        (Ticket.priority == "CRITICAL", 1),
        (Ticket.priority == "EMERGENCY", 1),
        (Ticket.priority == "HIGH", 2),
        (Ticket.priority == "MEDIUM", 3),
        (Ticket.priority == "LOW", 4),
        else_=5,
    )

    total = query.count()
    items = query.order_by(priority_order, desc(Ticket.created_at)).offset(offset).limit(limit).all()

    return TicketListResponse(total=total, items=items)


@router.post(
    "/resolve/{ticket_id}",
    response_model=TicketResponse,
    summary="Record Official Resolution",
    description="Records formal official investigation findings, resolution directives, and closes/resolves the ticket.",
)
async def resolve_ticket(
    ticket_id: str,
    request: Request,
    db: Session = Depends(get_db),
    _safe_key: str = Depends(verify_safe_key),
):
    # Parse payload supporting both JSON Content-Type and raw body text
    try:
        body_data = await request.json()
    except Exception:
        try:
            raw = (await request.body()).decode("utf-8")
            body_data = json.loads(raw) if raw else {}
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Malformed request body: {str(e)}",
            )

    if isinstance(body_data, str):
        try:
            body_data = json.loads(body_data)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Input should be a valid JSON dictionary.",
            )

    try:
        payload = OfficialResolveRequest(**body_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

    ticket = db.query(Ticket).filter(Ticket.id == ticket_id.strip()).first()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket '{ticket_id}' not found.",
        )

    now = datetime.now(timezone.utc)
    ticket.official_id = payload.official_id
    ticket.official_notes = payload.official_notes
    ticket.status = payload.outcome.value
    ticket.resolved_at = now
    ticket.updated_at = now

    # Record official audit log
    audit_entry = OfficialAuditLog(
        ticket_id=ticket.id,
        official_id=payload.official_id,
        action=OfficialActionEnum.RESOLVED.value,
        notes=payload.official_notes,
    )
    db.add(audit_entry)
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    return ticket


@router.get(
    "/audit-logs/{ticket_id}",
    response_model=List[OfficialAuditLogResponse],
    summary="Get Ticket Official Audit History",
    description="Retrieves the chronological record of official actions and directives taken for a ticket.",
)
def get_ticket_audit_logs(
    ticket_id: str,
    db: Session = Depends(get_db),
    _safe_key: str = Depends(verify_safe_key),
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id.strip()).first()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket '{ticket_id}' not found.",
        )

    logs = (
        db.query(OfficialAuditLog)
        .filter(OfficialAuditLog.ticket_id == ticket.id)
        .order_by(desc(OfficialAuditLog.created_at))
        .all()
    )
    return logs

