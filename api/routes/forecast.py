from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import date, datetime

from api.dependencies import get_db, get_forecast_service
from forecasting.model import ForecastingService

router = APIRouter(prefix="/forecast", tags=["Forecasting"])

# --- Pydantic Schema Models ---
class ForecastRunRequest(BaseModel):
    days_to_predict: int = 30
    region: Optional[str] = None
    category: Optional[str] = None

class ForecastItemResponse(BaseModel):
    forecast_date: date
    region: str
    category: str
    predicted_revenue: float
    model_version: str
    prediction_timestamp: datetime

    class Config:
        from_attributes = True

# --- API Endpoints ---
@router.post("/run", response_model=Dict[str, Any])
def run_forecast(
    payload: ForecastRunRequest,
    forecaster: ForecastingService = Depends(get_forecast_service),
    db: Session = Depends(get_db)
):
    """
    Triggers a Prophet forecast run.
    Fetches actuals, trains model, and saves forecast output to the database.
    """
    # Skeleton implementation:
    # 1. Fetch actual sales from db
    # 2. Call forecaster.train_and_forecast
    # 3. Store result in forecast_results table
    return {
        "status": "success",
        "message": f"Successfully generated {payload.days_to_predict}-day revenue forecast.",
        "model_version": forecaster.model_version,
        "region_filtered": payload.region or "All Regions",
        "category_filtered": payload.category or "All Categories"
    }

@router.get("/", response_model=List[ForecastItemResponse])
def get_forecast(
    region: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Retrieves forecasted revenue values from the database, filtered by region/category.
    """
    # Skeleton implementation: Returns dummy data or queries empty table
    dummy_timestamp = datetime.utcnow()
    return [
        ForecastItemResponse(
            forecast_date=date.today(),
            region=region or "All Regions",
            category=category or "All Categories",
            predicted_revenue=15400.99,
            model_version="v1.0.0",
            prediction_timestamp=dummy_timestamp
        )
    ]
