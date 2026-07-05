from backend.worker.main import JobWorker
import asyncio

async def run_worker():
    worker = JobWorker()
    await worker.start()

if __name__ == "__main__":
    asyncio.run(run_worker())
