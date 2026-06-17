import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from api.config import settings

logger = logging.getLogger(__name__)

# Base class for declarative models
Base = declarative_base()

# SQLAlchemy engine setup (using standard thread-safe configuration)
engine = create_engine(
    settings.database_url,
    echo=settings.DEBUG,
    pool_pre_ping=True,  # Test connections before using them to prevent stale connections
    pool_size=10,
    max_overflow=20
)

# Sessionmaker configured for SQLAlchemy 2.x transactions
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

def init_db() -> None:
    """
    Initializes the database schema by creating all tables defined under `Base`.
    In production, this should ideally be managed by migrations (e.g., Alembic).
    """
    try:
        logger.info("Initializing database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized successfully.")
    except Exception as e:
        logger.error("Error creating database tables: %s", str(e))
        raise

@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Context manager to safely retrieve and close a SQLAlchemy Session.
    Useful for batch scripts, notebooks, or tasks outside FastAPI endpoints.
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
