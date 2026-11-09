from pydantic import BaseModel, Field


class MessageCreate(BaseModel):
    question: str = Field(min_length=1)


class MessageUpdate(BaseModel):
    is_saved: bool
