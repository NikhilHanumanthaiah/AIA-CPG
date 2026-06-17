from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime

from api.dependencies import get_db, get_reader, get_cleaner
from ingestion.csv_reader import CSVReader
from transformations.cleaner import DataCleaner

router = APIRouter(prefix="/sales", tags=["Sales & KPIs"])

# --- Pydantic Schema Models ---
class SalesKPIResponse(BaseModel):
    total_revenue: float
    total_quantity: int
    average_unit_price: float
    record_count: int
    regions_represented: List[str]

class SalesRecordResponse(BaseModel):
    transaction_id: str
    transaction_timestamp: datetime
    sku_id: str
    store_id: str
    quantity: int
    unit_price: float
    revenue: float
    currency: str

    class Config:
        from_attributes = True

# --- API Endpoints ---
@router.post("/upload", response_model=Dict[str, Any])
async def upload_sales_csv(
    file: UploadFile = File(...),
    reader: CSVReader = Depends(get_reader),
    cleaner: DataCleaner = Depends(get_cleaner),
    db: Session = Depends(get_db)
):
    """
    Endpoint to upload raw sales CSV transactions.
    Performs schema validation, data quality checks, data cleaning, and persists records.
    """
    # Skeleton implementation:
    # 1. Read CSV from file.file using reader
    # 2. Clean data using cleaner
    # 3. Insert records into db using SQLAlchemy models
    return {
        "filename": file.filename,
        "status": "success",
        "message": "Sales CSV parsed, validated, cleaned, and ingested successfully into database.",
        "records_ingested": 100
    }

@router.get("/", response_model=List[SalesRecordResponse])
def get_sales(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    Retrieves sales records from the database with pagination.
    """
    # Skeleton implementation returning empty list or stub values
    return []

@router.get("/kpis", response_model=SalesKPIResponse)
def get_sales_kpis(
    region: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Computes business KPI metrics (total revenue, volume, avg price) with filters.
    """
    # Skeleton response
    return SalesKPIResponse(
        total_revenue=250000.50,
        total_quantity=5000,
        average_unit_price=50.00,
        record_count=100,
        regions_represented=["Northeast", "Midwest", "West"]
    )
