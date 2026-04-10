from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class NotificationConfig(Base):
    __tablename__ = "notification_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    channel: Mapped[str] = mapped_column(String, unique=True, index=True)  # feishu|dingtalk|wecom
    name: Mapped[str] = mapped_column(String, default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    webhook: Mapped[str] = mapped_column(String, default="")
    secret: Mapped[str] = mapped_column(String, default="")
    custom_keyword: Mapped[str] = mapped_column(String, default="")
