from __future__ import annotations

from dataclasses import dataclass

import requests

from app.ai.base import ChatBackend, ChatResponse
from app.ai.mock_chat import MockChatBackend
from app.ai.ollama_client import OllamaChatBackend, OllamaClientConfig


@dataclass(frozen=True)
class ProviderSpec:
    key: str
    label: str
    requires_token: bool
    default_base_url: str | None
    supports_model_listing: bool = True


PROVIDERS: dict[str, ProviderSpec] = {
    "mock": ProviderSpec("mock", "Mock", False, None, False),
    "openai": ProviderSpec("openai", "OpenAI", True, "https://api.openai.com"),
    "gemini": ProviderSpec("gemini", "Gemini", True, "https://generativelanguage.googleapis.com"),
    "ollama_local": ProviderSpec("ollama_local", "Ollama Local", False, "http://localhost:11434"),
    "ollama_cloud": ProviderSpec("ollama_cloud", "Ollama Cloud", True, "https://ollama.com"),
}

PROVIDER_ORDER = [
    "ollama_local",
    "ollama_cloud",
    "openai",
    "gemini",
    "mock",
]


@dataclass(frozen=True)
class ChatProviderConfig:
    provider: str
    model: str | None
    api_key: str | None = None
    base_url: str | None = None
    timeout_seconds: float = 60.0


class OpenAIChatBackend(ChatBackend):
    def __init__(self, api_key: str, base_url: str, model: str, timeout_seconds: float) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout_seconds = timeout_seconds

    def ask(self, prompt: str) -> ChatResponse:
        endpoint = f"{self._base_url}/v1/chat/completions"
        payload = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
        }
        response = requests.post(
            endpoint,
            json=payload,
            headers={"Authorization": f"Bearer {self._api_key}"},
            timeout=self._timeout_seconds,
        )
        _raise_for_status(response)
        data = _parse_json(response, "OpenAI")
        text = _extract_openai_style_content(data)
        return ChatResponse(text=text, provider_name=f"openai:{self._model}")


class GeminiChatBackend(ChatBackend):
    def __init__(self, api_key: str, base_url: str, model: str, timeout_seconds: float) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout_seconds = timeout_seconds

    def ask(self, prompt: str) -> ChatResponse:
        endpoint = f"{self._base_url}/v1beta/models/{self._model}:generateContent"
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        }
        response = requests.post(
            endpoint,
            json=payload,
            headers={"x-goog-api-key": self._api_key},
            timeout=self._timeout_seconds,
        )
        _raise_for_status(response)
        data = _parse_json(response, "Gemini")
        text = _extract_gemini_content(data)
        return ChatResponse(text=text, provider_name=f"gemini:{self._model}")


def get_provider_spec(provider: str) -> ProviderSpec:
    if provider not in PROVIDERS:
        raise ValueError(f"Provider de chat desconhecido: {provider}")
    return PROVIDERS[provider]


def create_backend(config: ChatProviderConfig) -> ChatBackend:
    spec = get_provider_spec(config.provider)
    if config.provider == "mock":
        return MockChatBackend()

    base_url = config.base_url or spec.default_base_url
    if not base_url:
        raise ValueError(f"Base URL nao configurada para {spec.label}.")
    model = (config.model or "").strip()
    if not model:
        raise ValueError(f"Selecione um modelo valido para {spec.label}.")

    if config.provider in {"openai", "gemini", "ollama_cloud"}:
        _require_token(config, spec)

    if config.provider == "openai":
        return OpenAIChatBackend(config.api_key or "", base_url, model, config.timeout_seconds)
    if config.provider == "gemini":
        return GeminiChatBackend(config.api_key or "", base_url, model, config.timeout_seconds)
    if config.provider in {"ollama_local", "ollama_cloud"}:
        return OllamaChatBackend(
            OllamaClientConfig(
                base_url=base_url,
                model=model,
                timeout_seconds=config.timeout_seconds,
                api_key=config.api_key if config.provider == "ollama_cloud" else None,
                use_chat_endpoint=config.provider == "ollama_cloud",
            )
        )

    raise ValueError(f"Provider de chat nao suportado: {config.provider}")


