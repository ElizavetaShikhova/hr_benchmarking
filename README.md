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

| Метод | Путь | Назначение | Успешный ответ |
|---|---|---|---|
| `POST` | `/conversations` | Создать диалог. | `201`, `Conversation` |
| `GET` | `/conversations` | Получить список диалогов. | `200`, `Conversation[]` |
| `GET` | `/conversations/{conversation_id}` | Получить сообщения и результаты анализа диалога. | `200`, `ConversationDetail` |
| `POST` | `/conversations/{conversation_id}/messages` | Отправить вопрос и запустить анализ. Тело: `{"question": "Вопрос"}`. | `200`, `AnalysisResult` |
| `PATCH` | `/messages/{message_id}` | Сохранить ответ или убрать сохранение. Тело: `{"is_saved": true}` или `false`. | `200`, `Message` |
| `GET` | `/enterprises` | Получить список предприятий. | `200`, `ReferenceItem[]` |
| `GET` | `/enterprises/{enterprise_id}/departments` | Получить подразделения предприятия. | `200`, `ReferenceItem[]` |
| `GET` | `/metrics` | Получить доступные HR-показатели. | `200`, `Metric[]` |
| `GET` | `/data/tables` | Получить список доступных таблиц. | `200`, `TableInfo[]` |
| `GET` | `/data/tables/{table_name}/rows` | Получить строки таблицы с пагинацией: `page=1`, `page_size=50`. | `200`, `TableRows` |
| `GET` | `/data/tables/{table_name}/export` | Скачать таблицу. Параметр `format=csv` или `format=xlsx`, по умолчанию `csv`. | `200`, файл CSV/XLSX |

## Форматы ответов

Схемы определены в `backend/api/schemas.py` и связаны с маршрутами. Они описывают будущие успешные ответы; сейчас ручки продолжают возвращать `501`.

- `Conversation`: `id`, `title`, `created_at`, `updated_at`. Даты — строки ISO 8601.
- `ConversationDetail`: поля диалога и массив `messages` в порядке отправки.
- `Message`: `id`, `conversation_id`, `role` (`user` или `assistant`), `content`, `analysis_plan`, `result_data`, `is_saved`, `created_at`. План — JSON-объект или `null`; результат — `AnalysisResult` или `null`.
- `ReferenceItem`: `id`, `name`. Используется для предприятий и подразделений.
- `Metric`: `code`, `name`, `unit`.
- `TableInfo`: `name`, `label`.
- `TableRows`: `table_name`, `columns`, `rows`, `total`, `page`, `page_size`. `total` — общее число доступных строк до пагинации. Нумерация страниц начинается с 1.

Результат анализа определяется полем `status`:

- `completed`: `message_id`, `summary`, необязательная `visualization`.
- `clarification_needed`: `question` — уточняющий вопрос.
- `insufficient_data`: `message` — объяснение, почему расчёт невозможен.

Все три варианта возвращаются с HTTP `200`. Уточнение и отсутствие данных — состояния анализа.

`visualization` содержит `default_view` (`table` или `chart`) и необязательные `table` и `chart`. Таблица содержит `columns` и `rows`; столбец — объект с `key` и `label`. График содержит `type` (`bar_chart`), `title`, `x_key`, `series` (объекты с `key` и `label`) и `data`. Строки таблицы и данные графика — объекты со скалярными значениями: строкой, числом, булевым значением или `null`.

## Ошибки

- `404`: неизвестный диалог, сообщение, предприятие или таблица. Формат: `{"detail": "Описание ошибки"}`.
- `422`: ошибка параметров или тела запроса. Стандартный формат FastAPI: `{"detail": [{"loc": ["body", "question"], "msg": "Описание ошибки", "type": "Код ошибки"}]}`. Ответ может содержать дополнительные сведения о неверном значении.
- `501`: заглушка ещё не реализована. Формат: `{"detail": "Ручка пока не реализована."}`.
