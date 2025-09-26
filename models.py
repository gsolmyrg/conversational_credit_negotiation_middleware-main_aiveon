from typing import Literal

from pydantic import BaseModel


class Persona(BaseModel):
    name: str
    cellphone: str
    gender: str
    age: int
    debt: int
    yearly_revenue: int


class Option(BaseModel):
    clear_history: bool


class DebtNegotiationRequestBody(BaseModel):
    persona: Persona
    options: Option


class WhatsappRequestBody(BaseModel):
    class Config:
        extra = "allow"


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class Conversation(BaseModel):
    id: str
    messages: list[Message]
