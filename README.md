## Запуск

Python 3.9 или новее. Из корня проекта:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn backend.main:app --reload
```

## Ручки

Префикс `/api/v1`. Ниже — назначение ручек после реализации.

| Метод | Путь | Назначение |
|---|---|---|
| `POST` | `/conversations` | Создать диалог. |
| `GET` | `/conversations` | Получить список диалогов. |
| `GET` | `/conversations/{conversation_id}` | Получить сообщения и результаты анализа диалога. |
| `POST` | `/conversations/{conversation_id}/messages` | Отправить вопрос и запустить анализ. Тело: `{"question": "Вопрос"}`. |
| `PATCH` | `/messages/{message_id}` | Сохранить ответ или убрать сохранение. Тело: `{"is_saved": true}` или `false`. |
| `GET` | `/enterprises` | Получить список предприятий. |
| `GET` | `/enterprises/{enterprise_id}/departments` | Получить подразделения предприятия. |
| `GET` | `/metrics` | Получить доступные HR-показатели. |
| `GET` | `/data/tables` | Получить список доступных таблиц. |
| `GET` | `/data/tables/{table_name}/rows` | Получить строки таблицы с пагинацией: `page=1`, `page_size=50`. |
| `GET` | `/data/tables/{table_name}/export` | Скачать таблицу. Параметр `format=csv` или `format=xlsx`, по умолчанию `csv`. |
