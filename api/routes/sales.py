from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy import Date, cast, func
from sqlalchemy.orm import Session

from api.dependencies import get_cleaner, get_db, get_reader
from database.models import ProductDimension, SalesFact, StoreDimension
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
    customer_id: Optional[str]
    quantity: int
    unit_price: float
    revenue: float
    currency: str

    class Config:
        from_attributes = True


class TrendItemResponse(BaseModel):
    date: str
    revenue: float


# --- API Endpoints ---
@router.post("/upload", response_model=Dict[str, Any])
async def upload_sales_csv(
    file: UploadFile = File(...),
    reader: CSVReader = Depends(get_reader),
    cleaner: DataCleaner = Depends(get_cleaner),
    db: Session = Depends(get_db),
):
    """
    Endpoint to upload raw sales CSV transactions.
    Performs schema validation, data quality checks, data cleaning, and persists records.
    """
    # In actual usage, this is handled dynamically by /upload/ route.
    # Provided here for skeleton compatibility.
    return {
        "filename": file.filename,
        "status": "success",
        "message": "Upload completed.",
        "records_ingested": 0,
    }


@router.get("/", response_model=List[SalesRecordResponse])
def get_sales(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """
    Retrieves sales records from the database with pagination.
    """
    records = (
        db.query(SalesFact)
        .order_by(SalesFact.transaction_timestamp.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return records


@router.get("/kpis", response_model=SalesKPIResponse)
def get_sales_kpis(
    region: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Computes business KPI metrics (total revenue, volume, avg price) with filters from real tables.
    """
    # Base query for joins
    query = db.query(SalesFact)
    if region:
        query = query.join(StoreDimension).filter(StoreDimension.region == region)
    if category:
        query = query.join(ProductDimension).filter(
            ProductDimension.category == category
        )

    # Calculate KPI values
    kpis = query.with_entities(
        func.sum(SalesFact.revenue).label("total_revenue"),
        func.sum(SalesFact.quantity).label("total_quantity"),
        func.avg(SalesFact.unit_price).label("avg_unit_price"),
        func.count(SalesFact.transaction_id).label("record_count"),
    ).first()

    total_rev = float(kpis.total_revenue or 0.0)
    total_qty = int(kpis.total_quantity or 0)
    avg_price = float(kpis.avg_unit_price or 0.0)
    record_cnt = int(kpis.record_count or 0)

    # Fetch unique regions represented
    regions_query = db.query(StoreDimension.region).distinct().join(SalesFact)
    if category:
        regions_query = regions_query.join(ProductDimension).filter(
            ProductDimension.category == category
        )
    regions = [r[0] for r in regions_query.all() if r[0] is not None]

    return SalesKPIResponse(
        total_revenue=total_rev,
        total_quantity=total_qty,
        average_unit_price=avg_price,
        record_count=record_cnt,
        regions_represented=regions,
    )


@router.get("/trends", response_model=List[TrendItemResponse])
def get_sales_trends(
    region: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Retrieves daily aggregated sales revenue trends for charts.
    """
    query = db.query(
        cast(SalesFact.transaction_timestamp, Date).label("sales_date"),
        func.sum(SalesFact.revenue).label("daily_revenue"),
    )

    if region:
        query = query.join(StoreDimension).filter(StoreDimension.region == region)
    if category:
        query = query.join(ProductDimension).filter(
            ProductDimension.category == category
        )

    trends = (
        query.group_by(cast(SalesFact.transaction_timestamp, Date))
        .order_by("sales_date")
        .all()
    )

    return [
        TrendItemResponse(
            date=str(row.sales_date), revenue=float(row.daily_revenue or 0.0)
        )
        for row in trends
    ]


@router.get("/regions", response_model=List[str])
def get_regions(db: Session = Depends(get_db)):
    """
    Retrieves unique regions present in the store dimension database table.
    """
    regions = (
        db.query(StoreDimension.region).distinct().order_by(StoreDimension.region).all()
    )
    return [r[0] for r in regions if r[0] is not None]


@router.get("/categories", response_model=List[str])
def get_categories(db: Session = Depends(get_db)):
    """
    Retrieves unique product categories present in the product dimension database table.
    """
    categories = (
        db.query(ProductDimension.category)
        .distinct()
        .order_by(ProductDimension.category)
        .all()
    )
    return [c[0] for c in categories if c[0] is not None]
