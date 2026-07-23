from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import require_admin
from app.modules.access.models import MODULE_UNLOCK_MARKER, ModuleAccessLog
from app.modules.admin.schemas import (
    AdminRechargeOrderOut,
    AdminSubmissionOut,
    AdminUserAccessOut,
    AdminUserOut,
    AdminUserUpdate,
    ModuleAccessItem,
    PointsConfigIn,
    PointsConfigOut,
    PointsPackage,
    ProjectAccessItem,
    RechargeQrIn,
    RechargeQrOut,
)
from app.modules.catalog import service as catalog_service
from app.modules.catalog.repository import CategoryRepository
from app.modules.catalog.schemas import (
    CategoryCreate,
    CategoryOut,
    CategoryReorderIn,
    CategoryUpdate,
    FolderTree,
)
from app.modules.payment.models import Entitlement
from app.modules.payment.recharge import (
    RECHARGE_QR_KEY,
    RechargeService,
    get_qr_url,
    list_packages,
)
from app.modules.points.models import PointLedger
from app.modules.points.service import POINTS_BY_TYPE
from app.modules.projects.models import Project
from app.modules.settings.service import (
    KEY_FREE_QUOTA,
    KEY_INTERVIEW_UNLOCK,
    KEY_RECHARGE_PACKAGES,
    KEY_REWARD_INTERVIEW,
    KEY_REWARD_KNOWLEDGE,
    KEY_REWARD_PROJECT,
    KEY_REWARD_SQL,
    KEY_SQL_UNLOCK,
    get_int_setting,
    set_setting,
)
from app.modules.submissions.repository import SubmissionRepository
from app.modules.submissions.schemas import ApproveIn, RejectIn, SubmissionOut
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
    submission_id: int,
    data: ApproveIn | None = None,
    db: AsyncSession = Depends(get_db),
) -> SubmissionOut:
    submission = await SubmissionService(db).approve(submission_id, data.content if data else None)
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


@router.get("/categories/tree", response_model=FolderTree)
async def category_folder_tree(
    section: str = Query(...), db: AsyncSession = Depends(get_db)
) -> FolderTree:
    """文件夹式管理视图：分类当文件夹，八股/SQL 当文件夹内文件。"""
    return await catalog_service.build_folder_tree(db, section)


@router.post("/categories/reorder", status_code=status.HTTP_204_NO_CONTENT)
async def reorder_categories(data: CategoryReorderIn, db: AsyncSession = Depends(get_db)) -> None:
    """拖拽后整体保存层级与顺序。"""
    await catalog_service.reorder_categories(db, data.section, data.items)


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


# ---- 用户权限范围（模块解锁 / 项目解锁）----
_MODULE_LABELS = {"sql": "SQL 题库", "interview": "面经"}


async def _load_user_access(db: AsyncSession, user: User) -> AdminUserAccessOut:
    is_admin = user.role == "admin"

    unlocked_modules = set(
        (
            await db.execute(
                select(ModuleAccessLog.module).where(
                    ModuleAccessLog.user_id == user.id,
                    ModuleAccessLog.item_id == MODULE_UNLOCK_MARKER,
                )
            )
        )
        .scalars()
        .all()
    )
    modules = [
        ModuleAccessItem(module=m, label=label, unlocked=is_admin or m in unlocked_modules)
        for m, label in _MODULE_LABELS.items()
    ]

    unlocked_projects = set(
        (
            await db.execute(
                select(Entitlement.content_id).where(
                    Entitlement.user_id == user.id,
                    Entitlement.content_type == "project",
                )
            )
        )
        .scalars()
        .all()
    )
    project_rows = (
        (
            await db.execute(
                select(Project)
                .where(Project.status == "published", Project.access_type != "free")
                .order_by(Project.id.desc())
            )
        )
        .scalars()
        .all()
    )
    projects = [
        ProjectAccessItem(
            id=p.id,
            title=p.title,
            access_type=p.access_type,
            unlocked=is_admin or p.id in unlocked_projects,
        )
        for p in project_rows
    ]
    return AdminUserAccessOut(user_id=user.id, modules=modules, projects=projects)


