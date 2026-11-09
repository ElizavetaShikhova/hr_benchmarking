from typing import Literal, NoReturn

from fastapi import APIRouter, HTTPException, Query, status

from backend import config
from backend.api.schemas import MessageCreate, MessageUpdate

router = APIRouter(prefix=config.API_PREFIX)


def not_implemented() -> NoReturn:
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=config.NOT_IMPLEMENTED_MESSAGE)


@router.post("/conversations")
def create_conversation() -> None:
    not_implemented()


@router.get("/conversations")
def list_conversations() -> None:
    not_implemented()


@router.get("/conversations/{conversation_id}")
def get_conversation(conversation_id: int) -> None:
    not_implemented()


@router.post("/conversations/{conversation_id}/messages")
def send_message(conversation_id: int, body: MessageCreate) -> None:
    not_implemented()


@router.patch("/messages/{message_id}")
def update_message(message_id: int, body: MessageUpdate) -> None:
    not_implemented()


@router.get("/enterprises")
def list_enterprises() -> None:
    not_implemented()


@router.get("/enterprises/{enterprise_id}/departments")
def list_departments(enterprise_id: int) -> None:
    not_implemented()


@router.get("/metrics")
def list_metrics() -> None:
    not_implemented()


@router.get("/data/tables")
def list_tables() -> None:
    not_implemented()


@router.get("/data/tables/{table_name}/rows")
def get_table_rows(
    table_name: str, page: int = Query(1, ge=1), page_size: int = Query(config.DEFAULT_PAGE_SIZE, ge=1)
) -> None:
    not_implemented()


@router.get("/data/tables/{table_name}/export")
def export_table(table_name: str, format: Literal["csv", "xlsx"] = "csv") -> None:
    not_implemented()
