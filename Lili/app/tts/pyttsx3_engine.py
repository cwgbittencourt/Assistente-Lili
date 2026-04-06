from __future__ import annotations

from typing import Any

from app.tts.base import SpeechSynthesisResult, TextToSpeechBackend, TextToSpeechVoice

try:
    import pyttsx3
except Exception as exc:  # pragma: no cover - depends on local runtime
    pyttsx3 = None
    _pyttsx3_import_error = exc
else:
    _pyttsx3_import_error = None


class Pyttsx3TextToSpeechBackend(TextToSpeechBackend):
    def __init__(self, rate: int = 180, volume: float = 1.0, voice_id: str | None = None) -> None:
        self._rate = rate
        self._volume = max(0.0, min(volume, 1.0))
        self._voice_id = voice_id or None
        self._engine: Any | None = None

    def speak(self, text: str) -> SpeechSynthesisResult:
        engine = self._create_engine()
        self._engine = engine

        try:
            engine.say(text)
            engine.runAndWait()
            return SpeechSynthesisResult(text=text)
        finally:
            try:
                engine.stop()
            finally:
                self._engine = None

    def stop(self) -> None:
        if self._engine is None:
            return

        self._engine.stop()
        self._engine = None

    def list_voices(self) -> list[TextToSpeechVoice]:
        engine = self._create_engine()
        try:
            return [
                TextToSpeechVoice(
                    id=str(getattr(voice, "id", "")),
                    name=str(getattr(voice, "name", getattr(voice, "id", "Voz sem nome"))),
                    languages=tuple(str(language) for language in getattr(voice, "languages", []) or ()),
                )
                for voice in engine.getProperty("voices")
            ]
        finally:
            engine.stop()

    def get_selected_voice_id(self) -> str | None:
        return self._voice_id

    def set_voice(self, voice_id: str | None) -> None:
        self._voice_id = voice_id or None

    def _create_engine(self) -> Any:
        if pyttsx3 is None:
            raise RuntimeError(
                "Falha ao importar pyttsx3. "
                f"Erro original: {_pyttsx3_import_error}"
            )

        engine = pyttsx3.init()
        engine.setProperty("rate", self._rate)
        engine.setProperty("volume", self._volume)
        if self._voice_id:
            engine.setProperty("voice", self._voice_id)
        return engine
