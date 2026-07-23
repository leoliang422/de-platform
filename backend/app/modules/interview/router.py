from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, get_current_user_optional
from app.modules.access.service import AccessService
from app.modules.interview import service as interview_service
from app.modules.interview.repository import InterviewRepository
from app.modules.interview.schemas import (
    CompanyOut,
    InterviewByTypeResponse,
    InterviewCardOut,
    ModuleAccessInfo,
)
from app.modules.users.models import User

router = APIRouter(tags=["interview"])


@router.get("/companies", response_model=list[CompanyOut])
async def list_companies(db: AsyncSession = Depends(get_db)) -> list[CompanyOut]:
    companies = await InterviewRepository(db).list_companies()
    return [CompanyOut.model_validate(c) for c in companies]


@router.get(
    "/companies/{company_id}/interviews-by-type",
    response_model=InterviewByTypeResponse,
)
async def list_company_interviews_by_type(
    company_id: int,
    user: User | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
) -> InterviewByTypeResponse:
    """企业下的面经按类型聚合，每篇为一次完整面试；受模块级积分门控。"""
    repo = InterviewRepository(db)
    if await repo.get_company(company_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="企业不存在")
    posts = await repo.list_posts_by_company(company_id)
    groups = await interview_service.list_cards_by_type(db, posts, user)
    summary = await AccessService(db).summary(user, "interview")
    return InterviewByTypeResponse(
        groups=groups,
        access=ModuleAccessInfo(
            unlocked=summary.unlocked,
            free_used=summary.free_used,
            free_limit=summary.free_limit,
            unlock_points=summary.unlock_points,
        ),
    )


@router.get("/interviews/mine", response_model=list[InterviewCardOut])
async def list_my_interviews(
    company: str | None = Query(default=None, description="按公司名过滤，留空返回全部"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[InterviewCardOut]:
    """当前用户自己上传的面经卡片（供投递记录「查看面经」弹窗展示）。"""
    return await interview_service.list_mine(db, current_user.id, company)


@router.get("/interviews/{post_id}", response_model=InterviewCardOut)
async def get_interview(
    post_id: int,
    user: User | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
) -> InterviewCardOut:
    post = await InterviewRepository(db).get_post(post_id)
    if post is None or post.status != "published":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="面经不存在")
    visible = await AccessService(db).can_view(user, "interview", post.id, post.author_id)
    return await interview_service.to_card_detail(db, post, locked=not visible)


@router.post("/interviews/{post_id}/reveal", response_model=InterviewCardOut)
async def reveal_interview(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InterviewCardOut:
    """查看一篇面经：命中免费名额则消耗一次；超额且未解锁模块时返回锁定态。"""
    post = await InterviewRepository(db).get_post(post_id)
    if post is None or post.status != "published":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="面经不存在")
    state = await AccessService(db).reveal(current_user, "interview", post.id, post.author_id)
    return await interview_service.to_card_detail(db, post, locked=not state.granted)
