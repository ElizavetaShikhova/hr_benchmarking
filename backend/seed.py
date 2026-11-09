from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import SessionFactory
from backend.models import (
    Absence,
    Base,
    Conversation,
    Department,
    Dismissal,
    Employee,
    EmploymentHistory,
    Enterprise,
    HRMetricPlan,
    Message,
    Position,
    SalaryHistory,
)


def load_demo(session: Session) -> bool:
    if any(session.scalar(select(table.c.id).limit(1)) is not None for table in Base.metadata.sorted_tables):
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
    session.add_all([north_worker_role, north_admin_role, south_worker_role])
    employees = [Employee(birth_date=date(1990 + index, 1, 1), gender=gender)
                 for index, gender in enumerate(["female", "male", "female", "male", "female", "male"])]
    session.add_all(employees)
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
        SalaryHistory(employment_id=north_worker.id, effective_from=start, effective_to=date(2026, 8, 31),
                      salary=Decimal("80000")),
        SalaryHistory(employment_id=north_worker.id, effective_from=date(2026, 9, 1), salary=Decimal("90000")),
        *[SalaryHistory(employment_id=employment.id, effective_from=employment.start_date,
                        effective_to=employment.end_date, salary=Decimal(amount))
          for employment, amount in [(north_leaver, "60000"), (north_hire, "60000"), (transfer_from, "30000"),
                                     (transfer_to, "30000"), *[(worker, "60000") for worker in south_workers]]],
    ])
    session.add_all([
        Absence(employee_id=employees[0].id, start_date=date(2026, 9, 7), end_date=date(2026, 9, 11),
                absence_type="vacation"),
        Absence(employee_id=employees[4].id, start_date=date(2026, 9, 14), end_date=date(2026, 9, 15),
                absence_type="sick_leave"),
        HRMetricPlan(enterprise_id=north.id, metric_code="turnover_rate", period=date(2026, 9, 1),
                     target_value=Decimal("20")),
        HRMetricPlan(enterprise_id=south.id, metric_code="turnover_rate", period=date(2026, 9, 1),
                     target_value=Decimal("5")),
        HRMetricPlan(enterprise_id=north.id, department_id=north_production.id, metric_code="turnover_rate",
                     period=date(2026, 9, 1), target_value=Decimal("25")),
    ])

    conversation = Conversation(title="Сравнение предприятий")
    session.add(conversation)
    session.flush()
    question = "Какой показатель и за какой период сравнить?"
    session.add_all([
        Message(conversation_id=conversation.id, role="user", content="Сравни предприятия"),
        Message(conversation_id=conversation.id, role="assistant", content=question,
                result_data={"status": "clarification_needed", "question": question}),
    ])
    return True


def main() -> None:
    with SessionFactory.begin() as session:
        loaded = load_demo(session)
    print("Демонстрационные данные загружены." if loaded else "База уже содержит данные, загрузка пропущена.")


if __name__ == "__main__":
    main()
