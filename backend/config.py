import os

API_PREFIX = "/api/v1"
DEFAULT_PAGE_SIZE = 50
NOT_IMPLEMENTED_MESSAGE = "Ручка пока не реализована."
CSV_MEDIA_TYPE = "text/csv"
XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql+psycopg://hr:hr@localhost:5432/hr_benchmarking")
DEFAULT_CONVERSATION_TITLE = "Новый диалог"