def list_models(config: ChatProviderConfig) -> list[str]:
    spec = get_provider_spec(config.provider)
    if not spec.supports_model_listing:
        return []

    base_url = config.base_url or spec.default_base_url
    if not base_url:
        raise ValueError(f"Base URL nao configurada para {spec.label}.")

    if config.provider in {"openai", "gemini", "ollama_cloud"}:
        _require_token(config, spec)

    if config.provider == "openai":
        endpoint = f"{base_url.rstrip('/')}/v1/models"
        response = requests.get(
            endpoint,
            headers={"Authorization": f"Bearer {config.api_key}"},
            timeout=config.timeout_seconds,
        )
        _raise_for_status(response)
        data = _parse_json(response, spec.label)
        models = [str(item.get("id", "")).strip() for item in data.get("data", [])]
        return sorted([model for model in models if model])

    if config.provider == "gemini":
        endpoint = f"{base_url.rstrip('/')}/v1beta/models"
        response = requests.get(
            endpoint,
            headers={"x-goog-api-key": config.api_key or ""},
            timeout=config.timeout_seconds,
        )
        _raise_for_status(response)
        data = _parse_json(response, spec.label)
        models = []
        for item in data.get("models", []):
            name = str(item.get("name", "")).strip()
            if name.startswith("models/"):
                name = name.split("/", 1)[1]
            if name:
                models.append(name)
        return sorted(models)

    if config.provider in {"ollama_local", "ollama_cloud"}:
        endpoint = f"{base_url.rstrip('/')}/api/tags"
        headers = {}
        if config.provider == "ollama_cloud":
            headers["Authorization"] = f"Bearer {config.api_key}"
        response = requests.get(endpoint, headers=headers, timeout=config.timeout_seconds)
        _raise_for_status(response)
        data = _parse_json(response, spec.label)
        models = []
        for item in data.get("models", []):
            name = str(item.get("name") or item.get("model") or "").strip()
            if name:
                models.append(name)
        return sorted(models)

    if config.provider == "mock":
        return ["mock"]

    raise ValueError(f"Provider de chat nao suportado: {config.provider}")


def _require_token(config: ChatProviderConfig, spec: ProviderSpec) -> None:
    if not config.api_key or not config.api_key.strip():
        raise ValueError(f"Informe um token valido para {spec.label}.")


def _raise_for_status(response: requests.Response) -> None:
    if response.status_code >= 400:
        raise RuntimeError(
            f"HTTP {response.status_code}: {response.text.strip()}"
        )


def _parse_json(response: requests.Response, provider_label: str) -> dict:
    try:
        data = response.json()
    except ValueError as exc:
        raise RuntimeError(
            f"{provider_label} retornou uma resposta JSON invalida."
        ) from exc
    if not isinstance(data, dict):
        raise RuntimeError(f"{provider_label} retornou um JSON inesperado.")
    return data


def _extract_openai_style_content(data: dict) -> str:
    choices = data.get("choices", [])
    if not choices:
        raise RuntimeError("Resposta do provider nao possui escolhas.")
    first = choices[0] if isinstance(choices[0], dict) else {}
    message = first.get("message") if isinstance(first, dict) else {}
    content = ""
    if isinstance(message, dict):
        content = str(message.get("content", "")).strip()
    if not content:
        content = str(first.get("text", "")).strip()
    if not content:
        raise RuntimeError("Resposta do provider nao possui texto.")
    return content


def _extract_gemini_content(data: dict) -> str:
    candidates = data.get("candidates", [])
    if not candidates:
        raise RuntimeError("Gemini retornou uma resposta vazia.")
    first = candidates[0] if isinstance(candidates[0], dict) else {}
    content = first.get("content", {}) if isinstance(first, dict) else {}
    if isinstance(content, dict):
        parts = content.get("parts", [])
        for part in parts:
            if isinstance(part, dict) and "text" in part:
                text = str(part.get("text", "")).strip()
                if text:
                    return text
    text = str(first.get("output_text", "")).strip()
    if not text:
        raise RuntimeError("Gemini retornou uma resposta sem texto.")
    return text
