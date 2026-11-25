from collections.abc import Sequence
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.models import Conversation, Message


class ConversationRepository:
    def __init__(self, session: Session, user_id: int) -> None:
        self.session = session
        self.user_id = user_id

    def create(self) -> Conversation:
        conversation = Conversation(user_id=self.user_id)
        self.session.add(conversation)
        self.session.flush()
        return conversation

    def list(self) -> Sequence[Conversation]:
        return self.session.scalars(
            select(Conversation).where(Conversation.user_id == self.user_id)
            .order_by(Conversation.updated_at.desc(), Conversation.id.desc())
        ).all()

    def get(self, conversation_id: int) -> Optional[Conversation]:
        return self.session.scalar(select(Conversation).where(
            Conversation.id == conversation_id, Conversation.user_id == self.user_id,
        ))

    def insert_message(self, conversation: Conversation, content: str) -> Message:
        message = Message(conversation_id=conversation.id, role="user", content=content)
        self.session.add(message)
        conversation.updated_at = func.now()
        self.session.flush()
        return message

    def get_message(self, message_id: int) -> Optional[Message]:
        return self.session.scalar(select(Message).join(Conversation).where(
            Message.id == message_id, Conversation.user_id == self.user_id,
        ))
