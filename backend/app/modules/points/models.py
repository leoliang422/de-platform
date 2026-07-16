import datetime as dt

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PointLedger(Base):
    """积分账本。发放/消耗均在此记录，(ref_type, ref_id) 保证发放幂等。"""

    __tablename__ = "point_ledger"
    __table_args__ = (UniqueConstraint("ref_type", "ref_id", name="uq_point_ledger_ref"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    delta: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(100), nullable=False)
    ref_type: Mapped[str] = mapped_column(String(30), nullable=False)
    ref_id: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
