from __future__ import annotations

from decimal import Decimal
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
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


async def list_all(db: AsyncSession) -> list[Project]:
    result = await db.execute(select(Project).order_by(Project.id.desc()))
    return list(result.scalars().all())


async def update(db: AsyncSession, project_id: int, fields: dict[str, Any]) -> Project:
    project = await db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")
    for key, value in fields.items():
        setattr(project, key, value)
    await db.commit()
    await db.refresh(project)
    return project


async def delete(db: AsyncSession, project_id: int) -> None:
    project = await db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")
    await db.delete(project)
    await db.commit()
