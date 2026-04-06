from __future__ import annotations

import numpy as np
from PySide6.QtCore import QObject, Signal, Slot

from app.core.logger import get_logger
from app.stt.base import SpeechToTextBackend, TranscriptionResult


class STTService(QObject):
    transcription_started = Signal()
    transcription_completed = Signal(object)
    error_occurred = Signal(str)

    def __init__(
        self,
        backend: SpeechToTextBackend,
        sample_rate: int,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._backend = backend
        self._sample_rate = sample_rate
        self._logger = get_logger("lili.stt.service")

    @Slot(object)
    def transcribe_capture(self, capture_result: object) -> None:
        self.transcription_started.emit()

        try:
            audio = np.asarray(getattr(capture_result, "audio"), dtype=np.float32).reshape(-1)
            if audio.size == 0:
                raise ValueError("Nao ha audio valido para transcrever.")

            result = self._backend.transcribe(audio, self._sample_rate)
        except Exception as exc:  # pragma: no cover - defensive path
            message = f"Falha na transcricao do audio: {exc}"
            self._logger.exception(message)
            self.error_occurred.emit(message)
            return

        self._logger.info(
            "Transcricao concluida: texto=%s duracao=%.2fs",
            result.text,
            result.duration_seconds,
        )
        self.transcription_completed.emit(result)
