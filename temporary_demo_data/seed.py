from datetime import date
from decimal import Decimal

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from backend.config import TURNOVER_METRIC_CODE
from backend.database import SessionFactory
from backend.models import Department, Dismissal, Employee, EmploymentHistory, Enterprise, HRMetricPlan, Position


def load_demo(session: Session) -> bool:
    session.execute(text("LOCK TABLE enterprises, employees IN SHARE ROW EXCLUSIVE MODE"))
    # All other HR tables reference at least one of these tables through foreign keys.
    if any(session.scalar(select(model.id).limit(1)) is not None for model in (Enterprise, Employee)):
        return False

    north = Enterprise(name="Север", industry="Промышленность", region="Северный")
    south = Enterprise(name="Юг", industry="Промышленность", region="Южный")
    session.add_all([north, south])
    session.flush()

    north_production = Department(enterprise_id=north.id, name="Производство")
    north_admin = Department(enterprise_id=north.id, name="Администрация")
    south_production = Department(enterprise_id=south.id, name="Производство")
    session.add_all([north_production, north_admin, south_production])
    session.flush()

    north_worker_role = Position(department_id=north_production.id, title="Инженер")
    north_admin_role = Position(department_id=north_admin.id, title="Менеджер")
    south_worker_role = Position(department_id=south_production.id, title="Инженер")
    employees = [Employee(birth_date=date(1990 + index, 1, 1), gender=gender)
                 for index, gender in enumerate(["female", "male", "female", "male", "female", "male"])]
    session.add_all([north_worker_role, north_admin_role, south_worker_role, *employees])
    session.flush()

    start = date(2025, 9, 1)
    first_half_end = date(2026, 9, 15)
    second_half_start = date(2026, 9, 16)
    north_worker = EmploymentHistory(employee_id=employees[0].id, position_id=north_worker_role.id, start_date=start,
                                     employment_type="full_time")
    north_leaver = EmploymentHistory(employee_id=employees[1].id, position_id=north_worker_role.id, start_date=start,
                                     end_date=first_half_end, employment_type="full_time")
    north_hire = EmploymentHistory(employee_id=employees[2].id, position_id=north_worker_role.id,
                                   start_date=second_half_start, employment_type="full_time")
    transfer_from = EmploymentHistory(employee_id=employees[3].id, position_id=north_worker_role.id, start_date=start,
                                      end_date=first_half_end, employment_type="full_time")
    transfer_to = EmploymentHistory(employee_id=employees[3].id, position_id=north_admin_role.id,
                                    start_date=second_half_start, employment_type="full_time")
    south_workers = [EmploymentHistory(employee_id=employee.id, position_id=south_worker_role.id, start_date=start,
                                       employment_type="full_time") for employee in employees[4:]]
    session.add_all([north_worker, north_leaver, north_hire, transfer_from, transfer_to, *south_workers])
    session.flush()

    session.add(Dismissal(employment_id=north_leaver.id, dismissal_date=first_half_end,
                          reason="По собственному желанию", voluntary=True))
    session.add_all([
        HRMetricPlan(enterprise_id=north.id, metric_code=TURNOVER_METRIC_CODE, period=date(2026, 9, 1),
                     target_value=Decimal("20")),
        HRMetricPlan(enterprise_id=south.id, metric_code=TURNOVER_METRIC_CODE, period=date(2026, 9, 1),
                     target_value=Decimal("5")),
        HRMetricPlan(enterprise_id=north.id, department_id=north_production.id, metric_code=TURNOVER_METRIC_CODE,
                     period=date(2026, 9, 1), target_value=Decimal("25")),
    ])

    return True


def main() -> None:
    with SessionFactory.begin() as session:
        loaded = load_demo(session)
    print("Демонстрационные данные загружены." if loaded else "В базе уже есть HR-данные, загрузка пропущена.")


if __name__ == "__main__":
    main()
