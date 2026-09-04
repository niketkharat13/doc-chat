from typing import Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: Optional[str] = Field(None, description="The user's message to the chatbot")


class ChatResponse(BaseModel):
    reply: str = Field(..., description="The chatbot's reply")
