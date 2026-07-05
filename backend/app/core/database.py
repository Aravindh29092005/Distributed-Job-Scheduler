import socket
from typing import AsyncGenerator
from urllib.parse import urlparse

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from backend.app.core.config import settings
from backend.app.core.logger import get_logger

logger = get_logger(__name__)


def is_db_reachable(url: str) -> bool:
    """Synchronous check if database port is open (2s timeout)."""
    try:
        check_url = url
        if check_url.startswith("postgresql+asyncpg://"):
            check_url = check_url.replace("postgresql+asyncpg://", "postgresql://", 1)
        if "?" in check_url:
            check_url = check_url.split("?")[0]
        parsed = urlparse(check_url)
        host = parsed.hostname or "localhost"
        port = parsed.port or 5432
        with socket.create_connection((host, port), timeout=2.0):
            return True
    except Exception:
        return False


# Resolve Database URL and connection parameters dynamically
raw_url = settings.DATABASE_URL.strip("'\"")
db_url = raw_url
if db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

# Strip query parameters for asyncpg compatibility, using standard ssl=True instead
connect_args = {}
if "postgresql" in db_url:
    if "?" in db_url:
        db_url = db_url.split("?")[0]
    connect_args = {"ssl": True}

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
        connect_args=connect_args,
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
