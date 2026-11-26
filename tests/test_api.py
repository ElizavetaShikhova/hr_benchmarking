from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from database_case import DatabaseTestCase, create_sample_conversation

from backend import config
from backend.api.auth import hash_token
from backend.database import get_session
from backend.main import app
from backend.manage_users import add_user, set_access
from backend.models import (
    AuthSession, Conversation, Department, Dismissal, Employee, EmploymentHistory, Enterprise, HRMetricPlan,
    Message, Position, User,
)


class APIClientTestCase(DatabaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        app.dependency_overrides[get_session] = lambda: self.session
        self.addCleanup(app.dependency_overrides.pop, get_session)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)


class APITests(APIClientTestCase):
    def setUp(self) -> None:
        super().setUp()
        user = User(email="fixture@example.com", password_hash="unused-by-session-fixture")
        self.session.add(user)
        self.session.flush()
        self.user_id = user.id
        token = "fixture-api-session"
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        self.session.add(AuthSession(token_hash=hash_token(token), user_id=self.user_id, expires_at=expires_at))
        self.session.flush()
        self.client.headers["Authorization"] = f"Bearer {token}"

    def test_enterprises_and_departments_are_loaded_and_filtered(self) -> None:
        response = self.client.get("/api/v1/enterprises")
        self.assertEqual(response.status_code, 200)
        enterprises = response.json()
        self.assertEqual([item["name"] for item in enterprises], ["Север", "Юг"])
        expected = {"Север": ["Администрация", "Производство"], "Юг": ["Производство"]}
        department_ids = set()
        for enterprise in enterprises:
            name = enterprise["name"]
            with self.subTest(enterprise=name):
                response = self.client.get(f"/api/v1/enterprises/{enterprise['id']}/departments")
                self.assertEqual(response.status_code, 200)
                departments = response.json()
                self.assertEqual([item["name"] for item in departments], expected[name])
                department_ids.update(item["id"] for item in departments)
        self.assertEqual(len(department_ids), 3)

    def test_existing_enterprise_without_departments_returns_empty_list(self) -> None:
        enterprise = Enterprise(name="Без подразделений", industry="Тест", region="Тест")
        self.session.add(enterprise)
        self.session.flush()
        response = self.client.get(f"/api/v1/enterprises/{enterprise.id}/departments")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_metrics_returns_catalog_with_units(self) -> None:
        response = self.client.get("/api/v1/metrics")
        self.assertEqual(response.status_code, 200)
        metrics = {item["code"]: item for item in response.json()}
        self.assertEqual(len(response.json()), 10)
        self.assertEqual(len(metrics), 10)
        self.assertEqual(metrics["turnover_rate"], {"code": "turnover_rate", "name": "Текучесть кадров", "unit": "%"})
        self.assertEqual(metrics["headcount"]["unit"], "чел.")
        self.assertEqual(metrics["average_salary"]["unit"], "руб.")

    def test_turnover_compares_demo_values_with_the_plan_for_each_scope(self) -> None:
        enterprises = {item["name"]: item["id"] for item in self.client.get("/api/v1/enterprises").json()}
        north, south = enterprises["Север"], enterprises["Юг"]
        departments = self.client.get(f"/api/v1/enterprises/{north}/departments").json()
        by_name = {item["name"]: item["id"] for item in departments}
        for scope, expected in [
            ({"enterprise_id": north}, (3.0, 1, 33.3333, 20.0, 13.3333)),
            ({"enterprise_id": south}, (2.0, 0, 0.0, 5.0, -5.0)),
            ({"enterprise_id": north, "department_id": by_name["Производство"]}, (2.5, 1, 40.0, 25.0, 15.0)),
            ({"enterprise_id": north, "department_id": by_name["Администрация"]}, (0.5, 0, 0.0, None, None)),
        ]:
            with self.subTest(scope=scope):
                response = self.client.get("/api/v1/metrics/turnover", params={**scope, "period": "2026-09-01"})
                self.assertEqual(response.status_code, 200, response.text)
                average, dismissals, turnover, plan, deviation = expected
                self.assertEqual(response.json(), {
                    "status": "completed", "average_headcount": average, "dismissals": dismissals,
                    "turnover_percent": turnover, "plan_percent": plan, "deviation_pp": deviation,
                })

    def test_turnover_counts_both_month_boundaries_and_deduplicates_employee_days(self) -> None:
        enterprise_id = self.session.scalar(select(Enterprise.id).order_by(Enterprise.id).limit(1))
        department = Department(enterprise_id=enterprise_id, name="Проверка границ периода")
        self.session.add(department)
        self.session.flush()
        position = Position(department_id=department.id, title="Инженер")
        self.session.add(position)
        self.session.flush()
        first_employee, second_employee = self.session.scalars(select(Employee.id).order_by(Employee.id).limit(2)).all()
        for employee_id, day, dismissed in [
            (first_employee, date(2028, 2, 1), True),
            (first_employee, date(2028, 2, 1), False),
            (second_employee, date(2028, 2, 29), True),
            (second_employee, date(2028, 3, 1), True),
        ]:
            employment = EmploymentHistory(
                employee_id=employee_id, position_id=position.id, start_date=day, end_date=day, employment_type="full_time",
            )
            self.session.add(employment)
            self.session.flush()
            if dismissed:
                self.session.add(Dismissal(employment_id=employment.id, dismissal_date=day, reason="Тест", voluntary=False))
        response = self.client.get("/api/v1/metrics/turnover", params={
            "enterprise_id": enterprise_id, "department_id": department.id, "period": "2028-02-01",
        })
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), {
            "status": "completed", "average_headcount": 0.069, "dismissals": 2, "turnover_percent": 2900.0,
            "plan_percent": None, "deviation_pp": None,
        })

    def test_turnover_with_no_employees_keeps_the_plan_but_has_no_rate(self) -> None:
        enterprise_id = self.session.scalar(select(Enterprise.id).order_by(Enterprise.id).limit(1))
        self.session.add(HRMetricPlan(
            enterprise_id=enterprise_id, metric_code=config.TURNOVER_METRIC_CODE,
            period=date(2025, 8, 1), target_value=Decimal("0"),
        ))
        self.session.flush()
        response = self.client.get("/api/v1/metrics/turnover", params={
            "enterprise_id": enterprise_id, "period": "2025-08-01",
        })
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), {
            "status": "insufficient_data", "average_headcount": 0.0, "dismissals": 0, "turnover_percent": None,
            "plan_percent": 0.0, "deviation_pp": None,
        })

    def test_turnover_validates_the_month_and_department_ownership(self) -> None:
        first, second = self.session.scalars(select(Enterprise.id).order_by(Enterprise.id)).all()
        department_id = self.session.scalar(select(Department.id).where(Department.enterprise_id == second).limit(1))
        response = self.client.get("/api/v1/metrics/turnover", params={
            "enterprise_id": first, "department_id": department_id, "period": "2026-09-01",
        })
        self.assertEqual(response.status_code, 404)
        response = self.client.get("/api/v1/metrics/turnover", params={
            "enterprise_id": first, "period": "2026-09-02",
        })
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"][0]["loc"], ["query", "period"])

    def test_create_conversation_is_persisted_and_has_empty_history(self) -> None:
        response = self.client.post("/api/v1/conversations")
        self.assertEqual(response.status_code, 201)
        conversation = response.json()
        self.assertEqual(conversation["title"], "Новый диалог")
        self.assertIsNotNone(datetime.fromisoformat(conversation["created_at"].replace("Z", "+00:00")).tzinfo)
        with Session(bind=self.session.connection(), join_transaction_mode="create_savepoint") as session:
            created = session.get(Conversation, conversation["id"])
            self.assertEqual(created.title, conversation["title"])
            self.assertEqual(created.user_id, self.user_id)
        history = self.client.get(f"/api/v1/conversations/{conversation['id']}")
        self.assertEqual(history.status_code, 200)
        self.assertEqual(history.json(), {**conversation, "messages": []})
        self.assertEqual(self.client.get("/api/v1/conversations").json()[0], conversation)

    def test_ownerless_conversation_is_hidden(self) -> None:
        legacy_id = create_sample_conversation(self.session).id
        response = self.client.get("/api/v1/conversations")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])
        self.assertEqual(self.client.get(f"/api/v1/conversations/{legacy_id}").status_code, 404)

    def test_history_keeps_message_order_and_results(self) -> None:
        conversation = create_sample_conversation(self.session, self.user_id)
        first_question, answer = conversation.messages
        first_question.created_at = answer.created_at = datetime(2021, 1, 1, tzinfo=timezone.utc)
        earlier_message = Message(conversation_id=conversation.id, role="user", content="Ранний вопрос",
                                  created_at=datetime(2020, 1, 1, tzinfo=timezone.utc))
        self.session.add(earlier_message)
        self.session.flush()
        self.session.expire(conversation, ["messages"])
        response = self.client.get(f"/api/v1/conversations/{conversation.id}")
        self.assertEqual(response.status_code, 200)
        messages = response.json()["messages"]
        self.assertEqual([item["content"] for item in messages], [
            "Ранний вопрос", "Сравни предприятия", "Какой показатель и за какой период сравнить?",
        ])
        self.assertEqual([item["role"] for item in messages], ["user", "user", "assistant"])
        self.assertEqual(messages[-1]["result_data"], {
            "status": "clarification_needed", "question": "Какой показатель и за какой период сравнить?",
        })

    def test_send_message_persists_question_and_updates_conversation_order(self) -> None:
        conversation = create_sample_conversation(self.session, self.user_id)
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
        conversation = create_sample_conversation(self.session, self.user_id)
        message = self.session.scalars(select(Message).where(Message.role == "assistant")).one()
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
        conversation = create_sample_conversation(self.session, self.user_id)
        before = self.session.scalar(select(func.count()).select_from(Message))
        for body in [{}, {"question": ""}, {"question": " \n\t"}, {"question": None}, {"question": 12}]:
            with self.subTest(body=body):
                response = self.client.post(f"/api/v1/conversations/{conversation.id}/messages", json=body)
                self.assertEqual(response.status_code, 422)
        self.assertEqual(self.client.patch("/api/v1/messages/-1", json={}).status_code, 422)
        self.assertEqual(self.client.get("/api/v1/conversations/invalid").status_code, 422)
        self.assertEqual(self.session.scalar(select(func.count()).select_from(Message)), before)


