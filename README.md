# CPG Sales Analytics & Forecasting Platform

A production-oriented analytics platform built for a Consumer Packaged Goods (CPG) company to validate, clean, persist sales transactions, run Prophet forecasting, and generate AI insights using the Gemini API.

---

## 🛠️ Tech Stack

- **Backend:** Python 3.12+, FastAPI, SQLAlchemy 2.x, Pydantic v2
- **Database:** PostgreSQL 16
- **ML Engine:** Facebook Prophet, Pandas
- **AI Integration:** Google Gemini API (`google-generativeai`)
- **Frontend UI:** Streamlit
- **DevOps:** Docker, Docker Compose, Pytest

---

## 📁 Repository Structure

```
.
├── data/                  # Storage for input/output CSV datasets
│   ├── raw/
│   └── processed/
├── database/              # SQLAlchemy connection, Session, and model definitions
├── ingestion/             # CSV Readers, Schema validation, and Data Quality logic
├── transformations/       # Deduplication, null handling, and business rule cleaner
├── forecasting/           # Prophet time-series models and forecast generation
├── ai/                    # Google Gemini API wrapper for narrative insights
├── api/                   # FastAPI application layer (endpoints, dependency injection)
├── frontend/              # Streamlit dashboard UI app
├── tests/                 # Complete Pytest test suite
├── docs/                  # Architecture Decision Records (ADRs) and diagrams
├── docker/                # Containter definitions (Dockerfiles)
├── docker-compose.yml     # Multi-container local deployment orchestrator
├── requirements.txt       # Project python dependencies
└── pyproject.toml         # Build tool dependencies & lint/testing specifications
```

---

## 🚀 Getting Started

### Prerequisites

- Docker and Docker Compose
- Python 3.12 (if running locally without containers)

### Running via Docker Compose (Recommended)

1. Clone or navigate to the repository directory.
2. Create your `.env` configuration:
   ```bash
   cp .env.example .env
   ```
   Add your Google Gemini API key to `GEMINI_API_KEY`.
3. Launch the complete multi-container stack:
   ```bash
   docker compose up --build
   ```
4. Access services:
   - **Streamlit Frontend Dashboard:** [http://localhost:8501](http://localhost:8501)
   - **FastAPI API Swagger Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
   - **Database:** Postgres listening on `localhost:5432`

---

## 🧪 Testing

We use `pytest` for unit and integration testing.

To run tests locally:
```bash
pip install -r requirements.txt
pytest
```
*Note: The test suite uses an in-memory SQLite database configuration to ensure unit tests run fast and with zero database dependencies.*
