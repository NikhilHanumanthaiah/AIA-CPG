import pandas as pd

from forecasting.model import ForecastingService


def test_forecasting_service_prepare_data_empty():
    """
    Tests that prepare_data returns an empty DataFrame with proper columns
    when input data is empty.
    """
    service = ForecastingService()
    df = pd.DataFrame()
    prepared = service.prepare_data(df)
    assert prepared.empty
    assert list(prepared.columns) == ["ds", "y"]


def test_forecasting_service_prepare_data_valid():
    """
    Tests that prepare_data aggregates daily revenue correctly and formats columns.
    """
    service = ForecastingService()
    df = pd.DataFrame(
        [
            {"transaction_timestamp": "2026-06-17T12:00:00Z", "revenue": 100.0},
            {"transaction_timestamp": "2026-06-17T15:00:00Z", "revenue": 150.0},
            {"transaction_timestamp": "2026-06-18T10:00:00Z", "revenue": 200.0},
        ]
    )
    prepared = service.prepare_data(df)
    assert len(prepared) == 2  # Aggregated into daily buckets
    assert pd.api.types.is_datetime64_any_dtype(prepared["ds"])
    # Check y values
    assert prepared.loc[prepared["ds"] == "2026-06-17", "y"].values[0] == 250.0
    assert prepared.loc[prepared["ds"] == "2026-06-18", "y"].values[0] == 200.0


def test_forecasting_service_insufficient_data():
    """
    Tests that train_and_forecast falls back to a structured mock forecast
    when fewer than 2 days of historical data are provided.
    """
    service = ForecastingService()
    # Single data point
    df = pd.DataFrame(
        [
            {"transaction_timestamp": "2026-06-17T12:00:00Z", "revenue": 100.0},
        ]
    )
    forecast = service.train_and_forecast(
        df, periods=5, region="Northeast", category="Beverages"
    )
    assert len(forecast) == 5
    assert forecast[0]["region"] == "Northeast"
    assert forecast[0]["category"] == "Beverages"
    assert "predicted_revenue" in forecast[0]
    assert "forecast_date" in forecast[0]


def test_forecasting_service_evaluate_model():
    """
    Tests that the evaluation helper returns appropriate structure and metrics.
    """
    service = ForecastingService()
    metrics = service.evaluate_model(pd.DataFrame(), pd.DataFrame())
    assert "mape" in metrics
    assert "rmse" in metrics
    assert metrics["model_version"] == "v1.0.0"
