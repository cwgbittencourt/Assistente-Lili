from __future__ import annotations

from app.ai.base import ChatBackend, ChatResponse


class MockChatBackend(ChatBackend):
    def __init__(self, response_prefix: str = "Resposta mock para:") -> None:
        self._response_prefix = response_prefix

    def ask(self, prompt: str) -> ChatResponse:
        normalized = prompt.strip() or "comando vazio"
        return ChatResponse(
            text=f"{self._response_prefix} {normalized}",
            provider_name="mock_chat",
        )
