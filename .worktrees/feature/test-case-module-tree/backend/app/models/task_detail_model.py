from typing import Optional
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class TaskDetail(Base):
    __tablename__ = "task_details"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id"), index=True)
    phase_key: Mapped[str] = mapped_column(String)
    phase_label: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)
    data_json: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    task: Mapped["Task"] = relationship(back_populates="details")
