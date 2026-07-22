from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.modules.files.extract import DOCUMENT_TYPES, IMAGE_TYPES, TEXT_TYPES, get_extractor
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


async def _process_submission_bg(submission_id: int) -> None:
    """后台加工投稿：用独立 DB session，避免占用已返回的请求 session。"""
    # 延迟导入，便于测试用例替换 SessionLocal 指向测试库。
    from app.core.database import SessionLocal

    async with SessionLocal() as session:
        await SubmissionService(session).dispatch(submission_id)


@router.post("", response_model=SubmissionOut, status_code=status.HTTP_201_CREATED)
async def create_submission(
    data: SubmissionCreate,
    background: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SubmissionOut:
    # 先落库并立即返回（状态 processing），大模型加工放到响应之后的后台任务，
    # 避免同步等待导致的请求超时（免费实例上表现为“上传失败”）。
    submission = await SubmissionService(db).create(current_user.id, data, dispatch=False)
    background.add_task(_process_submission_bg, submission.id)
    return SubmissionOut.model_validate(submission)


@router.post("/parse", response_model=ParseResult)
async def parse_submission(
    target_type: TargetType = Form(...),
    text: str | None = Form(default=None),
    file: UploadFile | None = File(default=None),
    current_user: User = Depends(get_current_user),
) -> ParseResult:
    """上传文件/粘贴文本 → 大模型结构化拆分为多条投稿草稿（支持 图片/Word/PDF/文本）。"""
    raw = (text or "").strip()
    if file is not None:
        data = await file.read()
        ct = file.content_type or ""
        if ct in TEXT_TYPES:
            raw = data.decode("utf-8", errors="replace")
        elif ct in IMAGE_TYPES:
            # 图片走多模态大模型 OCR 抽字，再交给结构化拆分。
            try:
                ocr_text = (await get_llm_client().ocr_image(data, ct)).strip()
            except Exception as exc:  # noqa: BLE001 - OCR 失败给出可读提示
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"图片文字识别失败：{exc}。请确认已配置多模态模型，或改用文本/Word/PDF。",
                ) from exc
            if not ocr_text:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="未能从图片识别出文字，请换更清晰的图片或直接粘贴文本。",
                )
            raw = ocr_text
        elif ct in DOCUMENT_TYPES:
            out = await get_extractor().extract(
                data=data, filename=file.filename or "", content_type=ct, url=None
            )
            if out.placeholder:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="未能从文件解析出文字（可能是扫描件/旧版 .doc），"
                    "请换 .docx/.pdf、上传图片，或直接粘贴文本。",
                )
            raw = out.text
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="仅支持 图片/Word/PDF/文本文件。",
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


@router.delete("/{submission_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_submission(
    submission_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """删除自己的投稿记录（清理「我的投稿」列表）。"""
    await SubmissionService(db).delete(submission_id, current_user)
