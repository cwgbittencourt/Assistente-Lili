from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ChatResponse:
    text: str
    provider_name: str


class ChatBackend(Protocol):
    def ask(self, prompt: str) -> ChatResponse:
        ...
