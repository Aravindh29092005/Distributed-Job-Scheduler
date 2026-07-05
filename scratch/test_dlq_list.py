import asyncio
from backend.db.session import AsyncSessionLocal
from backend.services.dlq import DLQService

async def test():
    async with AsyncSessionLocal() as db:
        service = DLQService(db)
        try:
            items, count = await service.list()
            print("Successfully listed DLQ items, count:", count)
            print("Items:", items)
        except Exception as e:
            print("Error listing DLQ items:", type(e), e)
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