class AuthTests(APIClientTestCase):
    password = "test account passphrase"

    def login(self, email: str) -> dict[str, str]:
        response = self.client.post("/api/v1/auth/login", json={"email": email, "password": self.password})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def test_only_active_accounts_can_log_in_and_use_sessions(self) -> None:
        email = "owner@example.com"
        credentials = {"email": email, "password": self.password}
        for path in ["/api/v1/conversations", "/api/v1/metrics", "/api/v1/auth/me"]:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.headers["WWW-Authenticate"], "Bearer")
        self.assertEqual(self.client.post("/api/v1/auth/register", json=credentials).status_code, 404)
        self.assertEqual(self.client.post("/api/v1/auth/login", json=credentials).status_code, 401)

        user_id = add_user(self.session, email, self.password)
        self.assertIsNotNone(user_id)
        self.assertTrue(self.session.get(User, user_id).password_hash.startswith("$argon2id$"))
        wrong_credentials = {**credentials, "password": "incorrect test password"}
        self.assertEqual(self.client.post("/api/v1/auth/login", json=wrong_credentials).status_code, 401)
        headers = self.login("OWNER@EXAMPLE.COM")
        token = headers["Authorization"].split()[1]
        stored_hash = self.session.scalar(select(AuthSession.token_hash).where(AuthSession.user_id == user_id))
        self.assertRegex(stored_hash, r"^[0-9a-f]{64}$")
        self.assertNotEqual(stored_hash, token)
        profile = self.client.get("/api/v1/auth/me", headers=headers).json()
        self.assertEqual(set(profile), {"id", "email", "created_at"})
        self.assertEqual(profile["email"], email)

        set_access(self.session, email, False)
        self.assertEqual(self.client.get("/api/v1/auth/me", headers=headers).status_code, 401)
        self.assertEqual(self.client.post("/api/v1/auth/login", json=credentials).status_code, 401)
        set_access(self.session, email, True)
        self.assertEqual(self.client.get("/api/v1/auth/me", headers=headers).status_code, 401)
        self.assertNotEqual(self.login(email), headers)

    def test_conversation_history_is_private_and_persists_across_sessions(self) -> None:
        owner_email = "owner@example.com"
        other_email = "other@example.org"
        add_user(self.session, owner_email, self.password)
        add_user(self.session, other_email, self.password)
        owner = self.login(owner_email)
        other = self.login(other_email)

        response = self.client.post("/api/v1/conversations", headers=owner)
        self.assertEqual(response.status_code, 201)
        path = f"/api/v1/conversations/{response.json()['id']}"
        question = {"question": "Мой вопрос"}
        response = self.client.post(f"{path}/messages", json=question, headers=owner)
        self.assertEqual(response.status_code, 202)
        message = response.json()

        self.assertEqual(self.client.get("/api/v1/conversations", headers=other).json(), [])
        self.assertEqual(self.client.get(path, headers=other).status_code, 404)
        self.assertEqual(self.client.post(f"{path}/messages", json=question, headers=other).status_code, 404)
        message_path = f"/api/v1/messages/{message['id']}"
        self.assertEqual(self.client.patch(message_path, json={"is_saved": True}, headers=other).status_code, 404)

        self.assertEqual(self.client.post("/api/v1/auth/logout", headers=owner).status_code, 204)
        self.assertEqual(self.client.get(path, headers=owner).status_code, 401)
        new_session = self.login(owner_email)
        self.assertEqual(self.client.get(path, headers=new_session).json()["messages"], [message])

    def test_expired_sessions_and_validation_errors(self) -> None:
        email = "owner@example.com"
        user_id = add_user(self.session, email, self.password)
        headers = self.login(email)
        auth_session = self.session.scalars(select(AuthSession).where(AuthSession.user_id == user_id)).one()
        auth_session.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        self.session.flush()
        self.assertEqual(self.client.get("/api/v1/auth/me", headers=headers).status_code, 401)

        for request in (
            {"json": {"password": self.password}},
            {"content": f'{{"password": "{self.password}",', "headers": {"Content-Type": "application/json"}},
        ):
            response = self.client.post("/api/v1/auth/login", **request)
            self.assertEqual(response.status_code, 422)
            self.assertNotIn(self.password, response.text)
