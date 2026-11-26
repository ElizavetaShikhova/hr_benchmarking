from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pwdlib import PasswordHash
from sqlalchemy import (
    CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Index, Numeric, String, Text, UniqueConstraint,
    false, func, true,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from backend import config

password_hasher = PasswordHash.recommended()


class Base(DeclarativeBase):
    pass


class Enterprise(Base):
    __tablename__ = "enterprises"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    industry: Mapped[str]
    region: Mapped[str]


class Department(Base):
    __tablename__ = "departments"
    __table_args__ = (UniqueConstraint("id", "enterprise_id", name="uq_departments_enterprise"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    enterprise_id: Mapped[int] = mapped_column(ForeignKey("enterprises.id"))
    name: Mapped[str]


class Position(Base):
    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(primary_key=True)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"))
    title: Mapped[str]


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True)
    birth_date: Mapped[date]
    gender: Mapped[str]


class EmploymentHistory(Base):
    __tablename__ = "employment_history"
    __table_args__ = (CheckConstraint("end_date IS NULL OR end_date >= start_date", name="ck_employment_dates"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    position_id: Mapped[int] = mapped_column(ForeignKey("positions.id"))
    start_date: Mapped[date]
    end_date: Mapped[Optional[date]]
    employment_type: Mapped[str]


class Dismissal(Base):
    __tablename__ = "dismissals"

    id: Mapped[int] = mapped_column(primary_key=True)
    employment_id: Mapped[int] = mapped_column(ForeignKey("employment_history.id"), unique=True)
    dismissal_date: Mapped[date]
    reason: Mapped[str]
    voluntary: Mapped[bool]


class SalaryHistory(Base):
    __tablename__ = "salary_history"
    __table_args__ = (
        CheckConstraint("effective_to IS NULL OR effective_to >= effective_from", name="ck_salary_dates"),
        CheckConstraint("salary >= 0", name="ck_salary_nonnegative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    employment_id: Mapped[int] = mapped_column(ForeignKey("employment_history.id"))
    effective_from: Mapped[date]
    effective_to: Mapped[Optional[date]]
    salary: Mapped[Decimal] = mapped_column(Numeric(14, 2))


class Absence(Base):
    __tablename__ = "absences"
    __table_args__ = (CheckConstraint("end_date >= start_date", name="ck_absence_dates"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    start_date: Mapped[date]
    end_date: Mapped[date]
    absence_type: Mapped[str]


class HRMetricPlan(Base):
    __tablename__ = "hr_metric_plans"
    __table_args__ = (
        ForeignKeyConstraint(
            ["department_id", "enterprise_id"], ["departments.id", "departments.enterprise_id"],
            name="fk_metric_plan_department",
        ),
        UniqueConstraint(
            "enterprise_id", "department_id", "metric_code", "period",
            name="uq_metric_plan_scope", postgresql_nulls_not_distinct=True,
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    enterprise_id: Mapped[int] = mapped_column(ForeignKey("enterprises.id"))
    department_id: Mapped[Optional[int]]
    metric_code: Mapped[str]
    period: Mapped[date]
    target_value: Mapped[Decimal] = mapped_column(Numeric(14, 4))


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(server_default=true())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (Index("ix_conversations_user_updated_at_id", "user_id", "updated_at", "id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", name="fk_conversations_user_id"))
    title: Mapped[str] = mapped_column(server_default=config.DEFAULT_CONVERSATION_TITLE)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    messages: Mapped[list["Message"]] = relationship(order_by=lambda: (Message.created_at, Message.id), viewonly=True)


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (CheckConstraint("role IN ('user', 'assistant')", name="ck_message_role"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"))
    role: Mapped[str]
    content: Mapped[str] = mapped_column(Text)
    analysis_plan: Mapped[Optional[dict[str, object]]] = mapped_column(JSONB(none_as_null=True))
    result_data: Mapped[Optional[dict[str, object]]] = mapped_column(JSONB(none_as_null=True))
    is_saved: Mapped[bool] = mapped_column(server_default=false())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
