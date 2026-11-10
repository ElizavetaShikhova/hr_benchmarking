from typing import Annotated, Literal, NoReturn

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from backend import config
from backend.api.schemas import (
    Conversation,
    ConversationDetail,
    ErrorResponse,
    Message,
    MessageCreate,
    MessageUpdate,
    Metric,
    ReferenceItem,
    TableInfo,
    TableRows,
)
from backend.database import get_session
from backend.models import Conversation as ConversationModel
from backend.repositories.conversation_repository import ConversationRepository
from backend.repositories.hr_repository import HRRepository

router = APIRouter(prefix=config.API_PREFIX, responses={404: {"model": ErrorResponse}, 501: {"model": ErrorResponse}})
SessionDep = Annotated[Session, Depends(get_session)]


def not_implemented() -> NoReturn:
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=config.NOT_IMPLEMENTED_MESSAGE)


def require_conversation(repository: ConversationRepository, conversation_id: int) -> ConversationModel:
    conversation = repository.get(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=config.CONVERSATION_NOT_FOUND_MESSAGE)
    return conversation


@router.post("/conversations", status_code=status.HTTP_201_CREATED)
def create_conversation(session: SessionDep) -> Conversation:
    conversation = ConversationRepository(session).create()
    session.commit()
    return Conversation.model_validate(conversation)


@router.get("/conversations")
def list_conversations(session: SessionDep) -> list[Conversation]:
    return [Conversation.model_validate(item) for item in ConversationRepository(session).list()]


@router.get("/conversations/{conversation_id}")
def get_conversation(conversation_id: int, session: SessionDep) -> ConversationDetail:
    repository = ConversationRepository(session)
    conversation = require_conversation(repository, conversation_id)
    return ConversationDetail(
        **Conversation.model_validate(conversation).model_dump(),
        messages=[Message.model_validate(item) for item in repository.get_messages(conversation_id)],
    )


@router.post("/conversations/{conversation_id}/messages", status_code=status.HTTP_202_ACCEPTED)
def send_message(conversation_id: int, body: MessageCreate, session: SessionDep) -> Message:
    repository = ConversationRepository(session)
    conversation = require_conversation(repository, conversation_id)
    message = repository.insert_message(conversation, body.question)
    session.commit()
    return Message.model_validate(message)


@router.patch("/messages/{message_id}")
def update_message(message_id: int, body: MessageUpdate, session: SessionDep) -> Message:
    repository = ConversationRepository(session)
    message = repository.get_message(message_id)
    if message is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=config.MESSAGE_NOT_FOUND_MESSAGE)
    repository.set_saved(message, body.is_saved)
    session.commit()
    return Message.model_validate(message)


@router.get("/enterprises")
def list_enterprises(session: SessionDep) -> list[ReferenceItem]:
    return [ReferenceItem.model_validate(item) for item in HRRepository(session).get_enterprises()]


@router.get("/enterprises/{enterprise_id}/departments")
def list_departments(enterprise_id: int, session: SessionDep) -> list[ReferenceItem]:
    repository = HRRepository(session)
    if repository.get_enterprise(enterprise_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=config.ENTERPRISE_NOT_FOUND_MESSAGE)
    return [ReferenceItem.model_validate(item) for item in repository.get_departments(enterprise_id)]


@router.get("/metrics")
def list_metrics() -> list[Metric]:
    return [Metric.model_validate(item) for item in config.METRICS]


@router.get("/data/tables")
def list_tables() -> list[TableInfo]:
    not_implemented()


@router.get("/data/tables/{table_name}/rows")
def get_table_rows(
    table_name: str, page: int = Query(1, ge=1), page_size: int = Query(config.DEFAULT_PAGE_SIZE, ge=1)
) -> TableRows:
    not_implemented()


@router.get(
    "/data/tables/{table_name}/export",
    response_class=Response,
    responses={200: {"content": {
        config.CSV_MEDIA_TYPE: {"schema": {"type": "string", "format": "binary"}},
        config.XLSX_MEDIA_TYPE: {"schema": {"type": "string", "format": "binary"}},
    }}},
)
def export_table(table_name: str, format: Literal["csv", "xlsx"] = "csv") -> Response:
    not_implemented()
