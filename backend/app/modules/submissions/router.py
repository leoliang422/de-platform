from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.modules.files.extract import DOCUMENT_TYPES, TEXT_TYPES, get_extractor
from app.modules.llm.factory import get_llm_client
from app.modules.submissions.repository import SubmissionRepository
from app.modules.submissions.schemas import (
    CompleteAnswerIn,
    CompleteAnswerOut,
    ParseResult,
    SubmissionCreate,
    SubmissionOut,
    TargetType,
)
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


@router.post("/parse", response_model=ParseResult)
async def parse_submission(
    target_type: TargetType = Form(...),
    text: str | None = Form(default=None),
    file: UploadFile | None = File(default=None),
    current_user: User = Depends(get_current_user),
) -> ParseResult:
    """上传文件/粘贴文本 → 大模型结构化拆分为多条投稿草稿（本批支持 Word/PDF/文本）。"""
    raw = (text or "").strip()
    if file is not None:
        data = await file.read()
        ct = file.content_type or ""
        if ct in TEXT_TYPES:
            raw = data.decode("utf-8", errors="replace")
        elif ct in DOCUMENT_TYPES:
            out = await get_extractor().extract(
                data=data, filename=file.filename or "", content_type=ct, url=None
            )
            if out.placeholder:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="未能从文件解析出文字（可能是扫描件/旧版 .doc/图片），"
                    "请换 .docx/.pdf 或直接粘贴文本；图片解析将在后续批次支持。",
                )
            raw = out.text
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="本批次仅支持 Word/PDF/文本文件；图片解析将在后续批次支持。",
            )
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="请上传文件或粘贴文本"
        )
    items = await get_llm_client().extract_items(raw, target_type)
    return ParseResult(target_type=target_type, items=items)


@router.post("/complete-answer", response_model=CompleteAnswerOut)
async def complete_answer(
    data: CompleteAnswerIn,
    current_user: User = Depends(get_current_user),
) -> CompleteAnswerOut:
    """针对单个问题用大模型生成参考答案（标注 AI 生成，供人工 review）。"""
    answer = await get_llm_client().complete_answer(data.question, data.target_type, data.context)
    return CompleteAnswerOut(answer=answer)


@router.get("/me", response_model=list[SubmissionOut])
async def my_submissions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[SubmissionOut]:
    items = await SubmissionRepository(db).list_by_user(current_user.id)
    return [SubmissionOut.model_validate(s) for s in items]


@router.post("/{submission_id}/retry", response_model=SubmissionOut)
async def retry_submission(
    submission_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SubmissionOut:
    submission = await SubmissionService(db).retry(submission_id, current_user)
    return SubmissionOut.model_validate(submission)
