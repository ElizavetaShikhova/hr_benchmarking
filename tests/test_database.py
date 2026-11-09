import unittest
from datetime import date
from decimal import Decimal

from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext
from sqlalchemy import distinct, func, inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.api.schemas import Message as MessageResponse
from backend.database import engine
from backend.models import Base, Department, Dismissal, EmploymentHistory, Enterprise, HRMetricPlan, Message, Position
from backend.seed import load_demo


def row_counts(session: Session) -> dict[str, int]:
    return {
        table.name: session.scalar(select(func.count()).select_from(table)) for table in Base.metadata.sorted_tables
    }


class DatabaseTests(unittest.TestCase):
    def setUp(self) -> None:
        connection = engine.connect()
        transaction = connection.begin()
        self.session = Session(bind=connection, join_transaction_mode="create_savepoint")
        self.addCleanup(connection.close)
        self.addCleanup(transaction.rollback)
        self.addCleanup(self.session.close)

    def test_migration_matches_models(self) -> None:
        tables = set(inspect(self.session.connection()).get_table_names()) - {"alembic_version"}
        self.assertEqual(tables, set(Base.metadata.tables))
        self.assertEqual(compare_metadata(MigrationContext.configure(self.session.connection()), Base.metadata), [])

    def test_seed_is_repeatable_without_duplicates(self) -> None:
        before = row_counts(self.session)
        self.assertEqual(before, {
            "enterprises": 2, "departments": 3, "positions": 3, "employees": 6, "employment_history": 7,
            "dismissals": 1, "salary_history": 8, "absences": 2, "hr_metric_plans": 3,
            "conversations": 1, "messages": 2,
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

    def test_plans_are_unique_for_enterprise_and_department(self) -> None:
        plans = self.session.scalars(select(HRMetricPlan).order_by(HRMetricPlan.id)).all()
        for plan in plans:
            with self.subTest(department_id=plan.department_id), self.assertRaises(IntegrityError):
                with self.session.begin_nested():
                    self.session.add(HRMetricPlan(
                        enterprise_id=plan.enterprise_id, department_id=plan.department_id,
                        metric_code=plan.metric_code, period=plan.period, target_value=Decimal("1"),
                    ))
                    self.session.flush()

    def test_plan_cannot_use_another_enterprise_department(self) -> None:
        north = self.session.scalars(select(Enterprise).where(Enterprise.name == "Север")).one()
        south = self.session.scalars(select(Enterprise).where(Enterprise.name == "Юг")).one()
        department = self.session.scalars(select(Department).where(Department.enterprise_id == south.id)).one()
        with self.assertRaises(IntegrityError), self.session.begin_nested():
            self.session.add(HRMetricPlan(enterprise_id=north.id, department_id=department.id,
                                          metric_code="headcount", period=date(2026, 9, 1), target_value=Decimal("2")))
            self.session.flush()

    def test_dismissal_is_unique_for_employment(self) -> None:
        dismissal = self.session.scalars(select(Dismissal)).one()
        with self.assertRaises(IntegrityError), self.session.begin_nested():
            self.session.add(Dismissal(employment_id=dismissal.employment_id, dismissal_date=dismissal.dismissal_date,
                                       reason="Повтор", voluntary=False))
            self.session.flush()

    def test_invalid_employment_dates_are_rejected(self) -> None:
        employment = self.session.scalars(select(EmploymentHistory).order_by(EmploymentHistory.id)).first()
        with self.assertRaises(IntegrityError), self.session.begin_nested():
            self.session.add(EmploymentHistory(employee_id=employment.employee_id, position_id=employment.position_id,
                                              start_date=date(2026, 9, 2), end_date=date(2026, 9, 1),
                                              employment_type="full_time"))
            self.session.flush()

    def test_message_json_and_saved_flag_round_trip(self) -> None:
        message = self.session.scalars(select(Message).where(Message.role == "assistant")).one()
        message_id = message.id
        plan = {"operation": "get_metric", "enterprise_ids": [1, 2], "period": {"month": 9, "year": 2026}}
        message.analysis_plan = plan
        message.is_saved = True
        self.session.flush()
        self.session.expire_all()
        restored = self.session.get(Message, message_id)
        self.assertEqual(restored.analysis_plan, plan)
        self.assertTrue(restored.is_saved)
        response = MessageResponse.model_validate(restored, from_attributes=True)
        self.assertEqual(response.result_data.status, "clarification_needed")
        self.assertIsNotNone(response.created_at.tzinfo)
