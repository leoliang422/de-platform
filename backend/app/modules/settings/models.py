from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SiteSetting(Base):
    """站点级可变配置的 key-value 存储（管理员后台可改，改后即时生效，无需重部署）。"""

    __tablename__ = "site_settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False, default="")
