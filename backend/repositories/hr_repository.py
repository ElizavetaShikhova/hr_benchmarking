from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import Date, and_, distinct, func, literal, select, tuple_
from sqlalchemy.orm import Session

from backend import config
from backend.models import Department, Dismissal, EmploymentHistory, Enterprise, HRMetricPlan, Position


class HRRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_enterprises(self) -> Sequence[Enterprise]:
        return self.session.scalars(select(Enterprise).order_by(Enterprise.name, Enterprise.id)).all()

    def enterprise_exists(self, enterprise_id: int) -> bool:
        return self.session.scalar(select(Enterprise.id).where(Enterprise.id == enterprise_id)) is not None

    def get_departments(self, enterprise_id: int) -> Sequence[Department]:
        query = select(Department).where(Department.enterprise_id == enterprise_id)
        return self.session.scalars(query.order_by(Department.name, Department.id)).all()

    def department_exists(self, enterprise_id: int, department_id: int) -> bool:
        query = select(Department.id).where(Department.enterprise_id == enterprise_id, Department.id == department_id)
        return self.session.scalar(query) is not None

    def get_turnover_data(
        self, enterprise_id: int, department_id: Optional[int], period_start: date, period_end: date
    ) -> tuple[int, int, Optional[Decimal]]:
        employment_query = (
            select(EmploymentHistory.id, EmploymentHistory.employee_id, EmploymentHistory.start_date,
                   EmploymentHistory.end_date)
            .join(Position, EmploymentHistory.position_id == Position.id)
            .join(Department, Position.department_id == Department.id)
            .where(Department.enterprise_id == enterprise_id)
        )
        if department_id is not None:
            employment_query = employment_query.where(Department.id == department_id)
        employments = employment_query.cte("scoped_employments")

        days = func.generate_series(0, (period_end - period_start).days).table_valued("day_offset").render_derived()
        day = literal(period_start, Date) + days.c.day_offset
        employee_days = (
            select(func.count(distinct(tuple_(days.c.day_offset, employments.c.employee_id))))
            .select_from(days.join(employments, and_(
                employments.c.start_date <= day,
                (employments.c.end_date >= day) | employments.c.end_date.is_(None),
            )))
            .scalar_subquery()
        )
        dismissals = (
            select(func.count(Dismissal.id))
            .join(employments, Dismissal.employment_id == employments.c.id)
            .where(Dismissal.dismissal_date.between(period_start, period_end))
            .scalar_subquery()
        )
        plan = select(HRMetricPlan.target_value).where(
            HRMetricPlan.enterprise_id == enterprise_id,
            HRMetricPlan.department_id.is_not_distinct_from(department_id),
            HRMetricPlan.metric_code == config.TURNOVER_METRIC_CODE,
            HRMetricPlan.period == period_start,
        ).scalar_subquery()
        query = select(employee_days, dismissals, plan)
        employee_day_count, dismissal_count, target_value = self.session.execute(query).one()
        return employee_day_count, dismissal_count, target_value
