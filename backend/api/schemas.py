from datetime import datetime
from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, Field, JsonValue

CellValue = Union[str, int, float, bool, None]
DataRow = dict[str, CellValue]


class MessageCreate(BaseModel):
    question: str = Field(min_length=1)


class MessageUpdate(BaseModel):
    is_saved: bool


class Column(BaseModel):
    key: str
    label: str


class Table(BaseModel):
    columns: list[Column]
    rows: list[DataRow]


class Chart(BaseModel):
    type: Literal["bar_chart"]
    title: str
    x_key: str
    series: list[Column]
    data: list[DataRow]


class Visualization(BaseModel):
    default_view: Literal["table", "chart"]
    table: Optional[Table] = None
    chart: Optional[Chart] = None


class CompletedAnalysis(BaseModel):
    status: Literal["completed"]
    message_id: int
    summary: str
    visualization: Optional[Visualization] = None


class ClarificationNeeded(BaseModel):
    status: Literal["clarification_needed"]
    question: str


class InsufficientData(BaseModel):
    status: Literal["insufficient_data"]
    message: str


AnalysisResult = Annotated[
    Union[CompletedAnalysis, ClarificationNeeded, InsufficientData], Field(discriminator="status")
]


class Conversation(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime


class Message(BaseModel):
    id: int
    conversation_id: int
    role: Literal["user", "assistant"]
    content: str
    analysis_plan: Optional[dict[str, JsonValue]] = None
    result_data: Optional[AnalysisResult] = None
    is_saved: bool = False
    created_at: datetime


class ConversationDetail(Conversation):
    messages: list[Message]


class ReferenceItem(BaseModel):
    id: int
    name: str


class Metric(BaseModel):
    code: str
    name: str
    unit: str


class TableInfo(BaseModel):
    name: str
    label: str


class TableRows(Table):
    table_name: str
    total: int
    page: int
    page_size: int


class ErrorResponse(BaseModel):
    detail: str
