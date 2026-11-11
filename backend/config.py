import os

API_PREFIX = "/api/v1"
DEFAULT_PAGE_SIZE = 50
NOT_IMPLEMENTED_MESSAGE = "Ручка пока не реализована."
CSV_MEDIA_TYPE = "text/csv"
XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql+psycopg://hr:hr@localhost:5432/hr_benchmarking")
DEFAULT_CONVERSATION_TITLE = "Новый диалог"
CONVERSATION_NOT_FOUND_MESSAGE = "Диалог не найден."
MESSAGE_NOT_FOUND_MESSAGE = "Сообщение не найдено."
ENTERPRISE_NOT_FOUND_MESSAGE = "Предприятие не найдено."
DEPARTMENT_NOT_FOUND_MESSAGE = "Подразделение не найдено в указанном предприятии."
TURNOVER_PERIOD_MESSAGE = "Укажите первый день месяца."
TURNOVER_METRIC_CODE = "turnover_rate"
TURNOVER_DECIMAL_PLACES = 4
METRICS = (
    {"code": "headcount", "name": "Численность на дату", "unit": "чел."},
    {"code": "average_headcount", "name": "Средняя численность за период", "unit": "чел."},
    {"code": "hires", "name": "Принято сотрудников", "unit": "чел."},
    {"code": "dismissals", "name": "Уволено сотрудников", "unit": "чел."},
    {"code": TURNOVER_METRIC_CODE, "name": "Текучесть кадров", "unit": "%"},
    {"code": "voluntary_dismissal_share", "name": "Доля добровольных увольнений", "unit": "%"},
    {"code": "average_salary", "name": "Средняя зарплата", "unit": "руб."},
    {"code": "salary_change", "name": "Изменение средней зарплаты", "unit": "руб."},
    {"code": "absence_rate", "name": "Уровень отсутствий", "unit": "%"},
    {"code": "average_tenure", "name": "Средний стаж", "unit": "лет"},
)
