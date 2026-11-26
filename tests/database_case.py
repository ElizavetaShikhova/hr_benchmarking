import unittest
from typing import Optional

from sqlalchemy.orm import Session

from backend.database import engine
from backend.models import Conversation, Message


def create_sample_conversation(session: Session, user_id: Optional[int] = None) -> Conversation:
    conversation = Conversation(title="Сравнение предприятий", user_id=user_id)
    session.add(conversation)
    session.flush()
    question = "Какой показатель и за какой период сравнить?"
    session.add_all([
        Message(conversation_id=conversation.id, role="user", content="Сравни предприятия"),
        Message(conversation_id=conversation.id, role="assistant", content=question,
                result_data={"status": "clarification_needed", "question": question}),
    ])
    session.flush()
    return conversation


class DatabaseTestCase(unittest.TestCase):
    def setUp(self) -> None:
        connection = engine.connect()
        transaction = connection.begin()
        self.session = Session(bind=connection, join_transaction_mode="create_savepoint")
        self.addCleanup(connection.close)
        self.addCleanup(transaction.rollback)
        self.addCleanup(self.session.close)
