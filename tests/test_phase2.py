import pytest
from app.schemas.common import PriorityEnum, TicketStatusEnum
from app.ml.classifier import classifier
from app.ml.priority_engine import evaluate_priority
from app.ml.rag_engine import rag_engine
from app.ml.pipeline import process_ticket_ai, TicketAIResult


def test_classifier_predictions():
    """Verify pre-trained KMRL model predicts valid categories and confidence."""
    # 1. Maintenance query
    res1 = classifier.predict("The escalator at Platform 1 has stopped working and needs repair")
    assert res1["predicted_category"] in [
        "Maintenance", "Operations", "Safety", "Passenger Grievances", "Finance", 
        "Human Resources", "Procurement", "Legal & Compliance"
    ]
    assert 0.0 <= res1["confidence"] <= 1.0

    # 2. Safety query
    res2 = classifier.predict("An employee reported an unsafe condition involving exposed electrical wire")
    assert res2["predicted_category"] == "Safety"
    assert res2["confidence"] > 0.5

    # 3. Finance query
    res3 = classifier.predict("The finance department has received an invoice for Rs. 25,000 for equipment servicing")
    assert res3["predicted_category"] == "Finance"
    assert res3["confidence"] > 0.5


def test_priority_engine_heuristics():
    """Verify KMRL rule-based priority engine urgency scoring and SLA assignment."""
    # 1. Critical / Safety Emergency -> SLA 1h & auto-escalation
    crit_res = evaluate_priority("Emergency! Passenger suffered an injury and collapsed on the track")
    assert crit_res["priority"] == PriorityEnum.CRITICAL
    assert crit_res["sla_hours"] == 1
    assert crit_res["requires_human_intervention"] is True
    assert "injury" in crit_res["matched_keywords"] or "emergency" in crit_res["matched_keywords"]

    # 2. High Priority -> Breakdown / Schedule disruption -> SLA 4h
    high_res = evaluate_priority("Major train schedule disruption due to signalling breakdown")
    assert high_res["priority"] == PriorityEnum.HIGH
    assert high_res["sla_hours"] == 4
    assert high_res["requires_human_intervention"] is False

    # 3. Medium Priority -> Routine maintenance / Ticket issue -> SLA 12h
    med_res = evaluate_priority("Requesting refund for ticket issue, recharge deducted twice")
    assert med_res["priority"] == PriorityEnum.MEDIUM
    assert med_res["sla_hours"] == 12
    assert med_res["requires_human_intervention"] is False

    # 4. Low Priority -> General passenger feedback -> SLA 24h
    low_res = evaluate_priority("General passenger feedback regarding friendly staff behaviour")
    assert low_res["priority"] == PriorityEnum.LOW
    assert low_res["sla_hours"] == 24
    assert low_res["requires_human_intervention"] is False


def test_rag_engine_response():
    """Verify RAG engine returns courteous, structured KMRL guidance and citations."""
    query = "What are the vigilance procedures and safety guidelines at Kochi Metro stations?"
    result = rag_engine.query(query)
    assert "answer" in result
    assert len(result["answer"]) > 50
    assert "sources" in result
    assert isinstance(result["sources"], list)


def test_unified_pipeline_critical_flow():
    """Verify full pipeline properly escalates critical issues with immediate dispatch flag."""
    query = "Fire detected near emergency exit door! Immediate assistance required!"
    ai_result: TicketAIResult = process_ticket_ai(query)

    assert ai_result.priority == PriorityEnum.CRITICAL
    assert ai_result.requires_human_intervention is True
    assert ai_result.initial_status == TicketStatusEnum.ESCALATED
    assert ai_result.sla_hours == 1
    assert len(ai_result.ai_response) > 20


def test_unified_pipeline_auto_resolved_flow():
    """Verify full pipeline auto-resolves general inquiries with SLA and reference docs."""
    query = "Where can I service and recharge my Kochi-1 metro smart card?"
    ai_result: TicketAIResult = process_ticket_ai(query)

    assert ai_result.priority in [PriorityEnum.MEDIUM, PriorityEnum.LOW]
    assert ai_result.requires_human_intervention is False
    assert ai_result.initial_status == TicketStatusEnum.AUTO_RESOLVED
    assert ai_result.sla_hours in [12, 24]
    assert len(ai_result.ai_response) > 20

