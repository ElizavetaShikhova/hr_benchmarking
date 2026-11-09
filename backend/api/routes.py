from typing import Literal, NoReturn

from fastapi import APIRouter, HTTPException, Query, Response, status

from backend import config
from backend.api.schemas import (
    AnalysisResult,
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

router = APIRouter(prefix=config.API_PREFIX, responses={404: {"model": ErrorResponse}, 501: {"model": ErrorResponse}})


def not_implemented() -> NoReturn:
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=config.NOT_IMPLEMENTED_MESSAGE)


@router.post("/conversations", status_code=status.HTTP_201_CREATED)
def create_conversation() -> Conversation:
    not_implemented()


@router.get("/conversations")
def list_conversations() -> list[Conversation]:
    not_implemented()


@router.get("/conversations/{conversation_id}")
def get_conversation(conversation_id: int) -> ConversationDetail:
    not_implemented()


@router.post("/conversations/{conversation_id}/messages")
def send_message(conversation_id: int, body: MessageCreate) -> AnalysisResult:
    not_implemented()


@router.patch("/messages/{message_id}")
def update_message(message_id: int, body: MessageUpdate) -> Message:
    not_implemented()


@router.get("/enterprises")
def list_enterprises() -> list[ReferenceItem]:
    not_implemented()


@router.get("/enterprises/{enterprise_id}/departments")
def list_departments(enterprise_id: int) -> list[ReferenceItem]:
    not_implemented()


@router.get("/metrics")
def list_metrics() -> list[Metric]:
    not_implemented()


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
