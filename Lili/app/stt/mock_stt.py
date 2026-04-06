from __future__ import annotations

import numpy as np

from app.stt.base import SpeechToTextBackend, TranscriptionResult


class MockSpeechToTextBackend(SpeechToTextBackend):
    def __init__(self, fixed_text: str = "ligar a luz da sala") -> None:
        self._fixed_text = fixed_text

    def transcribe(self, audio: np.ndarray, sample_rate: int) -> TranscriptionResult:
        samples = np.asarray(audio, dtype=np.float32).reshape(-1)
        duration_seconds = (samples.size / sample_rate) if sample_rate > 0 else 0.0
        return TranscriptionResult(
            text=self._fixed_text,
            duration_seconds=duration_seconds,
            confidence=1.0,
        )
