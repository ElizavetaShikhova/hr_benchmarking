from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import CheckConstraint, ForeignKey, ForeignKeyConstraint, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base


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
    __table_args__ = (
        CheckConstraint("end_date IS NULL OR end_date >= start_date", name="ck_employment_dates"),
    )

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
