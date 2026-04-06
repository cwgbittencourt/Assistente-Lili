import numpy as np

from app.ai import MockChatBackend
from app.stt import MockSpeechToTextBackend


def test_mock_stt_returns_configured_text_and_duration() -> None:
    backend = MockSpeechToTextBackend(fixed_text="abrir navegador")
    result = backend.transcribe(np.ones(3200, dtype=np.float32), 16000)

    assert result.text == "abrir navegador"
    assert result.duration_seconds == 0.2
    assert result.confidence == 1.0


def test_mock_chat_uses_custom_prefix() -> None:
    backend = MockChatBackend(response_prefix="Mock custom:")
    result = backend.ask("acender a luz")

    assert result.text == "Mock custom: acender a luz"
    assert result.provider_name == "mock_chat"
