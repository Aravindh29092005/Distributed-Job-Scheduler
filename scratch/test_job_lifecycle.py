import asyncio
import httpx
import sqlite3

async def main():
    async with httpx.AsyncClient() as client:
        # Login
        login_res = await client.post('http://localhost:8000/api/auth/login', json={
            "email": "aravindh3@gmail.com",
            "password": "password123"
        })
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Submit job
        job_payload = {
            "queue_id": "a1c9e988-96a9-4589-a699-bc48790088ce",
            "project_id": "27f33e36-c5e1-4c2b-b9ed-4f838765ae68",
            "name": "test-job-lifecycle",
            "job_type": "immediate",
            "payload": {"task": "verify-worker-executes"},
            "priority": 5,
            "max_retries": 3
        }
        res = await client.post('http://localhost:8000/api/jobs', json=job_payload, headers=headers)
        job_data = res.json()
        job_id = job_data["id"]
        print("Submitted Job ID:", job_id)

        # Wait 4 seconds for worker to process
        await asyncio.sleep(4)

        # Check DB status
        hex_id = job_id.replace("-", "")
        conn = sqlite3.connect('job_platform.db')
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (hex_id,)).fetchone()
        if row:
            print("Job DB Status after 4s:", dict(row))
        else:
            print("Job not found in DB")
        conn.close()

asyncio.run(main())
