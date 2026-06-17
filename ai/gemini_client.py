import logging
from typing import Dict, Any, Optional

import google.generativeai as genai
from api.config import settings

logger = logging.getLogger(__name__)

class GeminiClient:
    """
    Wrapper for interacting with the Google Gemini API to generate insights and translate text to SQL.
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
        
        region = kpi_data.get("region", "All")
        category = kpi_data.get("category", "All")
        total_rev = kpi_data.get("total_revenue", 0.0)
        total_qty = kpi_data.get("total_quantity", 0)
        
        fallback_msg = (
            f"API Fallback: Sales metrics summary for Region: '{region}', Category: '{category}'.\n"
            f"Total Revenue is ${total_rev:,.2f} over a total volume of {total_qty:,} units sold."
        )
        return self._generate_response(prompt, default_response=fallback_msg)

    def generate_forecast_explanation(self, forecast_summary: Dict[str, Any]) -> str:
        """
        Generates a summary explaining forecasting output to business stakeholders.
        """
        prompt = (
            f"Explain the following revenue forecast projection to non-technical business partners: "
            f"{forecast_summary}. Describe what the trend suggests for demand planning."
        )
        logger.info("Generating forecast explanation with Gemini API.")
        
        region = forecast_summary.get("region", "All")
        category = forecast_summary.get("category", "All")
        proj_rev = forecast_summary.get("30_day_projected_revenue", 0.0)
        trend = forecast_summary.get("trend_direction", "flat")
        
        fallback_msg = (
            f"API Fallback: Demand planning projection for Region: '{region}', Category: '{category}'.\n"
            f"The 30-day projected revenue is ${proj_rev:,.2f} with an overall trend indicating a '{trend}' direction."
        )
        return self._generate_response(prompt, default_response=fallback_msg)

    def generate_sql(self, question: str) -> str:
        """
        Translates a natural language question into a PostgreSQL query based on the database schema.
        """
        schema_info = """
        Database Schema:
        
        Table: dim_product
        Columns:
        - sku_id: VARCHAR(50), Primary Key
        - category: VARCHAR(100), not null, index
        - brand: VARCHAR(100), not null
        - package_size: VARCHAR(50)
        - launch_date: DATE
        
        Table: dim_store
        Columns:
        - store_id: VARCHAR(50), Primary Key
        - region: VARCHAR(100), not null, index
        - state: VARCHAR(50), not null
        - city: VARCHAR(100), not null
        
        Table: customer_master
        Columns:
        - customer_id: VARCHAR(50), Primary Key
        - customer_name: VARCHAR(100), not null
        - email: VARCHAR(100), not null
        - region: VARCHAR(100), not null
        
        Table: fact_sales
        Columns:
        - transaction_id: VARCHAR(100), Primary Key
        - transaction_timestamp: TIMESTAMP WITH TIME ZONE, not null, index
        - sku_id: VARCHAR(50), foreign key to dim_product.sku_id
        - store_id: VARCHAR(50), foreign key to dim_store.store_id
        - customer_id: VARCHAR(50), foreign key to customer_master.customer_id
        - quantity: INTEGER, not null
        - unit_price: NUMERIC(10, 2), not null
        - revenue: NUMERIC(12, 2), not null
        - currency: VARCHAR(10)
        """
        
        prompt = (
            f"You are a PostgreSQL expert translating business questions to SQL.\n"
            f"{schema_info}\n"
            f"Question: \"{question}\"\n"
            f"Instructions:\n"
            f"Generate a valid PostgreSQL query for the question. Output ONLY the raw SQL query. "
            f"Do not write any markdown code block syntax, backticks, or explanations."
        )
        logger.info("Generating SQL from question with Gemini.")
        
        # Build a robust programmatic fallback based on question content
        q_lower = question.lower()
        if "revenue" in q_lower or "sales" in q_lower:
            fallback = "SELECT sum(revenue) as total_revenue FROM fact_sales"
            if "region" in q_lower:
                for r in ["northeast", "midwest", "south", "west", "central", "east"]:
                    if r in q_lower:
                        fallback = f"SELECT sum(fs.revenue) as total_revenue FROM fact_sales fs JOIN dim_store ds ON fs.store_id = ds.store_id WHERE lower(ds.region) = '{r}'"
                        break
        elif "product" in q_lower or "sku" in q_lower:
            fallback = "SELECT count(*) as product_count FROM dim_product"
        elif "store" in q_lower:
            fallback = "SELECT count(*) as store_count FROM dim_store"
        elif "customer" in q_lower:
            fallback = "SELECT count(*) as customer_count FROM customer_master"
        else:
            fallback = "SELECT * FROM fact_sales LIMIT 5"
            
        if not self.client_initialized:
            logger.debug("AI client not initialized. Returning fallback response.")
            sql_out = fallback
        else:
            try:
                model = genai.GenerativeModel(self.model_name)
                response = model.generate_content(prompt)
                sql_out = response.text
            except Exception as e:
                logger.error("Failed to call Gemini API to generate SQL: %s. Returning fallback SQL.", str(e))
                sql_out = fallback
        
        # Clean potential markdown wrapping
        sql_out = sql_out.strip()
        if sql_out.startswith("```sql"):
            sql_out = sql_out[6:]
        if sql_out.startswith("```"):
            sql_out = sql_out[3:]
        if sql_out.endswith("```"):
            sql_out = sql_out[:-3]
        return sql_out.strip()

    def explain_query_results(self, question: str, sql: str, results: list) -> str:
        """
        Explains query results in business terms.
        """
        prompt = (
            f"You are a CPG executive analyst. Explain the answer to this business question based on the query results.\n"
            f"Question: \"{question}\"\n"
            f"SQL Query Executed: {sql}\n"
            f"Query Results: {results}\n\n"
            f"Provide a clear, professional, and concise narrative explanation explaining exactly what these results mean for business planning."
        )
        logger.info("Explaining SQL query results with Gemini.")
        
        if not self.client_initialized:
            logger.debug("AI client not initialized. Returning fallback response.")
            return f"API Fallback: Displaying raw query results because AI client is not initialized.\nQuery: `{sql}`\nResults: {results}"
            
        try:
            model = genai.GenerativeModel(self.model_name)
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error("Failed to call Gemini API to explain results: %s. Returning fallback explanation.", str(e))
            return (
                f"API Fallback: Displaying raw query results because Gemini API failed or was rate-limited.\n"
                f"Error details: {str(e)}\n"
                f"Query Executed: `{sql}`\n"
                f"Results: {results}"
            )

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

