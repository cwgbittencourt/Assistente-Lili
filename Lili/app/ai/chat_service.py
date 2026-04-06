from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Slot

from app.ai.base import ChatBackend, ChatResponse
from app.ai.providers import ChatProviderConfig, create_backend, list_models
from app.core.logger import get_logger


class ChatService(QObject):
    request_started = Signal(str)
    response_completed = Signal(object)
    error_occurred = Signal(str)
    models_listed = Signal(str, list)
    models_list_error = Signal(str, str)

    def __init__(self, backend: ChatBackend, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._backend = backend
        self._logger = get_logger("lili.ai.chat_service")

    @Slot(str)
    def ask(self, prompt: str) -> None:
        self.request_started.emit(prompt)

        try:
            response = self._backend.ask(prompt)
        except Exception as exc:  # pragma: no cover - defensive path
            message = f"Falha ao enviar pergunta para o chat: {exc}"
            self._logger.exception(message)
            self.error_occurred.emit(message)
            return

        self._logger.info("Resposta mock recebida do provider %s", response.provider_name)
        self.response_completed.emit(response)

    @Slot(object)
    def configure_provider(self, config: ChatProviderConfig) -> None:
        try:
            self._backend = create_backend(config)
        except Exception as exc:
            message = f"Falha ao configurar provider de chat: {exc}"
            self._logger.exception(message)
            self.error_occurred.emit(message)
            return
        self._logger.info("Provider de chat atualizado para %s", config.provider)

    @Slot(object)
    def list_available_models(self, config: ChatProviderConfig) -> None:
        try:
            models = list_models(config)
        except Exception as exc:
            message = f"Falha ao listar modelos de {config.provider}: {exc}"
            self._logger.warning(message)
            self.models_list_error.emit(config.provider, message)
            return
        self.models_listed.emit(config.provider, models)
