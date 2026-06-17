from api.routes.sales import router as sales_router
from api.routes.forecast import router as forecast_router
from api.routes.insights import router as insights_router

__all__ = ["sales_router", "forecast_router", "insights_router"]
