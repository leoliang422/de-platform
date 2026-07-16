from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_admin
from app.modules.admin.content_schemas import (
    ContentSummary,
    InterviewCreate,
    InterviewUpdate,
    KnowledgeCreate,
    KnowledgeUpdate,
    ProjectCreate,
    ProjectUpdate,
    SqlCreate,
    SqlUpdate,
)
from app.modules.interview import service as interview_service
from app.modules.interview.models import Company, InterviewPost
from app.modules.interview.repository import InterviewRepository
from app.modules.knowledge import service as knowledge_service
from app.modules.knowledge.models import KnowledgeItem
from app.modules.projects import service as project_service
from app.modules.projects.models import Project
from app.modules.sql_bank import service as sql_service
from app.modules.sql_bank.models import SqlQuestion


async def _get_or_404(db: AsyncSession, model: type, obj_id: int) -> Any:
    obj = await db.get(model, obj_id)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="内容不存在")
    return obj

router = APIRouter(
    prefix="/admin/content", tags=["admin-content"], dependencies=[Depends(require_admin)]
)


# ---- knowledge ----
@router.get("/knowledge", response_model=list[ContentSummary])
async def list_knowledge(db: AsyncSession = Depends(get_db)) -> list[ContentSummary]:
    items = await knowledge_service.list_all(db)
    return [
        ContentSummary(
            id=i.id, title=i.title, subtitle="付费" if i.is_paid else None, status=i.status
        )
        for i in items
    ]


