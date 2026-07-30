from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str
    content: str | list[dict[str, Any]] | None = ""


class ChatCompletionRequest(BaseModel):
    model: str = "hermes-codex"
    messages: list[ChatMessage]
    temperature: float | None = None
    stream: bool = False
    max_tokens: int | None = None


class ModelCard(BaseModel):
    id: str
    object: str = "model"
    created: int = 0
    owned_by: str = "hermes"


class ModelsResponse(BaseModel):
    object: str = "list"
    data: list[ModelCard] = Field(default_factory=lambda: [ModelCard(id="hermes-codex")])
