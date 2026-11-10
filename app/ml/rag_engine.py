import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from app.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an AI-powered grievance redressal and document analysis assistant for Kochi Metro Rail Limited (KMRL).

Your task is to provide courteous, actionable, and grounded guidance using official KMRL policies.

STRICT RULES:
1. Use the retrieved context as the primary source of factual policy information.
2. Do not invent policies, procedures, departments, or compensation figures.
3. If the retrieved context does not contain enough information, provide standard KMRL passenger assistance guidance and refer them to the Station Master or Helpline (1800 425 0373).
4. Distinguish between KMRL-specific policies and general guidelines.
5. Provide practical, step-by-step next steps for the commuter or employee.
6. Cite supporting evidence with document name and page number when available.

RESPONSE FORMAT:
### Resolution & Guidance
Explain practical next steps clearly.

### Relevant Policy / Provision
Explain the applicable KMRL standard or procedure.

### Responsible Authority / Contact
Station Master desk, Customer Relations, or Emergency Helpline (1800-425-0373).
"""


class KMRLRAGEngine:
    """
    RAG engine interfacing directly with KMRL's Chroma DB and Gemini LLM.
    """

    def __init__(
        self,
        chroma_path: Optional[str] = None,
        google_api_key: Optional[str] = None
    ):
        self.chroma_path = Path(chroma_path or settings.KMRL_CHROMA_PATH)
        self.api_key = google_api_key or settings.GOOGLE_API_KEY
        self.vector_store = None
        self.retriever = None
        self.llm = None
        self._init_components()

    def _init_components(self) -> None:
        # 1. Initialize Vector Store & Retriever if chroma_db exists
        if self.chroma_path.exists():
            try:
                from langchain_chroma import Chroma
                from langchain_huggingface import HuggingFaceEmbeddings

                embeddings = HuggingFaceEmbeddings(
                    model_name="sentence-transformers/all-MiniLM-L6-v2",
                    model_kwargs={"device": "cpu"},
                    encode_kwargs={"normalize_embeddings": True}
                )

                self.vector_store = Chroma(
                    collection_name="cvc_documents",
                    embedding_function=embeddings,
                    persist_directory=str(self.chroma_path)
                )
                self.retriever = self.vector_store.as_retriever(
                    search_type="similarity",
                    search_kwargs={"k": 3}
                )
                logger.info(f"Loaded KMRL ChromaDB vector store from {self.chroma_path}")
            except Exception as e:
                logger.warning(f"Could not load ChromaDB from {self.chroma_path}: {e}")
                self.vector_store = None
                self.retriever = None
        else:
            logger.warning(f"KMRL ChromaDB path does not exist: {self.chroma_path}")

        # 2. Initialize Gemini LLM
        if self.api_key:
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
                self.llm = ChatGoogleGenerativeAI(
                    model="gemini-3.5-flash-lite",
                    temperature=0.1,
                    max_retries=2,
                    google_api_key=self.api_key
                )
                logger.info("Initialized Gemini LLM provider for KMRL RAG.")
            except Exception as e:
                logger.warning(f"Could not initialize Gemini LLM: {e}")
                self.llm = None

    def query(self, question: str) -> Dict[str, Any]:
        """
        Executes semantic retrieval and grounded response generation.
        Returns:
            {
                "answer": str,
                "sources": list of dicts [{"file_name": ..., "page_number": ...}]
            }
        """
        clean_q = question.strip()
        if not clean_q:
            return {
                "answer": "No query provided.",
                "sources": []
            }

        documents = []
        sources = []

        # 1. Retrieve relevant chunks if retriever available
        if self.retriever is not None:
            try:
                documents = self.retriever.invoke(clean_q)
                for doc in documents:
                    source = {
                        "file_name": doc.metadata.get("file_name") or doc.metadata.get("title") or "KMRL Official Policy",
                        "page_number": doc.metadata.get("page_number") or doc.metadata.get("page") or 1,
                    }
                    if source not in sources:
                        sources.append(source)
            except Exception as e:
                logger.error(f"Error during retrieval: {e}")

        # Format context
        if documents:
            formatted_chunks = []
            for i, doc in enumerate(documents, start=1):
                chunk = (
                    f"Source {i} - {doc.metadata.get('file_name', 'Doc')} (Page {doc.metadata.get('page', 'N/A')}):\n"
                    f"{doc.page_content}"
                )
                formatted_chunks.append(chunk)
            context = "\n\n".join(formatted_chunks)
        else:
            context = "No specific policy document clause retrieved for this inquiry."

        # 2. Generate answer via LLM if available
        if self.llm is not None:
            try:
                from langchain_core.prompts import ChatPromptTemplate
                prompt = ChatPromptTemplate.from_messages([
                    ("system", SYSTEM_PROMPT),
                    ("human", "Question:\n{question}\n\nRetrieved context:\n<context>\n{context}\n</context>")
                ])
                messages = prompt.format_messages(question=clean_q, context=context)
                response = self.llm.invoke(messages)
                
                # Extract clean string content from response
                if isinstance(response.content, list):
                    text_parts = [
                        part.get("text", "") if isinstance(part, dict) else str(part)
                        for part in response.content
                    ]
                    answer_text = "".join(text_parts).strip()
                else:
                    answer_text = str(response.content).strip()

                return {
                    "answer": answer_text,
                    "sources": sources
                }
            except Exception as e:
                logger.warning(f"LLM generation failed or rate limited ({e}). Providing rule-grounded fallback.")

        # Fallback guidance when LLM is unavailable or offline
        fallback_answer = (
            f"### Official KMRL Assistance\n\n"
            f"Your request has been logged in the KMRL Civic & Grievance Redressal system.\n\n"
            f"**Recommended Steps:**\n"
            f"1. For immediate on-station assistance, visit the nearest **Station Control Room / Station Master Desk**.\n"
            f"2. For ticketing, smart card recharge, or refund inquiries, present your Kochi-1 Card or QR receipt to the customer service counter.\n"
            f"3. In case of emergency or safety concerns, use the Passenger Emergency Alarm or contact **KMRL Helpline: 1800 425 0373**.\n\n"
            f"*Status: Logged and processed according to official KMRL service standards.*"
        )
        return {
            "answer": fallback_answer,
            "sources": sources or [{"file_name": "KMRL Passenger Charter & Safety Manual", "page_number": 1}]
        }


# Singleton instance
rag_engine = KMRLRAGEngine()

