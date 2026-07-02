from typing import List, Optional
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class Defect(Base):
    __tablename__ = "defects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey("projects.id"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    severity: Mapped[str] = mapped_column(String, default="medium")
    priority: Mapped[str] = mapped_column(String, default="medium")
    status: Mapped[str] = mapped_column(String, default="open")
    defect_type: Mapped[str] = mapped_column(String, default="functional")
    module: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    reporter_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    assignee_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    requirement_id: Mapped[Optional[int]] = mapped_column(ForeignKey("requirements.id"), nullable=True)
    version_id: Mapped[Optional[int]] = mapped_column(ForeignKey("project_versions.id"), nullable=True)
    environment: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    steps_to_reproduce: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expected_result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    actual_result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    closed_at: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    project: Mapped[Optional["Project"]] = relationship(back_populates="defects")
    comments: Mapped[List["DefectComment"]] = relationship(back_populates="defect", cascade="all, delete-orphan")
    attachments: Mapped[List["DefectAttachment"]] = relationship(back_populates="defect", cascade="all, delete-orphan")
    history: Mapped[List["DefectHistory"]] = relationship(back_populates="defect", cascade="all, delete-orphan")


class DefectComment(Base):
    __tablename__ = "defect_comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    defect_id: Mapped[int] = mapped_column(ForeignKey("defects.id"), index=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    content: Mapped[str] = mapped_column(Text)

    defect: Mapped["Defect"] = relationship(back_populates="comments")


class DefectAttachment(Base):
    __tablename__ = "defect_attachments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    defect_id: Mapped[int] = mapped_column(ForeignKey("defects.id"), index=True)
    file_name: Mapped[str] = mapped_column(String)
    file_path: Mapped[str] = mapped_column(String)
    file_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    defect: Mapped["Defect"] = relationship(back_populates="attachments")


class DefectHistory(Base):
    __tablename__ = "defect_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    defect_id: Mapped[int] = mapped_column(ForeignKey("defects.id"), index=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    field: Mapped[str] = mapped_column(String)
    old_value: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    new_value: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    defect: Mapped["Defect"] = relationship(back_populates="history")
