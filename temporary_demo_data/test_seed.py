import unittest

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.database import SessionFactory
from backend.models import Base
from temporary_demo_data.seed import load_demo


def row_counts(session: Session) -> dict[str, int]:
    return {
        table.name: session.scalar(select(func.count()).select_from(table)) for table in Base.metadata.sorted_tables
    }


class DemoDataTests(unittest.TestCase):
    def setUp(self) -> None:
        self.session = SessionFactory()
        self.addCleanup(self.session.close)

    def test_seed_populates_empty_database_and_is_repeatable(self) -> None:
        self.assertTrue(load_demo(self.session), "Для проверки нужна пустая база с применёнными миграциями.")
        self.session.flush()
        before = row_counts(self.session)
        self.assertEqual(before, {
            "enterprises": 2, "departments": 3, "positions": 3, "employees": 6, "employment_history": 7,
            "dismissals": 1, "salary_history": 0, "absences": 0, "hr_metric_plans": 3,
            "conversations": 0, "messages": 0, "users": 0, "auth_sessions": 0,
        })
        self.assertFalse(load_demo(self.session))
        self.assertEqual(row_counts(self.session), before)
