from typing import List, Optional
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True, unique=True)
    name: Mapped[str] = mapped_column(String, index=True)
    email: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    position: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    department: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    team_id: Mapped[Optional[int]] = mapped_column(ForeignKey("teams.id"), nullable=True)
    role: Mapped[Optional[str]] = mapped_column(String, nullable=True, default="developer")
    level: Mapped[Optional[str]] = mapped_column(String, nullable=True, default="member")
    hire_date: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    sync_source: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    sync_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="active")

    team: Mapped[Optional["Team"]] = relationship(back_populates="members")
    skills: Mapped[List["EmployeeSkill"]] = relationship(back_populates="employee", cascade="all, delete-orphan")
    schedules: Mapped[List["Schedule"]] = relationship(back_populates="employee", cascade="all, delete-orphan")
    leaves: Mapped[List["LeaveRecord"]] = relationship(back_populates="employee", cascade="all, delete-orphan")


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    leader_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    members: Mapped[List["Employee"]] = relationship(back_populates="team")


class EmployeeSkill(Base):
    __tablename__ = "employee_skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    skill_name: Mapped[str] = mapped_column(String)
    level: Mapped[str] = mapped_column(String, default="intermediate")

    employee: Mapped["Employee"] = relationship(back_populates="skills")


class Schedule(Base):
    __tablename__ = "schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey("projects.id"), nullable=True)
    title: Mapped[str] = mapped_column(String)
    schedule_date: Mapped[str] = mapped_column(String, index=True)
    start_time: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    end_time: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    hours: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    schedule_type: Mapped[str] = mapped_column(String, default="work")
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    employee: Mapped["Employee"] = relationship(back_populates="schedules")


class LeaveRecord(Base):
    __tablename__ = "leave_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    leave_type: Mapped[str] = mapped_column(String)
    start_date: Mapped[str] = mapped_column(String)
    end_date: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="pending")
    reason: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    employee: Mapped["Employee"] = relationship(back_populates="leaves")