async def _get_user_or_404(db: AsyncSession, user_id: int) -> User:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    return user


@router.get("/users/{user_id}/access", response_model=AdminUserAccessOut)
async def get_user_access(user_id: int, db: AsyncSession = Depends(get_db)) -> AdminUserAccessOut:
    user = await _get_user_or_404(db, user_id)
    return await _load_user_access(db, user)


@router.put("/users/{user_id}/access/module/{module}", response_model=AdminUserAccessOut)
async def grant_module_access(
    user_id: int, module: str, db: AsyncSession = Depends(get_db)
) -> AdminUserAccessOut:
    if module not in _MODULE_LABELS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="模块不存在")
    user = await _get_user_or_404(db, user_id)
    exists = await db.scalar(
        select(ModuleAccessLog.id).where(
            ModuleAccessLog.user_id == user.id,
            ModuleAccessLog.module == module,
            ModuleAccessLog.item_id == MODULE_UNLOCK_MARKER,
        )
    )
    if exists is None:
        db.add(ModuleAccessLog(user_id=user.id, module=module, item_id=MODULE_UNLOCK_MARKER))
        await db.commit()
    return await _load_user_access(db, user)


@router.delete("/users/{user_id}/access/module/{module}", response_model=AdminUserAccessOut)
async def revoke_module_access(
    user_id: int, module: str, db: AsyncSession = Depends(get_db)
) -> AdminUserAccessOut:
    if module not in _MODULE_LABELS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="模块不存在")
    user = await _get_user_or_404(db, user_id)
    await db.execute(
        delete(ModuleAccessLog).where(
            ModuleAccessLog.user_id == user.id,
            ModuleAccessLog.module == module,
            ModuleAccessLog.item_id == MODULE_UNLOCK_MARKER,
        )
    )
    await db.commit()
    return await _load_user_access(db, user)


@router.put("/users/{user_id}/access/project/{project_id}", response_model=AdminUserAccessOut)
async def grant_project_access(
    user_id: int, project_id: int, db: AsyncSession = Depends(get_db)
) -> AdminUserAccessOut:
    user = await _get_user_or_404(db, user_id)
    project = await db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")
    exists = await db.scalar(
        select(Entitlement.id).where(
            Entitlement.user_id == user.id,
            Entitlement.content_type == "project",
            Entitlement.content_id == project_id,
        )
    )
    if exists is None:
        db.add(
            Entitlement(
                user_id=user.id,
                content_type="project",
                content_id=project_id,
                source="admin",
            )
        )
        await db.commit()
    return await _load_user_access(db, user)


@router.delete("/users/{user_id}/access/project/{project_id}", response_model=AdminUserAccessOut)
async def revoke_project_access(
    user_id: int, project_id: int, db: AsyncSession = Depends(get_db)
) -> AdminUserAccessOut:
    user = await _get_user_or_404(db, user_id)
    await db.execute(
        delete(Entitlement).where(
            Entitlement.user_id == user.id,
            Entitlement.content_type == "project",
            Entitlement.content_id == project_id,
        )
    )
    await db.commit()
    return await _load_user_access(db, user)


# ---- 积分充值审核（人工确认）----
async def _recharge_out(db: AsyncSession, orders: list) -> list[AdminRechargeOrderOut]:
    ids = {o.user_id for o in orders}
    users = (
        {u.id: u for u in (await db.execute(select(User).where(User.id.in_(ids)))).scalars().all()}
        if ids
        else {}
    )
    result: list[AdminRechargeOrderOut] = []
    for o in orders:
        u = users.get(o.user_id)
        result.append(
            AdminRechargeOrderOut(
                id=o.id,
                user_id=o.user_id,
                user_nickname=u.nickname if u else "未知用户",
                user_email=u.email if u else "",
                amount_cash=float(o.amount_cash),
                points_delta=o.points_delta,
                note=o.note,
                status=o.status,
                created_at=o.created_at,
            )
        )
    return result


