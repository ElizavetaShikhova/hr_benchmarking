from collections.abc import Sequence
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Department, Enterprise


class HRRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_enterprises(self) -> Sequence[Enterprise]:
        return self.session.scalars(select(Enterprise).order_by(Enterprise.name, Enterprise.id)).all()

    def get_enterprise(self, enterprise_id: int) -> Optional[Enterprise]:
        return self.session.get(Enterprise, enterprise_id)

    def get_departments(self, enterprise_id: int) -> Sequence[Department]:
        return self.session.scalars(
            select(Department).where(Department.enterprise_id == enterprise_id).order_by(Department.name, Department.id)
        ).all()
