from typing import List, Optional
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    task_name: Mapped[Optional[str]] = mapped_column(String, index=True, nullable=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    source_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    doc_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    file_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    file_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, index=True)
    status_text: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    decision_status: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    decision_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    decision_note: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    decision_at: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    mindmap: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    feishu_mindmap_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    user: Mapped[Optional["User"]] = relationship(back_populates="tasks")
    details: Mapped[List["TaskDetail"]] = relationship(back_populates="task")
