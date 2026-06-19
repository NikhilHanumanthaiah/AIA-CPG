from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime

from api.dependencies import get_db
from api.services.upload_service import UploadService

router = APIRouter(prefix="/upload", tags=["Data Upload Control"])

# --- Pydantic Schema Models ---
class TableItem(BaseModel):
    name: str
    display_name: str
    columns: Dict[str, str] = {}
    required_columns: List[str] = []

class SupportedTablesResponse(BaseModel):
    tables: List[TableItem]

class ValidationErrorDetail(BaseModel):
    row_index: int
    column: str
    value: Optional[str] = None
    reason: str

class UploadStatisticsResponse(BaseModel):
    status: str
    table_name: str
    file_name: str
    total_rows: int
    inserted_rows: int
    duplicate_rows: int
    removed_rows: int
    invalid_rows: int
    final_loaded_rows: int
    start_time: str
    end_time: str
    processing_time_seconds: int
    validation_errors: List[ValidationErrorDetail] = []

# --- API Endpoints ---
@router.get("/tables", response_model=SupportedTablesResponse)
def get_uploadable_tables():
    """
    Retrieves list of all registered databases and tables supported for CSV file uploads.
    """
    tables = UploadService.get_supported_tables()
    return SupportedTablesResponse(tables=tables)

@router.post("/", response_model=UploadStatisticsResponse)
async def process_file_upload(
    file: UploadFile = File(...),
    target_table: str = Form(...),
    column_mapping: Optional[str] = Form(None),
    data_types: Optional[str] = Form(None),
    dq_rules: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Handles CSV upload, schema verification, duplicates pruning, insertion, and stats logging.
    """
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file format. Please upload a valid CSV file."
        )

    try:
        content = await file.read()
        stats = UploadService.process_upload(
            db=db,
            file_name=file.filename,
            file_content=content,
            target_table=target_table,
            column_mapping=column_mapping,
            data_types=data_types,
            dq_rules=dq_rules
        )
        return UploadStatisticsResponse(**stats)
    except ValueError as ve:
        # Invalid schema, unsupported table, or validation error
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except RuntimeError as re:
        # Database write or connection errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(re)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during processing: {str(e)}"
        )
