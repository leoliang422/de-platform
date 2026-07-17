from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_admin
from app.modules.admin.schemas import (
    AdminSubmissionOut,
    AdminUserOut,
    AdminUserUpdate,
)
from app.modules.catalog import service as catalog_service
from app.modules.catalog.repository import CategoryRepository
from app.modules.catalog.schemas import CategoryCreate, CategoryOut, CategoryUpdate
from app.modules.points.models import PointLedger
from app.modules.submissions.repository import SubmissionRepository
from app.modules.submissions.schemas import RejectIn, SubmissionOut
from app.modules.submissions.service import SubmissionService
from app.modules.users.models import User

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


# ---- 用户管理 ----
@router.get("/users", response_model=list[AdminUserOut])
async def list_users(
    q: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> list[AdminUserOut]:
    stmt = select(User)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(User.email.ilike(like), User.nickname.ilike(like)))
    stmt = stmt.order_by(User.id.desc())
    users = (await db.execute(stmt)).scalars().all()
    return [AdminUserOut.model_validate(u) for u in users]


@router.patch("/users/{user_id}", response_model=AdminUserOut)
async def update_user(
    user_id: int, data: AdminUserUpdate, db: AsyncSession = Depends(get_db)
) -> AdminUserOut:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    if data.role is not None:
        if data.role not in ("user", "admin"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="角色不合法")
        user.role = data.role

    # 积分调整：set_points 绝对值优先，否则 delta_points 增减；写入账本便于追溯
    delta: int | None = None
    if data.set_points is not None:
        delta = data.set_points - user.points_balance
    elif data.delta_points is not None:
        delta = data.delta_points

    if delta:
        next_ref = (
            await db.execute(
                select(func.coalesce(func.max(PointLedger.ref_id), 0)).where(
                    PointLedger.ref_type == "admin_adjust"
                )
            )
        ).scalar_one() + 1
        db.add(
            PointLedger(
                user_id=user.id,
                delta=delta,
                reason=(data.reason or "管理员调整积分")[:100],
                ref_type="admin_adjust",
                ref_id=next_ref,
            )
        )
        user.points_balance += delta

    await db.commit()
    await db.refresh(user)
    return AdminUserOut.model_validate(user)
