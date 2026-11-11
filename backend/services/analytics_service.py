from dataclasses import dataclass
from decimal import Decimal
from typing import Literal, Optional

from backend.config import TURNOVER_DECIMAL_PLACES


@dataclass(frozen=True)
class TurnoverComparison:
    status: Literal["completed", "insufficient_data"]
    average_headcount: float
    dismissals: int
    turnover_percent: Optional[float]
    plan_percent: Optional[float]
    deviation_pp: Optional[float]


def calculate_turnover(
    employee_days: int, period_days: int, dismissals: int, plan_percent: Optional[Decimal]
) -> TurnoverComparison:
    average_headcount = Decimal(employee_days) / period_days
    turnover = Decimal(dismissals * period_days * 100) / employee_days if employee_days else None
    deviation = turnover - plan_percent if turnover is not None and plan_percent is not None else None
    return TurnoverComparison(
        status="completed" if turnover is not None else "insufficient_data",
        average_headcount=float(round(average_headcount, TURNOVER_DECIMAL_PLACES)),
        dismissals=dismissals,
        turnover_percent=float(round(turnover, TURNOVER_DECIMAL_PLACES)) if turnover is not None else None,
        plan_percent=float(plan_percent) if plan_percent is not None else None,
        deviation_pp=float(round(deviation, TURNOVER_DECIMAL_PLACES)) if deviation is not None else None,
    )
