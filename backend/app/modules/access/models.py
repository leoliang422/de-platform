import datetime as dt

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

# 采用模块级积分访问控制的模块。
ACCESS_MODULES = ("sql", "interview")

# item_id 取该值表示"整模块已解锁"的标记行（而非某条内容的免费额度消耗）。
MODULE_UNLOCK_MARKER = 0


class ModuleAccessLog(Base):
    """模块级访问记录（每用户每模块）。

    - ``item_id != 0``：该用户已消耗一次免费名额查看的具体条目。
    - ``item_id == 0``：该用户已用积分一次性解锁整个模块（此后全部可见）。
    """

    __tablename__ = "module_access_log"
    __table_args__ = (
        UniqueConstraint("user_id", "module", "item_id", name="uq_module_access"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    module: Mapped[str] = mapped_column(String(20), nullable=False)
    item_id: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
