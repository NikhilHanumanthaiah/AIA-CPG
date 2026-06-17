import logging
import sys
from api.config import settings

def setup_logging() -> None:
    """
    Sets up a standardized logging configuration for the entire application.
    """
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    
    # Define a clean, unified format for console output
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ],
        force=True  # Ensure that we overwrite default logging config
    )
    
    # Set logging level for third-party libraries to be less noisy
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.DEBUG else logging.WARNING
    )
    
    logger = logging.getLogger(__name__)
    logger.info("Logging has been initialized with level %s", settings.LOG_LEVEL)

# Setup logging automatically upon import
setup_logging()
