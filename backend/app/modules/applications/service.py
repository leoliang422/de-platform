from __future__ import annotations

import datetime as dt

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.applications.models import (
    ApplicationList,
    ApplicationRecord,
    CalendarEvent,
)
from app.modules.applications.schemas import (
    CalendarEventCreate,
    CalendarEventUpdate,
    InterviewCompanyOut,
    ListCreate,
    ListUpdate,
    RecordCreate,
    RecordUpdate,
)
from app.modules.interview.models import Company, InterviewPost


def _month_range(month: str | None) -> tuple[dt.date, dt.date] | None:
    """把 "YYYY-MM" 解析为 [当月1日, 次月1日) 的日期区间；非法/空则返回 None。"""
    if not month:
        return None
    try:
        year, mon = (int(x) for x in month.split("-", 1))
        start = dt.date(year, mon, 1)
    except (ValueError, TypeError):
        return None
    end = dt.date(year + 1, 1, 1) if mon == 12 else dt.date(year, mon + 1, 1)
    return start, end


class ApplicationService:
    """投递列表 / 记录 / 面试日历的业务逻辑（全部按 user 隔离）。"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ---- 列表 ----
    async def list_lists(self, user_id: int) -> list[ApplicationList]:
        result = await self.db.execute(
            select(ApplicationList)
            .where(ApplicationList.user_id == user_id)
            .order_by(ApplicationList.order_index, ApplicationList.id)
        )
        return list(result.scalars().all())

    async def interview_companies(self) -> list[InterviewCompanyOut]:
        """列出有已发布面经的公司，供投递记录「选择关联」下拉使用。"""
        rows = await self.db.execute(
            select(Company.id, Company.name, func.count(InterviewPost.id))
            .join(InterviewPost, InterviewPost.company_id == Company.id)
            .where(InterviewPost.status == "published")
            .group_by(Company.id, Company.name)
            .order_by(Company.name)
        )
        return [
            InterviewCompanyOut(id=cid, name=name, post_count=int(cnt))
            for cid, name, cnt in rows.all()
        ]

    async def _validate_company(self, company_id: int | None) -> None:
        if company_id is None:
            return
        if await self.db.get(Company, company_id) is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="关联的面经公司不存在"
            )

    async def _get_list(self, user_id: int, list_id: int) -> ApplicationList:
        lst = await self.db.get(ApplicationList, list_id)
        if lst is None or lst.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="投递列表不存在")
        return lst

    async def create_list(self, user_id: int, data: ListCreate) -> ApplicationList:
        max_order = await self.db.scalar(
            select(func.coalesce(func.max(ApplicationList.order_index), -1)).where(
                ApplicationList.user_id == user_id
            )
        )
        lst = ApplicationList(
            user_id=user_id, name=data.name.strip(), order_index=(max_order or 0) + 1
        )
        self.db.add(lst)
        await self.db.commit()
        await self.db.refresh(lst)
        return lst

    async def rename_list(self, user_id: int, list_id: int, data: ListUpdate) -> ApplicationList:
        lst = await self._get_list(user_id, list_id)
        lst.name = data.name.strip()
        await self.db.commit()
        await self.db.refresh(lst)
        return lst

    async def delete_list(self, user_id: int, list_id: int) -> None:
        lst = await self._get_list(user_id, list_id)
        await self.db.delete(lst)
        await self.db.commit()

    # ---- 记录 ----
    async def _get_record(self, user_id: int, record_id: int) -> ApplicationRecord:
        rec = await self.db.get(ApplicationRecord, record_id)
        if rec is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="投递记录不存在")
        # 校验归属：记录 → 列表 → 用户。
        await self._get_list(user_id, rec.list_id)
        return rec

    async def add_record(self, user_id: int, list_id: int, data: RecordCreate) -> ApplicationRecord:
        await self._get_list(user_id, list_id)
        await self._validate_company(data.interview_company_id)
        max_order = await self.db.scalar(
            select(func.coalesce(func.max(ApplicationRecord.order_index), -1)).where(
                ApplicationRecord.list_id == list_id
            )
        )
        rec = ApplicationRecord(
            list_id=list_id,
            company_name=data.company_name.strip(),
            nature=data.nature,
            position=data.position.strip(),
            applied_date=data.applied_date,
            status=data.status,
            interview_company_id=data.interview_company_id,
            order_index=(max_order or 0) + 1,
        )
        self.db.add(rec)
        await self.db.commit()
        await self.db.refresh(rec)
        return rec

    async def update_record(
        self, user_id: int, record_id: int, data: RecordUpdate
    ) -> ApplicationRecord:
        rec = await self._get_record(user_id, record_id)
        fields = data.model_dump(exclude_unset=True)
        if "interview_company_id" in fields:
            await self._validate_company(fields["interview_company_id"])
        for key, value in fields.items():
            if key in ("company_name", "position") and isinstance(value, str):
                value = value.strip()
            setattr(rec, key, value)
        await self.db.commit()
        await self.db.refresh(rec)
        return rec

    async def delete_record(self, user_id: int, record_id: int) -> None:
        rec = await self._get_record(user_id, record_id)
        await self.db.delete(rec)
        await self.db.commit()

    # ---- 日历 ----
    async def list_events(self, user_id: int, month: str | None = None) -> list[CalendarEvent]:
        stmt = select(CalendarEvent).where(CalendarEvent.user_id == user_id)
        rng = _month_range(month)
        if rng is not None:
            start, end = rng
            stmt = stmt.where(CalendarEvent.event_date >= start, CalendarEvent.event_date < end)
        stmt = stmt.order_by(CalendarEvent.event_date, CalendarEvent.start_time)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def _get_event(self, user_id: int, event_id: int) -> CalendarEvent:
        ev = await self.db.get(CalendarEvent, event_id)
        if ev is None or ev.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="日历事件不存在")
        return ev

    async def create_event(self, user_id: int, data: CalendarEventCreate) -> CalendarEvent:
        ev = CalendarEvent(
            user_id=user_id,
            title=data.title.strip(),
            event_date=data.event_date,
            start_time=data.start_time,
            end_time=data.end_time,
            note=data.note,
            color=data.color,
        )
        self.db.add(ev)
        await self.db.commit()
        await self.db.refresh(ev)
        return ev

    async def update_event(
        self, user_id: int, event_id: int, data: CalendarEventUpdate
    ) -> CalendarEvent:
        ev = await self._get_event(user_id, event_id)
        fields = data.model_dump(exclude_unset=True)
        for key, value in fields.items():
            if key == "title" and isinstance(value, str):
                value = value.strip()
            setattr(ev, key, value)
        await self.db.commit()
        await self.db.refresh(ev)
        return ev

    async def delete_event(self, user_id: int, event_id: int) -> None:
        ev = await self._get_event(user_id, event_id)
        await self.db.delete(ev)
        await self.db.commit()
