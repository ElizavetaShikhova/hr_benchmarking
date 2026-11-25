from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, JsonValue, SecretStr, field_validator

from backend.config import MAX_PASSWORD_LENGTH, MIN_PASSWORD_LENGTH, TURNOVER_PERIOD_MESSAGE

class Credentials(BaseModel):
    email: EmailStr
    password: SecretStr = Field(min_length=MIN_PASSWORD_LENGTH, max_length=MAX_PASSWORD_LENGTH)


class UserProfile(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    created_at: datetime


class AccessToken(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int


class MessageCreate(BaseModel):
    question: str = Field(min_length=1, pattern=r"\S")


class MessageUpdate(BaseModel):
    is_saved: bool


class Conversation(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    created_at: datetime
    updated_at: datetime


class Message(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    conversation_id: int
    role: Literal["user", "assistant"]
    content: str
    analysis_plan: Optional[dict[str, JsonValue]] = None
    result_data: Optional[dict[str, JsonValue]] = None
    is_saved: bool = False
    created_at: datetime


class ConversationDetail(Conversation):
    messages: list[Message]


class ReferenceItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class Metric(BaseModel):
    code: str
    name: str
    unit: str


class TurnoverQuery(BaseModel):
    enterprise_id: int = Field(gt=0)
    period: date
    department_id: Optional[int] = Field(default=None, gt=0)

    @field_validator("period")
    @classmethod
    def validate_period(cls, value: date) -> date:
        if value.day != 1:
            raise ValueError(TURNOVER_PERIOD_MESSAGE)
        return value


class ErrorResponse(BaseModel):
    detail: str
