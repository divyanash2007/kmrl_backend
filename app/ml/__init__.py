"""KMRL AI / ML Processing Pipeline for CiviSeva.
Directly interfaces with pre-trained KMRL models, rule engines, and RAG vector store.
"""

from app.ml.pipeline import process_ticket_ai, TicketAIResult

__all__ = ["process_ticket_ai", "TicketAIResult"]

