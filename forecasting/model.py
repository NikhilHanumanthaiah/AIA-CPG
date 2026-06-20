import logging
from typing import Any, Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)

# Note: We import Prophet inside functions or use optional imports
# so that the skeleton is safe even if compiled C libraries of Prophet aren't fully resolved yet.
try:
    from prophet import Prophet
except ImportError:
    Prophet = None
    logger.warning(
        "Prophet not installed or could not be imported. Running in Prophet-mock mode."
    )


class ForecastingService:
    """
    Skeleton class for generating revenue forecasts using Facebook Prophet.
    """

    def __init__(self, model_version: str = "v1.0.0"):
        self.model_version = model_version

    def prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Prepares sales data for Prophet:
        - Expects columns: 'transaction_timestamp' (as ds) and 'revenue' (as y).
        - Aggregates daily.
        """
        logger.info("Preparing data for forecasting.")
        if df.empty:
            return pd.DataFrame(columns=["ds", "y"])

        prepared_df = df.copy()

        # Ensure timestamp is datetime and date-only
        prepared_df["ds"] = pd.to_datetime(prepared_df["transaction_timestamp"]).dt.date

        # Rename revenue column to target y
        prepared_df = prepared_df.rename(columns={"revenue": "y"})

        # Group by date to get daily aggregated revenue
        daily_df = prepared_df.groupby("ds")["y"].sum().reset_index()
        daily_df["ds"] = pd.to_datetime(daily_df["ds"])

        return daily_df

    def train_and_forecast(
        self,
        df: pd.DataFrame,
        periods: int = 30,
        region: Optional[str] = None,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Trains a Prophet model on the provided historical DataFrame and outputs a forecast list.
        """
        logger.info(
            "Training forecast model (Region: %s, Category: %s)", region, category
        )

        prepared_df = self.prepare_data(df)

        if len(prepared_df) < 2:
            logger.warning(
                "Insufficient data points for forecasting. Returning mock forecast."
            )
            return self._generate_mock_forecast(periods, region, category)

        if Prophet is not None:
            try:
                # Actual Prophet model setup
                model = Prophet(
                    daily_seasonality=False,
                    weekly_seasonality=True,
                    yearly_seasonality=True,
                )
                model.fit(prepared_df)

                future = model.make_future_dataframe(periods=periods, freq="D")
                forecast = model.predict(future)

                # Filter to only the predicted dates (not historical dates)
                predictions = forecast.tail(periods)

                results = []
                for _, row in predictions.iterrows():
                    results.append(
                        {
                            "forecast_date": row["ds"].date(),
                            "region": region or "All Regions",
                            "category": category or "All Categories",
                            "predicted_revenue": float(row["yhat"]),
                            "model_version": self.model_version,
                        }
                    )
                return results
            except Exception as e:
                logger.error(
                    "Error during Prophet execution: %s. Falling back to mock.", str(e)
                )

        return self._generate_mock_forecast(periods, region, category)

    def evaluate_model(
        self, actual: pd.DataFrame, forecast: pd.DataFrame
    ) -> Dict[str, float]:
        """
        Skeleton method to evaluate model performance using MAPE / RMSE.
        """
        logger.info("Evaluating forecasting model performance.")
        # Stub values for performance metrics
        return {
            "mape": 0.125,  # Mean Absolute Percentage Error (e.g. 12.5%)
            "rmse": 1540.23,  # Root Mean Squared Error
            "model_version": self.model_version,
        }

    def _generate_mock_forecast(
        self, periods: int, region: Optional[str], category: Optional[str]
    ) -> List[Dict[str, Any]]:
        """
        Generates dummy predictions for skeleton demo verification.
        """
        from datetime import date, timedelta

        start_date = date.today()

        return [
            {
                "forecast_date": start_date + timedelta(days=i),
                "region": region or "All Regions",
                "category": category or "All Categories",
                "predicted_revenue": float(1000.0 + (i * 50) + (i % 7) * 200),
                "model_version": self.model_version,
            }
            for i in range(1, periods + 1)
        ]
