import asyncio
from backend.db.session import engine, db_url

async def main():
    print(f"Configured DB URL: {db_url}")
    try:
        async with engine.connect() as conn:
            print("Successfully connected!")
            # Try to run a simple query
            from sqlalchemy import text
            res = await conn.execute(text("SELECT 1"))
            print(f"Query test (SELECT 1): {res.scalar()}")
    except Exception as e:
        print(f"Error connecting: {e}")

if __name__ == "__main__":
    asyncio.run(main())
