import datetime as dt
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

# 可付费解锁的内容类型：仅项目（八股已全部免费；SQL/面经改用模块级积分门控）。
PAYABLE_TYPES = ("project",)
ORDER_STATUSES = ("pending", "paid", "failed")
ENTITLEMENT_SOURCES = ("purchase", "points")


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    item_type: Mapped[str] = mapped_column(String(20), nullable=False)
    item_id: Mapped[int] = mapped_column(Integer, nullable=False)
    amount_cash: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    # 充值订单（item_type="recharge"）确认到账后应发放的积分数；内容解锁订单为空。
    points_delta: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    provider: Mapped[str] = mapped_column(String(20), default="mock", nullable=False)
    provider_ref: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Entitlement(Base):
    """用户对某付费内容的解锁凭证。"""

    __tablename__ = "entitlements"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "content_type", "content_id", name="uq_entitlement_user_content"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    content_type: Mapped[str] = mapped_column(String(20), nullable=False)
    content_id: Mapped[int] = mapped_column(Integer, nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
