from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from database_case import DatabaseTestCase

from backend import config
from backend.database import get_session
from backend.main import app
from backend.models import Conversation, Department, Enterprise, Message


class APITests(DatabaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        app.dependency_overrides[get_session] = lambda: self.session
        self.addCleanup(app.dependency_overrides.pop, get_session)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def test_enterprises_and_departments_are_loaded_and_filtered(self) -> None:
        response = self.client.get("/api/v1/enterprises")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["name"] for item in response.json()], ["Север", "Юг"])
        for enterprise in response.json():
            departments = self.client.get(f"/api/v1/enterprises/{enterprise['id']}/departments")
            self.assertEqual(departments.status_code, 200)
            expected = self.session.scalars(
                select(Department).where(Department.enterprise_id == enterprise["id"])
                .order_by(Department.name, Department.id)
            ).all()
            self.assertEqual(departments.json(), [{"id": item.id, "name": item.name} for item in expected])

    def test_existing_enterprise_without_departments_returns_empty_list(self) -> None:
        enterprise = Enterprise(name="Без подразделений", industry="Тест", region="Тест")
        self.session.add(enterprise)
        self.session.flush()
        response = self.client.get(f"/api/v1/enterprises/{enterprise.id}/departments")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_metrics_match_architecture(self) -> None:
        response = self.client.get("/api/v1/metrics")
        self.assertEqual(response.status_code, 200)
        metrics = {item["code"]: item for item in response.json()}
        self.assertEqual(len(response.json()), 10)
        self.assertEqual(len(metrics), 10)
        self.assertEqual(metrics["turnover_rate"], {"code": "turnover_rate", "name": "Текучесть кадров", "unit": "%"})
        self.assertEqual(metrics["headcount"]["unit"], "чел.")
        self.assertEqual(metrics["average_salary"]["unit"], "руб.")

    def test_create_conversation_is_persisted_and_has_empty_history(self) -> None:
        response = self.client.post("/api/v1/conversations")
        self.assertEqual(response.status_code, 201)
        conversation = response.json()
        self.assertEqual(conversation["title"], config.DEFAULT_CONVERSATION_TITLE)
        self.assertIsNotNone(datetime.fromisoformat(conversation["created_at"].replace("Z", "+00:00")).tzinfo)
        with Session(bind=self.session.connection(), join_transaction_mode="create_savepoint") as session:
            self.assertEqual(session.get(Conversation, conversation["id"]).title, config.DEFAULT_CONVERSATION_TITLE)
        history = self.client.get(f"/api/v1/conversations/{conversation['id']}")
        self.assertEqual(history.status_code, 200)
        self.assertEqual(history.json(), {**conversation, "messages": []})
        self.assertEqual(self.client.get("/api/v1/conversations").json()[0], conversation)

    def test_conversation_list_can_be_empty(self) -> None:
        self.session.execute(delete(Message))
        self.session.execute(delete(Conversation))
        response = self.client.get("/api/v1/conversations")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_history_keeps_message_order_and_results(self) -> None:
        conversation = self.session.scalars(select(Conversation)).one()
        messages = self.session.scalars(select(Message).order_by(Message.id)).all()
        messages[0].created_at = messages[1].created_at
        self.session.flush()
        response = self.client.get(f"/api/v1/conversations/{conversation.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.json()["messages"]], [item.id for item in messages])
        self.assertEqual([item["role"] for item in response.json()["messages"]], ["user", "assistant"])
        self.assertEqual(response.json()["messages"][1]["result_data"], {
            "status": "clarification_needed", "question": "Какой показатель и за какой период сравнить?",
        })
        other = self.client.post("/api/v1/conversations").json()
        self.assertEqual(self.client.get(f"/api/v1/conversations/{other['id']}").json()["messages"], [])

    def test_send_message_persists_question_and_updates_conversation_order(self) -> None:
        conversation = self.session.scalars(select(Conversation)).one()
        conversation.updated_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
        self.session.flush()
        other = self.client.post("/api/v1/conversations").json()
        self.session.get(Conversation, other["id"]).updated_at = datetime(2021, 1, 1, tzinfo=timezone.utc)
        self.session.flush()
        self.assertNotEqual(self.client.get("/api/v1/conversations").json()[0]["id"], conversation.id)
        question = "Сравни текучесть за сентябрь 2026 года"
        response = self.client.post(f"/api/v1/conversations/{conversation.id}/messages", json={"question": question})
        self.assertEqual(response.status_code, 202)
        message = response.json()
        self.assertEqual(message["conversation_id"], conversation.id)
        self.assertEqual(message["role"], "user")
        self.assertEqual(message["content"], question)
        self.assertIsNone(message["analysis_plan"])
        self.assertIsNone(message["result_data"])
        self.assertFalse(message["is_saved"])
        history = self.client.get(f"/api/v1/conversations/{conversation.id}").json()
        self.assertEqual(len(history["messages"]), 3)
        self.assertEqual(history["messages"][-1], message)
        self.assertEqual(self.client.get("/api/v1/conversations").json()[0]["id"], conversation.id)
        self.session.expire_all()
        self.assertEqual(self.session.get(Message, message["id"]).content, question)

    def test_saved_flag_is_persisted_without_changing_analysis_or_history_order(self) -> None:
        message = self.session.scalars(select(Message).where(Message.role == "assistant")).one()
        conversation = self.session.get(Conversation, message.conversation_id)
        original_updated_at = conversation.updated_at
        original_result = message.result_data
        for saved in [True, False]:
            response = self.client.patch(f"/api/v1/messages/{message.id}", json={"is_saved": saved})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["is_saved"], saved)
            self.assertEqual(response.json()["result_data"], original_result)
            self.session.expire_all()
            self.assertEqual(self.session.get(Message, message.id).is_saved, saved)
            self.assertEqual(self.session.get(Conversation, conversation.id).updated_at, original_updated_at)
            history = self.client.get(f"/api/v1/conversations/{conversation.id}").json()
            self.assertEqual(history["messages"][-1]["is_saved"], saved)

    def test_unknown_ids_return_404_without_creating_messages(self) -> None:
        before = self.session.scalar(select(func.count()).select_from(Message))
        requests = [
            ("GET", "/api/v1/conversations/-1", None, config.CONVERSATION_NOT_FOUND_MESSAGE),
            ("POST", "/api/v1/conversations/-1/messages", {"question": "Вопрос"},
             config.CONVERSATION_NOT_FOUND_MESSAGE),
            ("PATCH", "/api/v1/messages/-1", {"is_saved": True}, config.MESSAGE_NOT_FOUND_MESSAGE),
            ("GET", "/api/v1/enterprises/-1/departments", None, config.ENTERPRISE_NOT_FOUND_MESSAGE),
        ]
        for method, path, body, detail in requests:
            with self.subTest(path=path):
                response = self.client.request(method, path, json=body)
                self.assertEqual(response.status_code, 404)
                self.assertEqual(response.json(), {"detail": detail})
        self.assertEqual(self.session.scalar(select(func.count()).select_from(Message)), before)

    def test_invalid_requests_return_422_without_creating_messages(self) -> None:
        conversation = self.session.scalars(select(Conversation)).one()
        before = self.session.scalar(select(func.count()).select_from(Message))
        for body in [{}, {"question": ""}, {"question": " \n\t"}, {"question": None}, {"question": 12}]:
            with self.subTest(body=body):
                response = self.client.post(f"/api/v1/conversations/{conversation.id}/messages", json=body)
                self.assertEqual(response.status_code, 422)
        self.assertEqual(self.client.patch("/api/v1/messages/-1", json={}).status_code, 422)
        self.assertEqual(self.client.get("/api/v1/conversations/invalid").status_code, 422)
        self.assertEqual(self.session.scalar(select(func.count()).select_from(Message)), before)

    def test_data_endpoints_remain_stubs(self) -> None:
        for path in ["/data/tables", "/data/tables/enterprises/rows", "/data/tables/enterprises/export"]:
            with self.subTest(path=path):
                response = self.client.get(f"/api/v1{path}")
                self.assertEqual(response.status_code, 501)
                self.assertEqual(response.json(), {"detail": config.NOT_IMPLEMENTED_MESSAGE})
