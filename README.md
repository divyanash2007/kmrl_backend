# KMRL CiviSeva — AI Backend API

Intelligent civic service and grievance management backend for **Kochi Metro Rail Limited (KMRL)**.

## Core Capabilities
- **Location-Agnostic Access**: Commuters can raise grievances with optional browser GPS coordinates attached strictly for source authenticity and physical dispatch reach.
- **Tri-Tier AI/ML Pipeline**:
  1. **TF-IDF + Logistic Regression Classifier**: Classifies queries across 8 KMRL operational verticals.
  2. **Rule-Based Urgency Engine**: Evaluates priority (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`) and SLA response windows.
  3. **RAG Guidance Engine**: Powered by LangChain, ChromaDB vector store, and Google Gemini (`gemini-3.5-flash-lite`) using official KMRL passenger manuals and SOPs.
- **Official Safe-Key Portal**: Authorized KMRL staff access with analytics, triage lists, and resolution logging.

## Tech Stack
- **Framework**: FastAPI (Python 3.11)
- **Database**: PostgreSQL (Supabase) via SQLAlchemy 2.0 & Psycopg 3
- **Migrations**: Alembic
- **Machine Learning**: scikit-learn, LangChain, ChromaDB, Google Generative AI

## Environment Variables
See `.env.example` for reference:
- `DATABASE_URL`: Supabase PostgreSQL connection string
- `SAFE_KEY`: KMRL metro personnel passphrase
- `GOOGLE_API_KEY`: Gemini API key
- `KMRL_MODEL_PATH`: Relative path to classifier (`data/model/document_classifier.joblib`)
- `KMRL_CHROMA_PATH`: Relative path to Chroma DB (`data/chroma_db`)
- `CORS_ORIGINS`: Allowed origins (e.g., frontend Railway URL)

## Deployment (Railway)
- Build automatically detected from `requirements.txt` and `runtime.txt`.
- Start Command: Handled by `Procfile`:
  ```
  web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
  ```
