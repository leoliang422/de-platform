from __future__ import annotations

from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.projects.models import Project
from app.modules.projects.repository import ProjectRepository


async def get_published(db: AsyncSession, project_id: int) -> Project | None:
    project = await ProjectRepository(db).get(project_id)
    if project is None or project.status != "published":
        return None
    return project


async def create_published(
    db: AsyncSession,
    *,
    title: str,
    description_md: str,
    implementation_md: str,
    level: str,
    access_type: str,
    price_cash: Decimal | None,
    price_points: int | None,
    author_id: int | None,
) -> Project:
    project = Project(
        title=title,
        description_md=description_md,
        implementation_md=implementation_md,
        level=level,
        access_type=access_type,
        price_cash=price_cash,
        price_points=price_points,
        status="published",
        author_id=author_id,
    )
    db.add(project)
    await db.flush()
    return project
