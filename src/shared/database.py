"""Database configuration with SQLite/PostgreSQL support"""
import os
from sqlmodel import create_engine, SQLModel, Session as SQLModelSession
from sqlalchemy.orm import sessionmaker
from typing import Generator
import logging

logger = logging.getLogger(__name__)

# Support both SQLite and PostgreSQL via environment variable
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./vela.db"  # Default to SQLite
)

# PostgreSQL: postgresql://user:password@host:port/dbname
# SQLite: sqlite:///./vela.db

# Configure engine based on database type
if "sqlite" in DATABASE_URL:
    engine = create_engine(
        DATABASE_URL,
        echo=True if os.getenv("DEBUG") else False,
        connect_args={"check_same_thread": False}
    )
else:
    # PostgreSQL configuration
    engine = create_engine(
        DATABASE_URL,
        echo=True if os.getenv("DEBUG") else False,
        pool_size=5,
        pool_pre_ping=True
    )

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=SQLModelSession)


def create_db_and_tables():
    """Create all database tables"""
    SQLModel.metadata.create_all(engine)
    logger.info("Database tables created successfully")


def get_session() -> Generator[SQLModelSession, None, None]:
    """Get a database session"""
    with SQLModelSession(engine) as session:
        yield session


def init_database():
    """Initialize the database with default data if needed"""
    create_db_and_tables()

    # Check if this is first run (no admin users)
    with SQLModelSession(engine) as session:
        from src.shared.models import AdminUser
        from sqlmodel import select

        admin_exists = session.exec(select(AdminUser).limit(1)).first()
        if not admin_exists:
            logger.info("No admin users found. First-run setup required.")
            return False

    return True  # Database already initialized