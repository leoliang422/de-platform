from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user_optional
from app.modules.payment.service import user_can_access
from app.modules.projects.repository import ProjectRepository
from app.modules.projects.schemas import ProjectDetail, ProjectListItem, ProjectQAOut
from app.modules.users.models import User

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[ProjectListItem])
async def list_projects(db: AsyncSession = Depends(get_db)) -> list[ProjectListItem]:
    projects = await ProjectRepository(db).list_published()
    return [ProjectListItem.model_validate(p) for p in projects]


@router.get("/{project_id}", response_model=ProjectDetail)
async def get_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
) -> ProjectDetail:
    repo = ProjectRepository(db)
    project = await repo.get(project_id)
    if project is None or project.status != "published":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")

    # 付费项目：管理员/作者/已解锁用户可见实现与问答。
    locked = project.access_type != "free" and not await user_can_access(
        db, user, "project", project.id, project.author_id
    )
    detail = ProjectDetail(
        id=project.id,
        title=project.title,
        level=project.level,
        access_type=project.access_type,
        price_cash=project.price_cash,
        price_points=project.price_points,
        description_md=project.description_md,
        locked=locked,
    )
    if not locked:
        qa = await repo.list_qa(project.id)
        detail.implementation_md = project.implementation_md
        detail.qa = [ProjectQAOut.model_validate(q) for q in qa]
    return detail
