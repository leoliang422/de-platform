from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.modules.applications.schemas import (
    CalendarEventCreate,
    CalendarEventOut,
    CalendarEventUpdate,
    ListCreate,
    ListOut,
    ListUpdate,
    RecordCreate,
    RecordOut,
    RecordUpdate,
)
from app.modules.applications.service import ApplicationService
from app.modules.users.models import User

router = APIRouter(prefix="/applications", tags=["applications"])


# ---- 投递列表 ----
@router.get("/lists", response_model=list[ListOut])
async def list_lists(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ListOut]:
    lists = await ApplicationService(db).list_lists(current_user.id)
    return [ListOut.model_validate(x) for x in lists]


@router.post("/lists", response_model=ListOut, status_code=status.HTTP_201_CREATED)
async def create_list(
    data: ListCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ListOut:
    lst = await ApplicationService(db).create_list(current_user.id, data)
    return ListOut.model_validate(lst)


@router.patch("/lists/{list_id}", response_model=ListOut)
async def rename_list(
    list_id: int,
    data: ListUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ListOut:
    lst = await ApplicationService(db).rename_list(current_user.id, list_id, data)
    return ListOut.model_validate(lst)


@router.delete("/lists/{list_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_list(
    list_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await ApplicationService(db).delete_list(current_user.id, list_id)


# ---- 投递记录 ----
@router.post(
    "/lists/{list_id}/records",
    response_model=RecordOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_record(
    list_id: int,
    data: RecordCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RecordOut:
    rec = await ApplicationService(db).add_record(current_user.id, list_id, data)
    return RecordOut.model_validate(rec)


@router.patch("/records/{record_id}", response_model=RecordOut)
async def update_record(
    record_id: int,
    data: RecordUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RecordOut:
    rec = await ApplicationService(db).update_record(current_user.id, record_id, data)
    return RecordOut.model_validate(rec)


@router.delete("/records/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_record(
    record_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await ApplicationService(db).delete_record(current_user.id, record_id)


# ---- 面试日历 ----
@router.get("/calendar", response_model=list[CalendarEventOut])
async def list_events(
    month: str | None = Query(default=None, description="按 YYYY-MM 过滤，留空返回全部"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[CalendarEventOut]:
    events = await ApplicationService(db).list_events(current_user.id, month)
    return [CalendarEventOut.model_validate(e) for e in events]


@router.post("/calendar", response_model=CalendarEventOut, status_code=status.HTTP_201_CREATED)
async def create_event(
    data: CalendarEventCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CalendarEventOut:
    ev = await ApplicationService(db).create_event(current_user.id, data)
    return CalendarEventOut.model_validate(ev)


@router.patch("/calendar/{event_id}", response_model=CalendarEventOut)
async def update_event(
    event_id: int,
    data: CalendarEventUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CalendarEventOut:
    ev = await ApplicationService(db).update_event(current_user.id, event_id, data)
    return CalendarEventOut.model_validate(ev)


@router.delete("/calendar/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await ApplicationService(db).delete_event(current_user.id, event_id)
