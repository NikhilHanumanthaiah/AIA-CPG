from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from ai.gemini_client import GeminiClient
from api.dependencies import get_db, get_gemini_client

router = APIRouter(prefix="/insights", tags=["AI Insights"])


# --- Pydantic Schema Models ---
class InsightRequest(BaseModel):
    region: Optional[str] = None
    category: Optional[str] = None


class InsightResponse(BaseModel):
    insight_type: str
    region: str
    category: str
    narrative: str


class QueryRequest(BaseModel):
    question: str


class QueryResponse(BaseModel):
    sql: str
    results: List[Dict[str, Any]]
    explanation: str


# --- API Endpoints ---
@router.post("/sales-summary", response_model=InsightResponse)
def generate_sales_summary(
    payload: InsightRequest,
    ai_client: GeminiClient = Depends(get_gemini_client),
    db: Session = Depends(get_db),
):
    """
    Retrieves sales metrics and calls the Gemini API to construct an executive text summary.
    """
    # 1. Fetch real sales metrics dynamically to pass to summary generator
    # Base query for joins
    from sqlalchemy import func

    from database.models import ProductDimension, SalesFact, StoreDimension

    query = db.query(SalesFact)
    if payload.region and payload.region != "All Regions":
        query = query.join(StoreDimension).filter(
            StoreDimension.region == payload.region
        )
    if payload.category and payload.category != "All Categories":
        query = query.join(ProductDimension).filter(
            ProductDimension.category == payload.category
        )

    kpis = query.with_entities(
        func.sum(SalesFact.revenue).label("total_revenue"),
        func.sum(SalesFact.quantity).label("total_quantity"),
    ).first()

    kpi_data = {
        "region": payload.region or "All Regions",
        "category": payload.category or "All Categories",
        "total_revenue": float(kpis.total_revenue or 0.0) if kpis else 0.0,
        "total_quantity": int(kpis.total_quantity or 0) if kpis else 0,
    }

    narrative = ai_client.generate_sales_summary(kpi_data)

    return InsightResponse(
        insight_type="Sales Summary",
        region=payload.region or "All Regions",
        category=payload.category or "All Categories",
        narrative=narrative,
    )


@router.post("/forecast-explanation", response_model=InsightResponse)
def generate_forecast_explanation(
    payload: InsightRequest,
    ai_client: GeminiClient = Depends(get_gemini_client),
    db: Session = Depends(get_db),
):
    """
    Retrieves forecast data and calls Gemini API to construct a forecast summary explaining trends.
    """
    # Fetch upcoming forecast results
    from sqlalchemy import func

    from database.models import ForecastResult

    query = db.query(ForecastResult)
    if payload.region and payload.region != "All Regions":
        query = query.filter(ForecastResult.region == payload.region)
    if payload.category and payload.category != "All Categories":
        query = query.filter(ForecastResult.category == payload.category)

    forecast_sum = query.with_entities(
        func.sum(ForecastResult.predicted_revenue).label("total_pred")
    ).first()

    total_projected = float(forecast_sum.total_pred or 0.0) if forecast_sum else 0.0

    forecast_summary = {
        "region": payload.region or "All Regions",
        "category": payload.category or "All Categories",
        "30_day_projected_revenue": total_projected,
        "trend_direction": "increasing" if total_projected > 0 else "flat",
    }

    narrative = ai_client.generate_forecast_explanation(forecast_summary)

    return InsightResponse(
        insight_type="Forecast Explanation",
        region=payload.region or "All Regions",
        category=payload.category or "All Categories",
        narrative=narrative,
    )


@router.post("/query", response_model=QueryResponse)
def execute_natural_query(
    payload: QueryRequest,
    ai_client: GeminiClient = Depends(get_gemini_client),
    db: Session = Depends(get_db),
):
    """
    Translates a natural language question to SQL, runs it, and explains the results.
    """
    # 1. Translate question to SQL
    sql_query = ai_client.generate_sql(payload.question)

    # 2. Execute SQL against database
    results = []
    try:
        res = db.execute(text(sql_query))
        if res.returns_rows:
            for row in res.all():
                results.append(dict(row._mapping))
        else:
            db.commit()
            results = [{"status": "success", "rows_affected": res.rowcount}]
    except Exception as e:
        results = [{"error": str(e)}]

    # 3. Get explanation
    explanation = ai_client.explain_query_results(payload.question, sql_query, results)

    return QueryResponse(sql=sql_query, results=results, explanation=explanation)
