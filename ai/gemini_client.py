import logging
from typing import Dict, Any, Optional

import google.generativeai as genai
from api.config import settings

logger = logging.getLogger(__name__)

class GeminiClient:
    """
    Skeleton wrapper for interacting with the Google Gemini API to generate insights.
    """
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model_name = settings.GEMINI_MODEL_NAME
        self.client_initialized = False

        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.client_initialized = True
                logger.info("Gemini API successfully configured with model: %s", self.model_name)
            except Exception as e:
                logger.error("Failed to configure Gemini API client: %s", str(e))
        else:
            logger.warning("GEMINI_API_KEY not found in environment. Running in AI mock-response mode.")

    def generate_sales_summary(self, kpi_data: Dict[str, Any]) -> str:
        """
        Generates an executive narrative summary of sales KPIs.
        """
        prompt = (
            f"You are an expert CPG analytics consultant. Summarize the following sales performance data: "
            f"{kpi_data}. Highlight top performers, flags, and actionable next steps."
        )
        logger.info("Generating sales summary with Gemini API.")
        return self._generate_response(prompt, default_response=(
            "Executive Summary (Mock AI Insight):\n"
            "- Overall sales performance is healthy with consistent quarter-over-quarter revenue growth.\n"
            "- Northeast region is outperforming, driven by beverages category sales.\n"
            "- Recommendation: Increase inventory for high-velocity brands in lagging Southern territories."
        ))

    def generate_forecast_explanation(self, forecast_summary: Dict[str, Any]) -> str:
        """
        Generates a summary explaining forecasting output to business stakeholders.
        """
        prompt = (
            f"Explain the following revenue forecast projection to non-technical business partners: "
            f"{forecast_summary}. Describe what the trend suggests for demand planning."
        )
        logger.info("Generating forecast explanation with Gemini API.")
        return self._generate_response(prompt, default_response=(
            "Demand Planning Explanation (Mock AI Insight):\n"
            "- The 30-day outlook shows an upward trend in category sales.\n"
            "- Seasonal adjustments suggest a spike matching summer category demand peaks.\n"
            "- Suggestion: Coordinate with warehouse logistics to accommodate the forecasted volume increases."
        ))

    def _generate_response(self, prompt: str, default_response: str) -> str:
        """
        Calls Gemini API using the generativeai library or returns default mockup content if offline.
        """
        if not self.client_initialized:
            logger.debug("AI client not initialized. Returning fallback response.")
            return default_response
            
        try:
            model = genai.GenerativeModel(self.model_name)
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error("Failed to call Gemini API: %s. Returning fallback response.", str(e))
            return f"{default_response}\n\n(Note: Fallback used due to API error: {str(e)})"
