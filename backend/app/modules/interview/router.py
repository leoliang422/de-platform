from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.interview import service as interview_service
from app.modules.interview.repository import InterviewRepository
from app.modules.interview.schemas import (
    CompanyOut,
    InterviewCardOut,
    InterviewTypeGroup,
)

router = APIRouter(tags=["interview"])


@router.get("/companies", response_model=list[CompanyOut])
async def list_companies(db: AsyncSession = Depends(get_db)) -> list[CompanyOut]:
    companies = await InterviewRepository(db).list_companies()
    return [CompanyOut.model_validate(c) for c in companies]


@router.get(
    "/companies/{company_id}/interviews-by-type",
    response_model=list[InterviewTypeGroup],
)
async def list_company_interviews_by_type(
    company_id: int, db: AsyncSession = Depends(get_db)
) -> list[InterviewTypeGroup]:
    """企业下的面经按类型（社招/校招/日常实习/暑期实习）聚合，每篇为一次完整面试。"""
    repo = InterviewRepository(db)
    if await repo.get_company(company_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="企业不存在")
    posts = await repo.list_posts_by_company(company_id)
    return await interview_service.list_cards_by_type(db, posts)


@router.get("/interviews/{post_id}", response_model=InterviewCardOut)
async def get_interview(post_id: int, db: AsyncSession = Depends(get_db)) -> InterviewCardOut:
    post = await InterviewRepository(db).get_post(post_id)
    if post is None or post.status != "published":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="面经不存在")
    return await interview_service.to_card_detail(db, post)