@router.get("/knowledge/{item_id}/detail")
async def get_knowledge_detail(
    item_id: int, db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    item: KnowledgeItem = await _get_or_404(db, KnowledgeItem, item_id)
    return {
        "id": item.id,
        "title": item.title,
        "content_md": item.content_md,
        "category_id": item.category_id,
        "is_paid": item.is_paid,
        "price_cash": str(item.price_cash) if item.price_cash is not None else None,
        "price_points": item.price_points,
        "status": item.status,
    }


@router.post("/knowledge", response_model=ContentSummary, status_code=status.HTTP_201_CREATED)
async def create_knowledge(
    data: KnowledgeCreate, db: AsyncSession = Depends(get_db)
) -> ContentSummary:
    item = await knowledge_service.create_published(
        db,
        title=data.title,
        content_md=data.content_md,
        category_id=data.category_id,
        is_paid=data.is_paid,
        price_cash=data.price_cash,
        price_points=data.price_points,
        author_id=None,
    )
    item.status = data.status
    await db.commit()
    await db.refresh(item)
    return ContentSummary(
        id=item.id, title=item.title, subtitle="付费" if item.is_paid else None, status=item.status
    )


@router.patch("/knowledge/{item_id}", response_model=ContentSummary)
async def update_knowledge(
    item_id: int, data: KnowledgeUpdate, db: AsyncSession = Depends(get_db)
) -> ContentSummary:
    item = await knowledge_service.update(db, item_id, data.model_dump(exclude_unset=True))
    return ContentSummary(
        id=item.id, title=item.title, subtitle="付费" if item.is_paid else None, status=item.status
    )


@router.delete("/knowledge/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_knowledge(item_id: int, db: AsyncSession = Depends(get_db)) -> None:
    await knowledge_service.delete(db, item_id)


# ---- sql ----
@router.get("/sql", response_model=list[ContentSummary])
async def list_sql(db: AsyncSession = Depends(get_db)) -> list[ContentSummary]:
    items = await sql_service.list_all(db)
    return [
        ContentSummary(id=i.id, title=i.title, subtitle=i.difficulty, status=i.status)
        for i in items
    ]


@router.get("/sql/{question_id}/detail")
async def get_sql_detail(
    question_id: int, db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    q: SqlQuestion = await _get_or_404(db, SqlQuestion, question_id)
    return {
        "id": q.id,
        "title": q.title,
        "prompt_md": q.prompt_md,
        "answer_md": q.answer_md,
        "difficulty": q.difficulty,
        "tags": q.tags,
        "category_id": q.category_id,
        "status": q.status,
    }


@router.post("/sql", response_model=ContentSummary, status_code=status.HTTP_201_CREATED)
async def create_sql(data: SqlCreate, db: AsyncSession = Depends(get_db)) -> ContentSummary:
    q = await sql_service.create_published(
        db,
        title=data.title,
        prompt_md=data.prompt_md,
        answer_md=data.answer_md,
        difficulty=data.difficulty,
        tags=data.tags,
        category_id=data.category_id,
        author_id=None,
    )
    q.status = data.status
    await db.commit()
    await db.refresh(q)
    return ContentSummary(id=q.id, title=q.title, subtitle=q.difficulty, status=q.status)


@router.patch("/sql/{question_id}", response_model=ContentSummary)
async def update_sql(
    question_id: int, data: SqlUpdate, db: AsyncSession = Depends(get_db)
) -> ContentSummary:
    q = await sql_service.update(db, question_id, data.model_dump(exclude_unset=True))
    return ContentSummary(id=q.id, title=q.title, subtitle=q.difficulty, status=q.status)


@router.delete("/sql/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sql(question_id: int, db: AsyncSession = Depends(get_db)) -> None:
    await sql_service.delete(db, question_id)


# ---- interview ----
@router.get("/interview", response_model=list[ContentSummary])
async def list_interview(db: AsyncSession = Depends(get_db)) -> list[ContentSummary]:
    posts = await interview_service.list_all(db)
    companies = {c.id: c.name for c in await InterviewRepository(db).list_companies()}
    return [
        ContentSummary(
            id=p.id, title=p.position, subtitle=companies.get(p.company_id), status=p.status
        )
        for p in posts
    ]


@router.get("/interview/{post_id}/detail")
async def get_interview_detail(
    post_id: int, db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    post: InterviewPost = await _get_or_404(db, InterviewPost, post_id)
    company = await db.get(Company, post.company_id)
    return {
        "id": post.id,
        "company_name": company.name if company else "",
        "position": post.position,
        "content_md": post.content_md,
        "status": post.status,
    }


@router.post("/interview", response_model=ContentSummary, status_code=status.HTTP_201_CREATED)
async def create_interview(
    data: InterviewCreate, db: AsyncSession = Depends(get_db)
) -> ContentSummary:
    post = await interview_service.create_published(
        db,
        company_name=data.company_name,
        position=data.position,
        content_md=data.content_md,
        author_id=None,
    )
    post.status = data.status
    await db.commit()
    await db.refresh(post)
    return ContentSummary(
        id=post.id, title=post.position, subtitle=data.company_name, status=post.status
    )


@router.patch("/interview/{post_id}", response_model=ContentSummary)
async def update_interview(
    post_id: int, data: InterviewUpdate, db: AsyncSession = Depends(get_db)
) -> ContentSummary:
    post = await interview_service.update(db, post_id, data.model_dump(exclude_unset=True))
    companies = {c.id: c.name for c in await InterviewRepository(db).list_companies()}
    return ContentSummary(
        id=post.id, title=post.position, subtitle=companies.get(post.company_id), status=post.status
    )


@router.delete("/interview/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_interview(post_id: int, db: AsyncSession = Depends(get_db)) -> None:
    await interview_service.delete(db, post_id)


# ---- project ----
@router.get("/project", response_model=list[ContentSummary])
async def list_project(db: AsyncSession = Depends(get_db)) -> list[ContentSummary]:
    items = await project_service.list_all(db)
    return [
        ContentSummary(id=i.id, title=i.title, subtitle=i.access_type, status=i.status)
        for i in items
    ]


@router.get("/project/{project_id}/detail")
async def get_project_detail(
    project_id: int, db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    p: Project = await _get_or_404(db, Project, project_id)
    return {
        "id": p.id,
        "title": p.title,
        "description_md": p.description_md,
        "implementation_md": p.implementation_md,
        "level": p.level,
        "access_type": p.access_type,
        "price_cash": str(p.price_cash) if p.price_cash is not None else None,
        "price_points": p.price_points,
        "status": p.status,
    }


@router.post("/project", response_model=ContentSummary, status_code=status.HTTP_201_CREATED)
async def create_project(
    data: ProjectCreate, db: AsyncSession = Depends(get_db)
) -> ContentSummary:
    project = await project_service.create_published(
        db,
        title=data.title,
        description_md=data.description_md,
        implementation_md=data.implementation_md,
        level=data.level,
        access_type=data.access_type,
        price_cash=data.price_cash,
        price_points=data.price_points,
        author_id=None,
    )
    project.status = data.status
    await db.commit()
    await db.refresh(project)
    return ContentSummary(
        id=project.id, title=project.title, subtitle=project.access_type, status=project.status
    )


@router.patch("/project/{project_id}", response_model=ContentSummary)
async def update_project(
    project_id: int, data: ProjectUpdate, db: AsyncSession = Depends(get_db)
) -> ContentSummary:
    project = await project_service.update(db, project_id, data.model_dump(exclude_unset=True))
    return ContentSummary(
        id=project.id, title=project.title, subtitle=project.access_type, status=project.status
    )


@router.delete("/project/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(project_id: int, db: AsyncSession = Depends(get_db)) -> None:
    await project_service.delete(db, project_id)
