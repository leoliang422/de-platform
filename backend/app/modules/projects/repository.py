from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.projects.models import Project, ProjectQA


class ProjectRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_published(self) -> list[Project]:
        result = await self.db.execute(
            select(Project).where(Project.status == "published").order_by(Project.id.desc())
        )
        return list(result.scalars().all())

    async def get(self, project_id: int) -> Project | None:
        return await self.db.get(Project, project_id)

    async def list_qa(self, project_id: int) -> list[ProjectQA]:
        result = await self.db.execute(
            select(ProjectQA)
            .where(ProjectQA.project_id == project_id)
            .order_by(ProjectQA.order, ProjectQA.id)
        )
        return list(result.scalars().all())
