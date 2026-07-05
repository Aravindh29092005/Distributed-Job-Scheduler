import socket
from typing import AsyncGenerator
from urllib.parse import urlparse

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from backend.core.config import settings
from backend.core.logging import get_logger

logger = get_logger(__name__)


def is_db_reachable(url: str) -> bool:
    """Synchronous check if database port is open (1s timeout)."""
    try:
        parsed = urlparse(url)
        host = parsed.hostname or "localhost"
        port = parsed.port or 5432
        with socket.create_connection((host, port), timeout=1.0):
            return True
    except Exception:
        return False


# Resolve Database URL and connection parameters dynamically
db_url = settings.DATABASE_URL
is_reachable = is_db_reachable(db_url)

if not is_reachable:
    logger.warning(
        "db_connection_failed_falling_back_to_sqlite",
        target_url=db_url,
        fallback_url="sqlite+aiosqlite:///job_platform.db",
    )
    db_url = "sqlite+aiosqlite:///job_platform.db"
    engine = create_async_engine(
        db_url,
        echo=False,
    )
else:
    engine = create_async_engine(
        db_url,
        echo=False,
        pool_size=20,
        max_overflow=10,
        pool_pre_ping=True,
    )

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for obtaining database sessions."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
