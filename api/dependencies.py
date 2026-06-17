from typing import Generator
from sqlalchemy.orm import Session

from database.connection import SessionLocal
from ai.gemini_client import GeminiClient
from forecasting.model import ForecastingService
from transformations.cleaner import DataCleaner
from ingestion.csv_reader import CSVReader

def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides a transactional database session scope.
    Closes the session automatically when the request completes.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_gemini_client() -> GeminiClient:
    """
    FastAPI dependency providing the Gemini AI client wrapper.
    """
    return GeminiClient()

def get_forecast_service() -> ForecastingService:
    """
    FastAPI dependency providing the Prophet forecasting service.
    """
    return ForecastingService()

def get_cleaner() -> DataCleaner:
    """
    FastAPI dependency providing the data transformations cleaner.
    """
    return DataCleaner()

def get_reader() -> CSVReader:
    """
    FastAPI dependency providing the CSV reader and validator.
    """
    return CSVReader()
