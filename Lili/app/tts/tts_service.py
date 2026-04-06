from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Slot

from app.core.logger import get_logger
from app.tts.base import SpeechSynthesisResult, TextToSpeechBackend, TextToSpeechVoice


class TTSService(QObject):
    speech_started = Signal(str)
    speech_finished = Signal(object)
    error_occurred = Signal(str)

    def __init__(self, backend: TextToSpeechBackend, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._backend = backend
        self._logger = get_logger("lili.tts.service")

    @Slot(str)
    def speak(self, text: str) -> None:
        self.speech_started.emit(text)

        try:
            result = self._backend.speak(text)
        except Exception as exc:  # pragma: no cover - defensive path
            message = f"Falha ao reproduzir fala: {exc}"
            self._logger.exception(message)
            self.error_occurred.emit(message)
            return

        self._logger.info("Reproducao TTS concluida")
        self.speech_finished.emit(result)

    def stop(self) -> None:
        self._backend.stop()

    def list_voices(self) -> list[TextToSpeechVoice]:
        return self._backend.list_voices()

    def get_selected_voice_id(self) -> str | None:
        return self._backend.get_selected_voice_id()

    @Slot(object)
    def set_voice(self, voice_id: object) -> None:
        try:
            normalized_voice_id = None if voice_id in (None, "") else str(voice_id)
            self._backend.set_voice(normalized_voice_id)
        except Exception as exc:  # pragma: no cover - defensive path
            message = f"Falha ao alterar a voz do TTS: {exc}"
            self._logger.exception(message)
            self.error_occurred.emit(message)
