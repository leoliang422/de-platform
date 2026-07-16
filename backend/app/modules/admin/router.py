from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_admin
from app.modules.admin.schemas import AdminSubmissionOut
from app.modules.catalog import service as catalog_service
from app.modules.catalog.repository import CategoryRepository
from app.modules.catalog.schemas import CategoryCreate, CategoryOut, CategoryUpdate
from app.modules.submissions.repository import SubmissionRepository
from app.modules.submissions.schemas import RejectIn, SubmissionOut
from app.modules.submissions.service import SubmissionService

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


# ---- 审核队列 ----
@router.get("/submissions", response_model=list[AdminSubmissionOut])
async def list_submissions(
    status_filter: str | None = Query(default="pending_review", alias="status"),
    db: AsyncSession = Depends(get_db),
) -> list[AdminSubmissionOut]:
    items = await SubmissionRepository(db).list_by_status(status_filter or None)
    return [AdminSubmissionOut.model_validate(s) for s in items]


@router.post("/submissions/{submission_id}/approve", response_model=SubmissionOut)
async def approve_submission(
    submission_id: int, db: AsyncSession = Depends(get_db)
) -> SubmissionOut:
    submission = await SubmissionService(db).approve(submission_id)
    return SubmissionOut.model_validate(submission)


@router.post("/submissions/{submission_id}/reject", response_model=SubmissionOut)
async def reject_submission(
    submission_id: int, data: RejectIn, db: AsyncSession = Depends(get_db)
) -> SubmissionOut:
    submission = await SubmissionService(db).reject(submission_id, data.reason)
    return SubmissionOut.model_validate(submission)


# ---- 分类维护 ----
@router.get("/categories", response_model=list[CategoryOut])
async def list_categories(
    section: str = Query(...), db: AsyncSession = Depends(get_db)
) -> list[CategoryOut]:
    items = await CategoryRepository(db).list_by_section(section)
    return [CategoryOut.model_validate(c) for c in items]


@router.post("/categories", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
async def create_category(data: CategoryCreate, db: AsyncSession = Depends(get_db)) -> CategoryOut:
    category = await catalog_service.create_category(db, data)
    return CategoryOut.model_validate(category)


@router.patch("/categories/{category_id}", response_model=CategoryOut)
async def update_category(
    category_id: int, data: CategoryUpdate, db: AsyncSession = Depends(get_db)
) -> CategoryOut:
    category = await catalog_service.update_category(db, category_id, data)
    return CategoryOut.model_validate(category)


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(category_id: int, db: AsyncSession = Depends(get_db)) -> None:
    await catalog_service.delete_category(db, category_id)
