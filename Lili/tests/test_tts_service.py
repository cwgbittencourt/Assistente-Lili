from __future__ import annotations

from app.tts import SpeechSynthesisResult, TTSService, TextToSpeechVoice


class _FakeVoiceBackend:
    def __init__(self) -> None:
        self.selected_voice_id: str | None = None
        self.voices = [
            TextToSpeechVoice(id="v1", name="Voz 1", languages=("pt-BR",)),
            TextToSpeechVoice(id="v2", name="Voz 2", languages=("en-US",)),
        ]

    def speak(self, text: str) -> SpeechSynthesisResult:
        return SpeechSynthesisResult(text=text)

    def stop(self) -> None:
        return

    def list_voices(self) -> list[TextToSpeechVoice]:
        return self.voices

    def get_selected_voice_id(self) -> str | None:
        return self.selected_voice_id

    def set_voice(self, voice_id: str | None) -> None:
        self.selected_voice_id = voice_id


def test_tts_service_exposes_available_voices() -> None:
    service = TTSService(_FakeVoiceBackend())

    voices = service.list_voices()

    assert [voice.id for voice in voices] == ["v1", "v2"]


def test_tts_service_updates_selected_voice() -> None:
    backend = _FakeVoiceBackend()
    service = TTSService(backend)

    service.set_voice("v2")

    assert service.get_selected_voice_id() == "v2"
    assert backend.selected_voice_id == "v2"
