"""
Create all database tables directly from ORM models on Neon PostgreSQL.
This bypasses Alembic and uses SQLAlchemy metadata.create_all() for a clean schema.
"""
import asyncio
import ssl
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

# Import all models so they register with Base.metadata
from backend.models import (
    Base, User, Organization, OrganizationMember, Project, ProjectMember,
    Queue, RetryPolicy, Job, ScheduledJob, JobExecution, JobLog,
    Worker, WorkerHeartbeat, DeadLetterQueue,
)
from backend.core.config import settings


def get_adapted_url() -> str:
    url = settings.DATABASE_URL.strip("'\"")
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if "postgresql" in url and "?" in url:
        url = url.split("?")[0]
    return url


async def create_tables():
    url = get_adapted_url()
    print(f"Connecting to: {url[:50]}...")

    engine = create_async_engine(
        url,
        echo=True,
        connect_args={"ssl": True} if "postgresql" in url else {},
    )

    async with engine.begin() as conn:
        # Enable uuid-ossp extension
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
        print("Enabled uuid-ossp extension")

        # Drop all existing tables (cascade)
        await conn.execute(text("""
            DO $$ DECLARE
                r RECORD;
            BEGIN
                FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
                    EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
                END LOOP;
            END $$;
        """))
        print("Dropped all existing tables")

        # Create all tables from ORM models
        await conn.run_sync(Base.metadata.create_all)
        print("Created all tables from ORM models!")

    # List tables
    async with engine.connect() as conn:
        result = await conn.execute(text(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename"
        ))
        tables = [row[0] for row in result.fetchall()]
        print(f"\nCreated {len(tables)} tables:")
        for t in tables:
            print(f"  - {t}")

    await engine.dispose()
    print("\nDone! Database schema created successfully.")


if __name__ == "__main__":
    asyncio.run(create_tables())
