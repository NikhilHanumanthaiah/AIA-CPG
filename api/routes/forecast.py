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
import pandas as pd
from database.models import SalesFact, StoreDimension, ProductDimension, ForecastResult

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
    # 1. Fetch actual sales from db
    query = db.query(SalesFact)
    if payload.region and payload.region != "All Regions":
        query = query.join(StoreDimension).filter(StoreDimension.region == payload.region)
    if payload.category and payload.category != "All Categories":
        query = query.join(ProductDimension).filter(ProductDimension.category == payload.category)
        
    sales_records = query.all()
    
    # Format database records into a pandas DataFrame
    data = [
        {
            "transaction_timestamp": r.transaction_timestamp,
            "revenue": float(r.revenue)
        }
        for r in sales_records
    ]
    df = pd.DataFrame(data, columns=["transaction_timestamp", "revenue"])
    
    # 2. Call forecaster.train_and_forecast
    region_str = payload.region or "All Regions"
    category_str = payload.category or "All Categories"
    
    forecast_results = forecaster.train_and_forecast(
        df,
        periods=payload.days_to_predict,
        region=region_str,
        category=category_str
    )
    
    # 3. Store result in forecast_results table
    # Delete existing forecasts for the same region and category to avoid duplicates
    db.query(ForecastResult).filter(
        ForecastResult.region == region_str,
        ForecastResult.category == category_str
    ).delete()
    
    db_items = [
        ForecastResult(
            forecast_date=item["forecast_date"],
            region=item["region"],
            category=item["category"],
            predicted_revenue=item["predicted_revenue"],
            model_version=item["model_version"],
            prediction_timestamp=datetime.utcnow()
        )
        for item in forecast_results
    ]
    
    db.add_all(db_items)
    db.commit()
    
    return {
        "status": "success",
        "message": f"Successfully generated {payload.days_to_predict}-day revenue forecast.",
        "model_version": forecaster.model_version,
        "region_filtered": region_str,
        "category_filtered": category_str
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
    region_str = region or "All Regions"
    category_str = category or "All Categories"
    
    forecasts = db.query(ForecastResult).filter(
        ForecastResult.region == region_str,
        ForecastResult.category == category_str
    ).order_by(ForecastResult.forecast_date.asc()).all()
    
    return forecasts
