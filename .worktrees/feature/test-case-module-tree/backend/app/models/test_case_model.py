from typing import List, Optional
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class TestCase(Base):
    __tablename__ = "test_cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey("projects.id"), nullable=True, index=True)
    requirement_id: Mapped[Optional[int]] = mapped_column(ForeignKey("requirements.id"), nullable=True, index=True)
    task_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    title: Mapped[str] = mapped_column(String, index=True)
    module: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    priority: Mapped[str] = mapped_column(String, default="medium")
    case_type: Mapped[str] = mapped_column(String, default="functional")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    precondition: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String, default="active")
    source: Mapped[str] = mapped_column(String, default="manual")
    assignee_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    last_result: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    steps: Mapped[List["TestCaseStep"]] = relationship(back_populates="test_case", cascade="all, delete-orphan")


class TestCaseStep(Base):
    __tablename__ = "test_case_steps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    test_case_id: Mapped[int] = mapped_column(ForeignKey("test_cases.id"), index=True)
    order: Mapped[int] = mapped_column(Integer)
    action: Mapped[str] = mapped_column(Text)
    expected_result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    test_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    test_case: Mapped["TestCase"] = relationship(back_populates="steps")
