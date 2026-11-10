import re
from typing import Dict, Any, List
from app.schemas.common import PriorityEnum

# KMRL Rule heuristics directly mapped from KMRL/Rule-engine/rule_engine.py
KMRL_RULES = {
    "Maintenance": [
        {
            "keywords": ["malfunction", "breakdown", "equipment failure", "not working", "stuck in lift"],
            "priority": "HIGH"
        },
        {
            "keywords": ["repair", "maintenance", "servicing", "cleaning", "dirty coach"],
            "priority": "MEDIUM"
        },
    ],

    "Safety": [
        {
            "keywords": [
                "accident", "injury", "fire", "emergency exit", "emergency", "medical", 
                "fainted", "collapsed", "theft", "stolen", "assault", "harassment", "track", "fallen"
            ],
            "priority": "CRITICAL"
        },
        {
            "keywords": ["hazard", "unsafe condition", "safety violation", "exposed wire", "smoke"],
            "priority": "HIGH"
        },
    ],

    "Finance": [
        {
            "keywords": ["invoice", "payment", "reimbursement", "double charged", "deducted twice"],
            "priority": "MEDIUM"
        },
        {
            "keywords": ["budget", "financial statement", "expenditure"],
            "priority": "MEDIUM"
        },
    ],

    "Human Resources": [
        {
            "keywords": ["leave application", "salary revision", "employee benefits"],
            "priority": "MEDIUM"
        },
        {
            "keywords": ["attendance", "employee transfer", "recruitment"],
            "priority": "LOW"
        },
    ],

    "Operations": [
        {
            "keywords": ["train schedule", "service disruption", "platform allocation", "train delayed", "delayed"],
            "priority": "HIGH"
        },
        {
            "keywords": ["train frequency", "operational planning", "headway", "first train", "last train"],
            "priority": "MEDIUM"
        },
    ],

    "Procurement": [
        {
            "keywords": ["purchase order", "vendor quotation", "tender"],
            "priority": "MEDIUM"
        },
        {
            "keywords": ["vendor selection", "procurement request"],
            "priority": "MEDIUM"
        },
    ],

    "Passenger Grievances": [
        {
            "keywords": ["passenger complaint", "refund", "ticket issue", "recharge failed", "gate not opening"],
            "priority": "MEDIUM"
        },
        {
            "keywords": ["poor service", "staff behaviour", "passenger feedback", "general inquiry"],
            "priority": "LOW"
        },
    ],

    "Legal & Compliance": [
        {
            "keywords": ["legal notice", "court order", "lawsuit", "vigilance", "cvc complaint"],
            "priority": "CRITICAL"
        },
        {
            "keywords": ["contract dispute", "regulatory violation", "compliance", "rti"],
            "priority": "HIGH"
        },
    ],
}

SLA_MAP = {
    PriorityEnum.CRITICAL: 1,  # 1 hour response
    PriorityEnum.EMERGENCY: 1, # 1 hour response
    PriorityEnum.HIGH: 4,      # 4 hours response
    PriorityEnum.MEDIUM: 12,   # 12 hours response
    PriorityEnum.LOW: 24,      # 24 hours response
}

PRIORITY_WEIGHT = {
    "CRITICAL": 4,
    "HIGH": 3,
    "MEDIUM": 2,
    "LOW": 1
}


def evaluate_priority(text: str) -> Dict[str, Any]:
    """
    Evaluates text urgency using KMRL rules and returns PriorityEnum, SLA hours,
    and whether immediate human dispatch / intervention is required.
    """
    clean_text = text.lower()
    matched_rules: List[Dict[str, Any]] = []

    for category, rules in KMRL_RULES.items():
        for rule in rules:
            matched_keywords = [
                kw for kw in rule["keywords"]
                if re.search(r'\b' + re.escape(kw) + r'\b', clean_text) or kw in clean_text
            ]
            if matched_keywords:
                matched_rules.append({
                    "category": category,
                    "matched_keywords": matched_keywords,
                    "priority": rule["priority"]
                })

    if not matched_rules:
        # Default priority is LOW (24h SLA)
        return {
            "priority": PriorityEnum.LOW,
            "sla_hours": SLA_MAP[PriorityEnum.LOW],
            "requires_human_intervention": False,
            "category_hint": None,
            "matched_keywords": []
        }

    # Sort to find highest priority rule
    matched_rules.sort(
        key=lambda x: PRIORITY_WEIGHT.get(x["priority"], 1),
        reverse=True
    )

    top_match = matched_rules[0]
    p_str = top_match["priority"]
    priority_enum = PriorityEnum.CRITICAL if p_str == "CRITICAL" else PriorityEnum(p_str)
    requires_human = (priority_enum == PriorityEnum.CRITICAL)

    return {
        "priority": priority_enum,
        "sla_hours": SLA_MAP[priority_enum],
        "requires_human_intervention": requires_human,
        "category_hint": top_match["category"],
        "matched_keywords": top_match["matched_keywords"]
    }

