from collections.abc import Sequence
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.models import Conversation, Message


class ConversationRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self) -> Conversation:
        conversation = Conversation()
        self.session.add(conversation)
        self.session.flush()
        return conversation

    def list(self) -> Sequence[Conversation]:
        return self.session.scalars(
            select(Conversation).order_by(Conversation.updated_at.desc(), Conversation.id.desc())
        ).all()

    def get(self, conversation_id: int) -> Optional[Conversation]:
        return self.session.get(Conversation, conversation_id)

    def get_messages(self, conversation_id: int) -> Sequence[Message]:
        return self.session.scalars(
            select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at, Message.id)
        ).all()

    def insert_message(self, conversation: Conversation, content: str) -> Message:
        message = Message(conversation_id=conversation.id, role="user", content=content)
        self.session.add(message)
        conversation.updated_at = func.now()
        self.session.flush()
        return message

    def get_message(self, message_id: int) -> Optional[Message]:
        return self.session.get(Message, message_id)

    def set_saved(self, message: Message, is_saved: bool) -> Message:
        message.is_saved = is_saved
        self.session.flush()
        return message
