from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np


@dataclass(frozen=True)
class TranscriptionResult:
    text: str
    duration_seconds: float
    confidence: float | None = None


class SpeechToTextBackend(Protocol):
    def transcribe(self, audio: np.ndarray, sample_rate: int) -> TranscriptionResult:
        ...
