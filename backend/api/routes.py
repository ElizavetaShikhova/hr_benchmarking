from calendar import monthrange
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend import config
from backend.api.auth import CurrentSession, SessionDep, auth_router, get_current_session
from backend.api.schemas import (
    Conversation,
    ConversationDetail,
    ErrorResponse,
    Message,
    MessageCreate,
    MessageUpdate,
    Metric,
    ReferenceItem,
    TurnoverQuery,
)
from backend.models import Conversation as ConversationModel
from backend.repositories.conversation_repository import ConversationRepository
from backend.repositories.hr_repository import HRRepository
from backend.services.analytics_service import TurnoverComparison, calculate_turnover

router = APIRouter(prefix=config.API_PREFIX)
protected_router = APIRouter(
    dependencies=[Depends(get_current_session)],
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)


def require_conversation(repository: ConversationRepository, conversation_id: int) -> ConversationModel:
    conversation = repository.get(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=config.CONVERSATION_NOT_FOUND_MESSAGE)
    return conversation


def require_enterprise(repository: HRRepository, enterprise_id: int) -> None:
    if not repository.enterprise_exists(enterprise_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=config.ENTERPRISE_NOT_FOUND_MESSAGE)


@protected_router.post("/conversations", status_code=status.HTTP_201_CREATED)
def create_conversation(session: SessionDep, current_session: CurrentSession) -> Conversation:
    conversation = ConversationRepository(session, current_session.user_id).create()
    response = Conversation.model_validate(conversation)
    session.commit()
    return response


@protected_router.get("/conversations")
def list_conversations(session: SessionDep, current_session: CurrentSession) -> list[Conversation]:
    repository = ConversationRepository(session, current_session.user_id)
    return [Conversation.model_validate(item) for item in repository.list()]


@protected_router.get("/conversations/{conversation_id}")
def get_conversation(conversation_id: int, session: SessionDep, current_session: CurrentSession) -> ConversationDetail:
    repository = ConversationRepository(session, current_session.user_id)
    return ConversationDetail.model_validate(require_conversation(repository, conversation_id))


@protected_router.post("/conversations/{conversation_id}/messages", status_code=status.HTTP_202_ACCEPTED)
def send_message(conversation_id: int, body: MessageCreate, session: SessionDep, current_session: CurrentSession) -> Message:
    repository = ConversationRepository(session, current_session.user_id)
    conversation = require_conversation(repository, conversation_id)
    message = repository.insert_message(conversation, body.question)
    response = Message.model_validate(message)
    session.commit()
    return response


@protected_router.patch("/messages/{message_id}")
def update_message(message_id: int, body: MessageUpdate, session: SessionDep, current_session: CurrentSession) -> Message:
    repository = ConversationRepository(session, current_session.user_id)
    message = repository.get_message(message_id)
    if message is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=config.MESSAGE_NOT_FOUND_MESSAGE)
    message.is_saved = body.is_saved
    response = Message.model_validate(message)
    session.commit()
    return response


@protected_router.get("/enterprises")
def list_enterprises(session: SessionDep) -> list[ReferenceItem]:
    return [ReferenceItem.model_validate(item) for item in HRRepository(session).get_enterprises()]


@protected_router.get("/enterprises/{enterprise_id}/departments")
def list_departments(enterprise_id: int, session: SessionDep) -> list[ReferenceItem]:
    repository = HRRepository(session)
    require_enterprise(repository, enterprise_id)
    return [ReferenceItem.model_validate(item) for item in repository.get_departments(enterprise_id)]


@protected_router.get("/metrics")
def list_metrics() -> list[Metric]:
    return [Metric.model_validate(item) for item in config.METRICS]


@protected_router.get("/metrics/turnover")
def get_turnover(query: Annotated[TurnoverQuery, Query()], session: SessionDep) -> TurnoverComparison:
    repository = HRRepository(session)
    require_enterprise(repository, query.enterprise_id)
    if query.department_id is not None and not repository.department_exists(query.enterprise_id, query.department_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=config.DEPARTMENT_NOT_FOUND_MESSAGE)
    period_days = monthrange(query.period.year, query.period.month)[1]
    period_end = query.period.replace(day=period_days)
    employee_days, dismissals, plan = repository.get_turnover_data(
        query.enterprise_id, query.department_id, query.period, period_end
    )
    return calculate_turnover(employee_days, period_days, dismissals, plan)


router.include_router(auth_router)
router.include_router(protected_router)
