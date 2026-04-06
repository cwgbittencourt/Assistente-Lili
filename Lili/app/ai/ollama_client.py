from __future__ import annotations

from dataclasses import dataclass

import requests

from app.ai.base import ChatBackend, ChatResponse


@dataclass(frozen=True)
class OllamaClientConfig:
    base_url: str
    model: str
    timeout_seconds: float
    api_key: str | None = None
    use_chat_endpoint: bool = False


class OllamaChatBackend(ChatBackend):
    def __init__(self, config: OllamaClientConfig) -> None:
        self._config = config

    def ask(self, prompt: str) -> ChatResponse:
        if self._config.use_chat_endpoint:
            endpoint = f"{self._config.base_url.rstrip('/')}/api/chat"
            payload = {
                "model": self._config.model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
            }
        else:
            endpoint = f"{self._config.base_url.rstrip('/')}/api/generate"
            payload = {
                "model": self._config.model,
                "prompt": prompt,
                "stream": False,
            }
        headers = {}
        if self._config.api_key:
            headers["Authorization"] = f"Bearer {self._config.api_key}"

        last_exception: requests.RequestException | None = None
        for _attempt in range(2):
            try:
                response = requests.post(
                    endpoint,
                    json=payload,
                    headers=headers,
                    timeout=self._config.timeout_seconds,
                )
                break
            except requests.RequestException as exc:
                last_exception = exc
        else:
            raise RuntimeError(
                f"Falha ao conectar no Ollama em {self._config.base_url}: {last_exception}"
            ) from last_exception

        if response.status_code >= 400:
            raise RuntimeError(
                f"Ollama retornou HTTP {response.status_code}: {response.text.strip()}"
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise RuntimeError("Ollama retornou uma resposta JSON invalida.") from exc

        text = ""
        if self._config.use_chat_endpoint:
            message = data.get("message", {}) if isinstance(data, dict) else {}
            if isinstance(message, dict):
                text = str(message.get("content", "")).strip()
        else:
            text = str(data.get("response", "")).strip()
        if not text:
            raise RuntimeError("Ollama retornou uma resposta vazia.")

        return ChatResponse(text=text, provider_name=f"ollama:{self._config.model}")
