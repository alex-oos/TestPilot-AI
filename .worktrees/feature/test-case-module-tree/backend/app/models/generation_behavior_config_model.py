from sqlalchemy import Boolean, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

class GenerationBehaviorConfig(Base):
    __tablename__ = "generation_behavior_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    config_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    name: Mapped[str] = mapped_column(String, default="")
    output_mode: Mapped[str] = mapped_column(String, default="stream")
    enable_ai_review: Mapped[bool] = mapped_column(Boolean, default=True)
    review_timeout_seconds: Mapped[int] = mapped_column(Integer, default=1500)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
