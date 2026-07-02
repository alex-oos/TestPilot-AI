from typing import List, Optional
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class Requirement(Base):
    __tablename__ = "requirements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey("projects.id"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    priority: Mapped[str] = mapped_column(String, default="medium")
    status: Mapped[str] = mapped_column(String, default="requirement_review")
    req_type: Mapped[str] = mapped_column(String, default="functional")
    version_id: Mapped[Optional[int]] = mapped_column(ForeignKey("project_versions.id"), nullable=True)
    assignee_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    product_owner_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    dev_owner_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    test_owner_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    project: Mapped[Optional["Project"]] = relationship(back_populates="requirements")
    traces: Mapped[List["RequirementTrace"]] = relationship(back_populates="requirement", cascade="all, delete-orphan")


class RequirementTrace(Base):
    __tablename__ = "requirement_traces"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    requirement_id: Mapped[int] = mapped_column(ForeignKey("requirements.id"), index=True)
    target_type: Mapped[str] = mapped_column(String)
    target_id: Mapped[str] = mapped_column(String)
    relation: Mapped[str] = mapped_column(String, default="covers")

    requirement: Mapped["Requirement"] = relationship(back_populates="traces")


class RequirementNodeMember(Base):
    """每个需求的每个流程节点上绑定的人员"""
    __tablename__ = "requirement_node_members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    requirement_id: Mapped[int] = mapped_column(ForeignKey("requirements.id"), index=True)
    node: Mapped[str] = mapped_column(String, index=True)
    role: Mapped[str] = mapped_column(String)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    planned_time: Mapped[Optional[str]] = mapped_column(String, nullable=True)
