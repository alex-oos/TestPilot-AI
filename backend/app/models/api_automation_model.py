from typing import List, Optional
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class ApiEndpoint(Base):
    __tablename__ = "api_endpoints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey("projects.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String)
    method: Mapped[str] = mapped_column(String)
    path: Mapped[str] = mapped_column(String)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    headers_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    body_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    response_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    test_cases: Mapped[List["ApiTestCase"]] = relationship(back_populates="endpoint", cascade="all, delete-orphan")


class ApiEnvironment(Base):
    __tablename__ = "api_environments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey("projects.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String)
    base_url: Mapped[str] = mapped_column(String)
    variables_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_default: Mapped[Optional[str]] = mapped_column(String, default="false")


class ApiTestCase(Base):
    __tablename__ = "api_test_cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    endpoint_id: Mapped[Optional[int]] = mapped_column(ForeignKey("api_endpoints.id"), nullable=True, index=True)
    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey("projects.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    priority: Mapped[str] = mapped_column(String, default="medium")
    status: Mapped[str] = mapped_column(String, default="active")

    endpoint: Mapped[Optional["ApiEndpoint"]] = relationship(back_populates="test_cases")
    steps: Mapped[List["ApiTestStep"]] = relationship(back_populates="test_case", cascade="all, delete-orphan")


class ApiTestStep(Base):
    __tablename__ = "api_test_steps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    test_case_id: Mapped[int] = mapped_column(ForeignKey("api_test_cases.id"), index=True)
    order: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String)
    method: Mapped[str] = mapped_column(String)
    url: Mapped[str] = mapped_column(String)
    headers_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    body_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extractors_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    assertions_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    test_case: Mapped["ApiTestCase"] = relationship(back_populates="steps")


class ApiExecution(Base):
    __tablename__ = "api_executions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey("projects.id"), nullable=True, index=True)
    environment_id: Mapped[Optional[int]] = mapped_column(ForeignKey("api_environments.id"), nullable=True)
    status: Mapped[str] = mapped_column(String, default="running")
    total: Mapped[int] = mapped_column(Integer, default=0)
    passed: Mapped[int] = mapped_column(Integer, default=0)
    failed: Mapped[int] = mapped_column(Integer, default=0)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    trigger_type: Mapped[str] = mapped_column(String, default="manual")

    results: Mapped[List["ApiExecutionResult"]] = relationship(back_populates="execution", cascade="all, delete-orphan")


class ApiExecutionResult(Base):
    __tablename__ = "api_execution_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    execution_id: Mapped[int] = mapped_column(ForeignKey("api_executions.id"), index=True)
    test_case_id: Mapped[Optional[int]] = mapped_column(ForeignKey("api_test_cases.id"), nullable=True)
    status: Mapped[str] = mapped_column(String)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    response_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    response_body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    execution: Mapped["ApiExecution"] = relationship(back_populates="results")
