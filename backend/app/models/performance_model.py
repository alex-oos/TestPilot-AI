from typing import List, Optional
from sqlalchemy import ForeignKey, Integer, String, Text, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class PerfScenario(Base):
    __tablename__ = "perf_scenarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey("projects.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    test_type: Mapped[str] = mapped_column(String, default="load")
    target_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    concurrency: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ramp_up_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String, default="draft")

    scripts: Mapped[List["PerfScript"]] = relationship(back_populates="scenario", cascade="all, delete-orphan")
    executions: Mapped[List["PerfExecution"]] = relationship(back_populates="scenario", cascade="all, delete-orphan")


class PerfScript(Base):
    __tablename__ = "perf_scripts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scenario_id: Mapped[int] = mapped_column(ForeignKey("perf_scenarios.id"), index=True)
    name: Mapped[str] = mapped_column(String)
    script_type: Mapped[str] = mapped_column(String, default="k6")
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    scenario: Mapped["PerfScenario"] = relationship(back_populates="scripts")


class PerfExecution(Base):
    __tablename__ = "perf_executions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scenario_id: Mapped[int] = mapped_column(ForeignKey("perf_scenarios.id"), index=True)
    status: Mapped[str] = mapped_column(String, default="running")
    started_at: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    finished_at: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    summary_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    scenario: Mapped["PerfScenario"] = relationship(back_populates="executions")
    results: Mapped[List["PerfResult"]] = relationship(back_populates="execution", cascade="all, delete-orphan")


class PerfResult(Base):
    __tablename__ = "perf_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    execution_id: Mapped[int] = mapped_column(ForeignKey("perf_executions.id"), index=True)
    timestamp: Mapped[str] = mapped_column(String)
    avg_response_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    p95_response_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    p99_response_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    tps: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    error_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    concurrent_users: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    execution: Mapped["PerfExecution"] = relationship(back_populates="results")


class PerfBaseline(Base):
    __tablename__ = "perf_baselines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scenario_id: Mapped[int] = mapped_column(ForeignKey("perf_scenarios.id"), index=True)
    name: Mapped[str] = mapped_column(String)
    avg_response_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    p95_response_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_tps: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_error_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
