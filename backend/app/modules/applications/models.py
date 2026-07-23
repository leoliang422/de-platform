"""投递记录管理：投递列表 / 投递记录 / 面试日历。

个人主页的求职进度追踪工具，全部按用户隔离：
- ``ApplicationList``：用户自命名的投递列表（如「秋招」「暑期实习」）。
- ``ApplicationRecord``：列表内的一条投递（公司 / 性质 / 岗位 / 投递时间 / 状态）。
- ``CalendarEvent``：面试安排日历事件（哪天哪个时间段有什么事）。
"""

import datetime as dt

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

# 公司性质。
COMPANY_NATURES = ("state", "private", "foreign", "other")

# 投递状态（含简历/笔试/各面试轮次的「进行中」与「挂」）。
APPLICATION_STATUSES = (
    "applied",  # 已投递
    "resume_fail",  # 简历挂
    "written",  # 笔试中
    "written_fail",  # 笔试挂
    "round1",  # 一面中
    "round1_fail",  # 一面挂
    "round2",  # 二面中
    "round2_fail",  # 二面挂
    "round3",  # 三面中
    "round3_fail",  # 三面挂
    "hr",  # HR面中
    "hr_fail",  # HR面挂
    "rejected",  # 已拒
    "offer",  # Offer
)


class ApplicationList(Base):
    __tablename__ = "application_lists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    records: Mapped[list["ApplicationRecord"]] = relationship(
        "ApplicationRecord",
        cascade="all, delete-orphan",
        order_by="ApplicationRecord.order_index, ApplicationRecord.id",
        lazy="selectin",
    )


class ApplicationRecord(Base):
    __tablename__ = "application_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    list_id: Mapped[int] = mapped_column(
        ForeignKey("application_lists.id", ondelete="CASCADE"), nullable=False, index=True
    )
    company_name: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    # 性质：state / private / foreign / other
    nature: Mapped[str | None] = mapped_column(String(20), nullable=True)
    position: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    applied_date: Mapped[dt.date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="applied")
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # 手动关联的面经公司（用户显式选择）。为空时前端回退到按公司名自动匹配。
    interview_company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class CalendarEvent(Base):
    __tablename__ = "calendar_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    event_date: Mapped[dt.date] = mapped_column(Date, nullable=False, index=True)
    # 时间段用 "HH:MM" 文本存储（可空 → 全天事项）。
    start_time: Mapped[str | None] = mapped_column(String(5), nullable=True)
    end_time: Mapped[str | None] = mapped_column(String(5), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 前端展示用的颜色标记（可选）。
    color: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
