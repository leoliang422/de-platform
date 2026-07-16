from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.interview.repository import InterviewRepository
from app.modules.interview.schemas import (
    CompanyOut,
    InterviewPostDetail,
    InterviewPostListItem,
)

router = APIRouter(tags=["interview"])


@router.get("/companies", response_model=list[CompanyOut])
async def list_companies(db: AsyncSession = Depends(get_db)) -> list[CompanyOut]:
    companies = await InterviewRepository(db).list_companies()
    return [CompanyOut.model_validate(c) for c in companies]


@router.get("/companies/{company_id}/interviews", response_model=list[InterviewPostListItem])
async def list_company_interviews(
    company_id: int, db: AsyncSession = Depends(get_db)
) -> list[InterviewPostListItem]:
    repo = InterviewRepository(db)
    if await repo.get_company(company_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="企业不存在")
    posts = await repo.list_posts_by_company(company_id)
    return [InterviewPostListItem.model_validate(p) for p in posts]


@router.get("/interviews/{post_id}", response_model=InterviewPostDetail)
async def get_interview(post_id: int, db: AsyncSession = Depends(get_db)) -> InterviewPostDetail:
    post = await InterviewRepository(db).get_post(post_id)
    if post is None or post.status != "published":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="面经不存在")
    return InterviewPostDetail.model_validate(post)
