import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Initialize logging before any other module imports to capture early logs
import api.logging_config  # noqa: F401
from api.config import settings
from api.routes.forecast import router as forecast_router
from api.routes.insights import router as insights_router
from api.routes.sales import router as sales_router
from api.routes.upload import router as upload_router
from database.connection import init_db

logger = logging.getLogger(__name__)

# Initialize FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description="CPG Analytics platform API service providing sales ingestion, forecasting, and AI narrative generation.",
    version="1.0.0",
    debug=settings.DEBUG,
)

# Enable CORS (Cross-Origin Resource Sharing) for local frontend UI communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to the Streamlit host
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Startup event: Initialize database structure
@app.on_event("startup")
def on_startup():
    logger.info("Starting up CPG Sales API service...")
    if settings.APP_ENV != "testing":
        init_db()


# Register API Routers
app.include_router(sales_router, prefix="/api/v1")
app.include_router(forecast_router, prefix="/api/v1")
app.include_router(insights_router, prefix="/api/v1")
app.include_router(upload_router, prefix="/api/v1")


@app.get("/health", tags=["System"])
def health_check():
    """
    Standard API status health check endpoint.
    """
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "environment": settings.APP_ENV,
    }
