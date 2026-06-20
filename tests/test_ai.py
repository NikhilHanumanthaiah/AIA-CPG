import unittest
from unittest.mock import MagicMock, patch

from ai.gemini_client import GeminiClient


def test_gemini_client_fallback_when_uninitialized():
    """
    Tests that the client returns proper structured fallback messages
    when the Google Gemini API key is missing.
    """
    with patch("ai.gemini_client.settings") as mock_settings:
        mock_settings.GEMINI_API_KEY = None
        mock_settings.GEMINI_MODEL_NAME = "gemini-1.5-flash"

        client = GeminiClient()
        assert not client.client_initialized

        kpi_data = {
            "region": "Northeast",
            "category": "Beverages",
            "total_revenue": 100.0,
            "total_quantity": 10,
        }
        summary = client.generate_sales_summary(kpi_data)
        assert "API Fallback:" in summary
        assert "Northeast" in summary
        assert "Beverages" in summary
        assert "$100.00" in summary

        forecast_summary = {
            "region": "West",
            "category": "Dairy",
            "30_day_projected_revenue": 500.0,
            "trend_direction": "increasing",
        }
        explanation = client.generate_forecast_explanation(forecast_summary)
        assert "API Fallback:" in explanation
        assert "West" in explanation
        assert "$500.00" in explanation

        sql = client.generate_sql("Show total revenue")
        assert "SELECT sum(revenue)" in sql


def test_gemini_client_sql_markdown_stripping():
    """
    Tests that generate_sql correctly strips potential markdown wrapping
    (such as ```sql and ```) from generated SQL strings.
    """
    with patch("ai.gemini_client.settings") as mock_settings:
        mock_settings.GEMINI_API_KEY = "dummy_key"
        mock_settings.GEMINI_MODEL_NAME = "gemini-1.5-flash"

        with patch("google.generativeai.configure"):
            with patch("google.generativeai.GenerativeModel") as mock_model_class:
                mock_model = MagicMock()
                mock_model_class.return_value = mock_model

                # Case 1: wrapped in ```sql ... ```
                mock_response = MagicMock()
                mock_response.text = "```sql\nSELECT * FROM fact_sales;\n```"
                mock_model.generate_content.return_value = mock_response

                client = GeminiClient()
                assert client.client_initialized

                sql = client.generate_sql("Give me sales")
                assert sql == "SELECT * FROM fact_sales;"

                # Case 2: wrapped in plain ```
                mock_response.text = "```SELECT * FROM dim_product;```"
                mock_model.generate_content.return_value = mock_response

                sql = client.generate_sql("Give me products")
                assert sql == "SELECT * FROM dim_product;"
