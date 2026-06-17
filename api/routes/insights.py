from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from pydantic import BaseModel

from api.dependencies import get_db, get_gemini_client
from ai.gemini_client import GeminiClient

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

# --- API Endpoints ---
@router.post("/sales-summary", response_model=InsightResponse)
def generate_sales_summary(
    payload: InsightRequest,
    ai_client: GeminiClient = Depends(get_gemini_client),
    db: Session = Depends(get_db)
):
    """
    Retrieves sales metrics and calls the Gemini API to construct an executive text summary.
    """
    # Skeleton:
    # 1. Fetch sales aggregate metrics for region/category from db
    # 2. Call ai_client.generate_sales_summary
    mock_kpi_data = {
        "region": payload.region or "All",
        "category": payload.category or "All",
        "total_revenue": 250000.50,
        "total_quantity": 5000
    }
    narrative = ai_client.generate_sales_summary(mock_kpi_data)
    
    return InsightResponse(
        insight_type="Sales Summary",
        region=payload.region or "All Regions",
        category=payload.category or "All Categories",
        narrative=narrative
    )

@router.post("/forecast-explanation", response_model=InsightResponse)
def generate_forecast_explanation(
    payload: InsightRequest,
    ai_client: GeminiClient = Depends(get_gemini_client),
    db: Session = Depends(get_db)
):
    """
    Retrieves forecast data and calls Gemini API to construct a forecast summary explaining trends.
    """
    # Skeleton:
    # 1. Fetch upcoming forecasted revenue totals from db
    # 2. Call ai_client.generate_forecast_explanation
    mock_forecast_summary = {
        "region": payload.region or "All",
        "category": payload.category or "All",
        "30_day_projected_revenue": 450000.00,
        "trend_direction": "increasing"
    }
    narrative = ai_client.generate_forecast_explanation(mock_forecast_summary)
    
    return InsightResponse(
        insight_type="Forecast Explanation",
        region=payload.region or "All Regions",
        category=payload.category or "All Categories",
        narrative=narrative
    )
