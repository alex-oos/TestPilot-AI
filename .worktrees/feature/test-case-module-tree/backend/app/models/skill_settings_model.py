"""QA Skill 全局设置表模型（单行）。

作者：Zhao Wang
"""

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class SkillSettings(Base):
    """QA Skill 全局开关等设置（id 固定为 1）。"""

    __tablename__ = "skill_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    qa_skills_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[str] = mapped_column(String, default="")
    updated_at: Mapped[str] = mapped_column(String, default="")
