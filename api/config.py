from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    """
    Application Settings loaded from environment variables and/or a .env file.
    """
    # Application Configuration
    APP_NAME: str = "CPG Sales Analytics Platform"
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    DEBUG: bool = True

    # Database Configuration
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "cpg_sales_db"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432

    # FastAPI Server
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    # Streamlit Server
    STREAMLIT_PORT: int = 8501
    API_URL: str = "http://localhost:8000"  # Endpoint for the frontend to connect to the backend

    # Gemini API Configuration
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL_NAME: str = "gemini-1.5-flash"

    @property
    def database_url(self) -> str:
        """
        Generates the standard PostgreSQL connection URL.
        """
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

# Instantiate a global settings object for DI and application usage
settings = Settings()
