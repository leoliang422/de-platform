from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.modules.submissions.repository import SubmissionRepository
from app.modules.submissions.schemas import SubmissionCreate, SubmissionOut
from app.modules.submissions.service import SubmissionService
from app.modules.users.models import User

router = APIRouter(prefix="/submissions", tags=["submissions"])


@router.post("", response_model=SubmissionOut, status_code=status.HTTP_201_CREATED)
async def create_submission(
    data: SubmissionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SubmissionOut:
    submission = await SubmissionService(db).create(current_user.id, data)
    return SubmissionOut.model_validate(submission)


@router.get("/me", response_model=list[SubmissionOut])
async def my_submissions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[SubmissionOut]:
    items = await SubmissionRepository(db).list_by_user(current_user.id)
    return [SubmissionOut.model_validate(s) for s in items]
