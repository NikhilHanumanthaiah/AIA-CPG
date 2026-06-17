# ADR 0001: Initial Architecture Design

## Status
Accepted

## Context
We are building a production-oriented analytics platform for a Consumer Packaged Goods (CPG) company to handle CSV ingestion, data cleaning, relational storage in PostgreSQL, revenue forecasting using Facebook Prophet, and generative summaries using Google Gemini API. The system needs to be clean, modular, and easily extendable.

## Decisions

1. **Backend Framework: FastAPI**
   - Chosen for its performance, asynchronous request handling support, and auto-generated OpenAPI documentation.
   - Built-in Dependency Injection provides decoupling of DB sessions, ML forecasting models, and LLM API clients.

2. **ORM: SQLAlchemy 2.0 (Type-Annotated style)**
   - Utilizes `Mapped` and `mapped_column` type annotations to provide structural type checking.
   - Separate models defined for `fact_sales` and core dimensions to match business domain structures.

3. **Frontend UI: Streamlit**
   - Enables fast prototyping of analytical charts, dashboards, and AI interactions without writing heavy JavaScript.
   - Standard HTTP client communication to interact with the backend FastAPI.

4. **Forecasting Engine: Facebook Prophet**
   - Chosen for its time-series robustness and native support for trends and seasonalities.
   - Configured with a fallback mock service to ensure baseline runs complete even if local binary dependencies are absent.

5. **AI Insights Layer: Google Gemini (google-generativeai)**
   - Utilizes Gemini's large context windows to process summaries of historical sales KPIs and projected demand lines.

6. **Containerization: Docker and Compose**
   - Isolates the database, API server, and Streamlit user interface into standard multi-container environments.

## Consequences
- Clean boundaries between ingestion, transformation, analytics, database models, and service interfaces.
- The project is fully independent of specific frontend/backend bindings, allowing developers to switch UI layers or models in isolation.
