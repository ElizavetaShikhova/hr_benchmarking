from datetime import date
from decimal import Decimal

from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext
from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError

from database_case import DatabaseTestCase, create_sample_conversation

from backend.models import Base, Department, Dismissal, EmploymentHistory, Enterprise, HRMetricPlan, Message


class DatabaseTests(DatabaseTestCase):
    def test_migration_matches_models(self) -> None:
        tables = set(inspect(self.session.connection()).get_table_names()) - {"alembic_version"}
        self.assertEqual(tables, set(Base.metadata.tables))
        self.assertEqual(compare_metadata(MigrationContext.configure(self.session.connection()), Base.metadata), [])

    def test_plans_are_unique_for_enterprise_and_department(self) -> None:
        plans = self.session.scalars(select(HRMetricPlan).order_by(HRMetricPlan.id)).all()
        self.assertEqual({plan.department_id is None for plan in plans}, {True, False})
        for plan in plans:
            with self.subTest(department_id=plan.department_id):
                with self.assertRaises(IntegrityError) as error, self.session.begin_nested():
                    self.session.add(HRMetricPlan(
                        enterprise_id=plan.enterprise_id, department_id=plan.department_id,
                        metric_code=plan.metric_code, period=plan.period, target_value=Decimal("1"),
                    ))
                    self.session.flush()
                self.assertEqual(error.exception.orig.diag.constraint_name, "uq_metric_plan_scope")

    def test_plan_cannot_use_another_enterprise_department(self) -> None:
        north = self.session.scalars(select(Enterprise).where(Enterprise.name == "Север")).one()
        south = self.session.scalars(select(Enterprise).where(Enterprise.name == "Юг")).one()
        department = self.session.scalars(select(Department).where(Department.enterprise_id == south.id)).one()
        with self.assertRaises(IntegrityError) as error, self.session.begin_nested():
            self.session.add(HRMetricPlan(
                enterprise_id=north.id, department_id=department.id, metric_code="headcount",
                period=date(2026, 9, 1), target_value=Decimal("2"),
            ))
            self.session.flush()
        self.assertEqual(error.exception.orig.diag.constraint_name, "fk_metric_plan_department")

    def test_dismissal_is_unique_for_employment(self) -> None:
        dismissal = self.session.scalars(select(Dismissal)).one()
        with self.assertRaises(IntegrityError) as error, self.session.begin_nested():
            self.session.add(Dismissal(
                employment_id=dismissal.employment_id, dismissal_date=dismissal.dismissal_date,
                reason="Повтор", voluntary=False,
            ))
            self.session.flush()
        self.assertEqual(error.exception.orig.diag.constraint_name, "dismissals_employment_id_key")

    def test_invalid_employment_dates_are_rejected(self) -> None:
        employment = self.session.scalars(select(EmploymentHistory).order_by(EmploymentHistory.id)).first()
        with self.assertRaises(IntegrityError) as error, self.session.begin_nested():
            self.session.add(EmploymentHistory(
                employee_id=employment.employee_id, position_id=employment.position_id, employment_type="full_time",
                start_date=date(2026, 9, 2), end_date=date(2026, 9, 1),
            ))
            self.session.flush()
        self.assertEqual(error.exception.orig.diag.constraint_name, "ck_employment_dates")

    def test_message_json_and_saved_flag_round_trip(self) -> None:
        create_sample_conversation(self.session)
        message = self.session.scalars(select(Message).where(Message.role == "assistant")).one()
        message_id = message.id
        plan = {"operation": "get_metric", "enterprise_ids": [1, 2], "period": {"month": 9, "year": 2026}}
        result = {"status": "completed", "rows": [{"turnover_percent": 33.3, "plan_percent": None}]}
        message.analysis_plan = plan
        message.result_data = result
        message.is_saved = True
        self.session.flush()
        self.session.expire_all()
        restored = self.session.get(Message, message_id)
        self.assertEqual(restored.analysis_plan, plan)
        self.assertEqual(restored.result_data, result)
        self.assertTrue(restored.is_saved)
        self.assertIsNotNone(restored.created_at.tzinfo)
