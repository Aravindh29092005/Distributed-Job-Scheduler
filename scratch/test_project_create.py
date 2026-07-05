import asyncio
from backend.db.session import AsyncSessionLocal
from backend.services.org_project import ProjectService
import uuid

async def test():
    async with AsyncSessionLocal() as db:
        service = ProjectService(db)
        try:
            # Let's try to create a project for org '6d1e3e8a-a504-4fc7-bb2b-bb7fc771150e' and user '722aaa5c-3a3d-407a-ba53-577402cca355'
            org_id = '6d1e3e8a-a504-4fc7-bb2b-bb7fc771150e'
            user_id = '722aaa5c-3a3d-407a-ba53-577402cca355'
            project = await service.create(
                org_id=org_id,
                name="project one manual test",
                description="a project created from test script",
                user_id=user_id
            )
            print("Successfully created project:", project.id, project.name)
        except Exception as e:
            print("Error creating project:", type(e), e)

asyncio.run(test())
