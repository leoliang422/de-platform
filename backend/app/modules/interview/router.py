from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.interview import service as interview_service
from app.modules.interview.models import InterviewPost
from app.modules.interview.repository import InterviewRepository
from app.modules.interview.schemas import (
    CompanyOut,
    InterviewPostDetail,
    InterviewPostListItem,
    InterviewQAOut,
    PositionGroup,
)

router = APIRouter(tags=["interview"])


def _to_detail(post: InterviewPost) -> InterviewPostDetail:
    technical = [q for q in post.qa if q.section == "technical"]
    hr = [q for q in post.qa if q.section == "hr"]
    return InterviewPostDetail(
        id=post.id,
        company_id=post.company_id,
        position=post.position,
        position_level=post.position_level,
        interview_date=post.interview_date,
        rounds=post.rounds,
        result=post.result,
        city=post.city,
        channel=post.channel,
        content_md=post.content_md,
        technical_qa=[InterviewQAOut.model_validate(q) for q in technical],
        hr_qa=[InterviewQAOut.model_validate(q) for q in hr],
    )


@router.get("/companies", response_model=list[CompanyOut])
async def list_companies(db: AsyncSession = Depends(get_db)) -> list[CompanyOut]:
    companies = await InterviewRepository(db).list_companies()
    return [CompanyOut.model_validate(c) for c in companies]


@router.get("/companies/{company_id}/positions", response_model=list[PositionGroup])
async def list_company_positions(
    company_id: int, db: AsyncSession = Depends(get_db)
) -> list[PositionGroup]:
    """企业下的面经按岗位聚合（相同岗位合并）。"""
    repo = InterviewRepository(db)
    if await repo.get_company(company_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="企业不存在")
    posts = await repo.list_posts_by_company(company_id)
    groups = interview_service.group_by_position(posts)
    return [
        PositionGroup(
            position=g["position"],
            count=g["count"],
            posts=[InterviewPostListItem.model_validate(p) for p in g["posts"]],
        )
        for g in groups
    ]


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
    return _to_detail(post)
