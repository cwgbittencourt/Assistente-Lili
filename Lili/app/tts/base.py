from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class SpeechSynthesisResult:
    text: str


@dataclass(frozen=True)
class TextToSpeechVoice:
    id: str
    name: str
    languages: tuple[str, ...] = ()


class TextToSpeechBackend(Protocol):
    def speak(self, text: str) -> SpeechSynthesisResult:
        ...

    def stop(self) -> None:
        ...

    def list_voices(self) -> list[TextToSpeechVoice]:
        ...

    def get_selected_voice_id(self) -> str | None:
        ...

    def set_voice(self, voice_id: str | None) -> None:
        ...