@router.get("/recharge-orders", response_model=list[AdminRechargeOrderOut])
async def list_recharge_orders(
    status_filter: str | None = Query(default="pending", alias="status"),
    db: AsyncSession = Depends(get_db),
) -> list[AdminRechargeOrderOut]:
    orders = await RechargeService(db).list_for_admin(status_filter or None)
    return await _recharge_out(db, orders)


@router.post("/recharge-orders/{order_id}/confirm", response_model=AdminRechargeOrderOut)
async def confirm_recharge_order(
    order_id: int, db: AsyncSession = Depends(get_db)
) -> AdminRechargeOrderOut:
    order = await RechargeService(db).confirm(order_id)
    return (await _recharge_out(db, [order]))[0]


@router.post("/recharge-orders/{order_id}/reject", response_model=AdminRechargeOrderOut)
async def reject_recharge_order(
    order_id: int, db: AsyncSession = Depends(get_db)
) -> AdminRechargeOrderOut:
    order = await RechargeService(db).reject(order_id)
    return (await _recharge_out(db, [order]))[0]


# ---- 收款码设置（管理员上传后即时生效）----
@router.get("/recharge-qr", response_model=RechargeQrOut)
async def get_recharge_qr(db: AsyncSession = Depends(get_db)) -> RechargeQrOut:
    return RechargeQrOut(url=await get_qr_url(db))


@router.put("/recharge-qr", response_model=RechargeQrOut)
async def set_recharge_qr(data: RechargeQrIn, db: AsyncSession = Depends(get_db)) -> RechargeQrOut:
    await set_setting(db, RECHARGE_QR_KEY, data.url.strip())
    return RechargeQrOut(url=data.url.strip())


# ---- 积分规则（免费额度 / 模块解锁积分 / 充值套餐）后台可编辑 ----
async def _points_config(db: AsyncSession) -> PointsConfigOut:
    s = get_settings()
    return PointsConfigOut(
        free_module_quota=await get_int_setting(db, KEY_FREE_QUOTA, s.free_module_quota),
        sql_module_unlock_points=await get_int_setting(
            db, KEY_SQL_UNLOCK, s.sql_module_unlock_points
        ),
        interview_module_unlock_points=await get_int_setting(
            db, KEY_INTERVIEW_UNLOCK, s.interview_module_unlock_points
        ),
        reward_knowledge=await get_int_setting(
            db, KEY_REWARD_KNOWLEDGE, POINTS_BY_TYPE["knowledge"]
        ),
        reward_sql=await get_int_setting(db, KEY_REWARD_SQL, POINTS_BY_TYPE["sql"]),
        reward_interview=await get_int_setting(
            db, KEY_REWARD_INTERVIEW, POINTS_BY_TYPE["interview"]
        ),
        reward_project=await get_int_setting(db, KEY_REWARD_PROJECT, POINTS_BY_TYPE["project"]),
        packages=[
            PointsPackage(amount=p["amount"], points=p["points"]) for p in await list_packages(db)
        ],
    )


@router.get("/points-config", response_model=PointsConfigOut)
async def get_points_config(db: AsyncSession = Depends(get_db)) -> PointsConfigOut:
    return await _points_config(db)


@router.put("/points-config", response_model=PointsConfigOut)
async def set_points_config(
    data: PointsConfigIn, db: AsyncSession = Depends(get_db)
) -> PointsConfigOut:
    await set_setting(db, KEY_FREE_QUOTA, str(data.free_module_quota))
    await set_setting(db, KEY_SQL_UNLOCK, str(data.sql_module_unlock_points))
    await set_setting(db, KEY_INTERVIEW_UNLOCK, str(data.interview_module_unlock_points))
    await set_setting(db, KEY_REWARD_KNOWLEDGE, str(data.reward_knowledge))
    await set_setting(db, KEY_REWARD_SQL, str(data.reward_sql))
    await set_setting(db, KEY_REWARD_INTERVIEW, str(data.reward_interview))
    await set_setting(db, KEY_REWARD_PROJECT, str(data.reward_project))
    raw = ",".join(f"{p.amount}:{p.points}" for p in data.packages)
    await set_setting(db, KEY_RECHARGE_PACKAGES, raw)
    return await _points_config(db)
