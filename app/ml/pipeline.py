import json
import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

from app.schemas.common import PriorityEnum, TicketStatusEnum
from app.ml.classifier import classifier
from app.ml.priority_engine import evaluate_priority
from app.ml.rag_engine import rag_engine

logger = logging.getLogger(__name__)


class TicketAIResult(BaseModel):
    predicted_category: str
    classification_confidence: float
    priority: PriorityEnum
    sla_hours: int
    requires_human_intervention: bool
    ai_response: str
    ai_referenced_docs: Optional[str] = None
    initial_status: TicketStatusEnum


def process_ticket_ai(query_text: str) -> TicketAIResult:
    """
    Unified Tri-Tier AI/ML Processing Pipeline:
    1. Categorizes request via KMRL TF-IDF + Logistic Regression Classifier.
    2. Evaluates priority, SLA hours, and escalation flags via KMRL Rule Engine.
    3. Retrieves policy clauses and generates grounded guidance via KMRL Chroma + Gemini RAG.
    """
    clean_text = query_text.strip()

    # Tier 1: ML Classification
    clf_res = classifier.predict(clean_text)
    predicted_category = clf_res["predicted_category"]
    confidence = clf_res["confidence"]

    # Tier 2: Priority & Escalation Evaluation
    priority_res = evaluate_priority(clean_text)
    priority = priority_res["priority"]
    sla_hours = priority_res["sla_hours"]
    requires_human = priority_res["requires_human_intervention"]

    # If priority engine provides a stronger category hint for safety/legal, respect it
    if priority_res.get("category_hint") in ["Safety", "Legal & Compliance"] and priority == PriorityEnum.CRITICAL:
        predicted_category = priority_res["category_hint"]

    # Tier 3: RAG Guidance Generation
    rag_res = rag_engine.query(clean_text)
    ai_response = rag_res["answer"]
    sources = rag_res.get("sources", [])
    referenced_docs_json = json.dumps(sources) if sources else None

    # Lifecycle Status assignment
    initial_status = TicketStatusEnum.ESCALATED if requires_human else TicketStatusEnum.AUTO_RESOLVED

    return TicketAIResult(
        predicted_category=predicted_category,
        classification_confidence=confidence,
        priority=priority,
        sla_hours=sla_hours,
        requires_human_intervention=requires_human,
        ai_response=ai_response,
        ai_referenced_docs=referenced_docs_json,
        initial_status=initial_status,
    )

