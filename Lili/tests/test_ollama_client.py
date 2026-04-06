from __future__ import annotations

import requests

from app.ai.ollama_client import OllamaChatBackend, OllamaClientConfig


class _ResponseStub:
    def __init__(self, status_code: int, payload: dict[str, object], text: str = "") -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self) -> dict[str, object]:
        return self._payload


def test_ollama_retries_once_before_succeeding(monkeypatch) -> None:
    attempts = {"count": 0}

    def fake_post(*args, **kwargs):
        del args, kwargs
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise requests.ConnectTimeout("timeout")
        return _ResponseStub(200, {"response": "ok"})

    monkeypatch.setattr("app.ai.ollama_client.requests.post", fake_post)
    backend = OllamaChatBackend(
        OllamaClientConfig(
            base_url="http://localhost:11434",
            model="qwen2.5:7b-instruct",
            timeout_seconds=30,
        )
    )

    result = backend.ask("teste")

    assert attempts["count"] == 2
    assert result.text == "ok"
    assert result.provider_name == "ollama:qwen2.5:7b-instruct"


def test_ollama_raises_after_retry_exhausted(monkeypatch) -> None:
    attempts = {"count": 0}

    def fake_post(*args, **kwargs):
        del args, kwargs
        attempts["count"] += 1
        raise requests.ReadTimeout("timeout")

    monkeypatch.setattr("app.ai.ollama_client.requests.post", fake_post)
    backend = OllamaChatBackend(
        OllamaClientConfig(
            base_url="http://localhost:11434",
            model="qwen2.5:7b-instruct",
            timeout_seconds=30,
        )
    )

    try:
        backend.ask("teste")
    except RuntimeError as exc:
        assert "Falha ao conectar no Ollama" in str(exc)
    else:
        raise AssertionError("Esperava RuntimeError apos esgotar retry")

    assert attempts["count"] == 2
