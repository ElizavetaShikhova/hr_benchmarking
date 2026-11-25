import unittest
from datetime import date

from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from backend.database import SessionFactory
from backend.models import Base, Department, EmploymentHistory, Enterprise, Position
from temporary_demo_data.seed import load_demo


def row_counts(session: Session) -> dict[str, int]:
    return {
        table.name: session.scalar(select(func.count()).select_from(table)) for table in Base.metadata.sorted_tables
    }


class DemoDataTests(unittest.TestCase):
    def setUp(self) -> None:
        self.session = SessionFactory()
        self.addCleanup(self.session.close)

    def test_seed_is_repeatable_without_duplicates(self) -> None:
        before = row_counts(self.session)
        self.assertEqual(before, {
            "enterprises": 2, "departments": 3, "positions": 3, "employees": 6, "employment_history": 7,
            "dismissals": 1, "salary_history": 0, "absences": 0, "hr_metric_plans": 3,
            "conversations": 0, "messages": 0, "users": 0, "auth_sessions": 0,
        })
        self.assertFalse(load_demo(self.session))
        self.assertEqual(row_counts(self.session), before)

    def test_daily_headcount_is_constant_during_hiring_and_transfer(self) -> None:
        for name, expected in [("Север", 3), ("Юг", 2)]:
            enterprise = self.session.scalars(select(Enterprise).where(Enterprise.name == name)).one()
            for day in range(1, 31):
                current = date(2026, 9, day)
                count = self.session.scalar(
                    select(func.count(distinct(EmploymentHistory.employee_id)))
                    .join(Position, EmploymentHistory.position_id == Position.id)
                    .join(Department, Position.department_id == Department.id)
                    .where(Department.enterprise_id == enterprise.id, EmploymentHistory.start_date <= current,
                           (EmploymentHistory.end_date.is_(None)) | (EmploymentHistory.end_date >= current))
                )
                self.assertEqual(count, expected, (name, current))
