from __future__ import annotations

from enum import Enum

from PySide6.QtCore import QObject, Signal

from app.core.logger import get_logger


class AppState(str, Enum):
    INICIALIZANDO = "INICIALIZANDO"
    AGUARDANDO_WAKE_WORD = "AGUARDANDO_WAKE_WORD"
    WAKE_WORD_DETECTADA = "WAKE_WORD_DETECTADA"
    CAPTURANDO_COMANDO = "CAPTURANDO_COMANDO"
    TRANSCREVENDO = "TRANSCREVENDO"
    ENVIANDO_PARA_IA = "ENVIANDO_PARA_IA"
    REPRODUZINDO_RESPOSTA = "REPRODUZINDO_RESPOSTA"
    ERRO = "ERRO"


class AppStateMachine(QObject):
    state_changed = Signal(object, object)

    _VALID_TRANSITIONS: dict[AppState, set[AppState]] = {
        AppState.INICIALIZANDO: {
            AppState.AGUARDANDO_WAKE_WORD,
            AppState.ERRO,
        },
        AppState.AGUARDANDO_WAKE_WORD: {
            AppState.WAKE_WORD_DETECTADA,
            AppState.ERRO,
        },
        AppState.WAKE_WORD_DETECTADA: {
            AppState.CAPTURANDO_COMANDO,
            AppState.AGUARDANDO_WAKE_WORD,
            AppState.ERRO,
        },
        AppState.CAPTURANDO_COMANDO: {
            AppState.TRANSCREVENDO,
            AppState.AGUARDANDO_WAKE_WORD,
            AppState.ERRO,
        },
        AppState.TRANSCREVENDO: {
            AppState.ENVIANDO_PARA_IA,
            AppState.AGUARDANDO_WAKE_WORD,
            AppState.ERRO,
        },
        AppState.ENVIANDO_PARA_IA: {
            AppState.REPRODUZINDO_RESPOSTA,
            AppState.AGUARDANDO_WAKE_WORD,
            AppState.ERRO,
        },
        AppState.REPRODUZINDO_RESPOSTA: {
            AppState.AGUARDANDO_WAKE_WORD,
            AppState.ERRO,
        },
        AppState.ERRO: {
            AppState.INICIALIZANDO,
            AppState.AGUARDANDO_WAKE_WORD,
        },
    }

    def __init__(self, initial_state: AppState = AppState.INICIALIZANDO, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._logger = get_logger("lili.core.state_machine")
        self._state = initial_state

    @property
    def current_state(self) -> AppState:
        return self._state

    def can_transition_to(self, new_state: AppState) -> bool:
        if new_state == self._state:
            return True

        return new_state in self._VALID_TRANSITIONS.get(self._state, set())

    def transition_to(self, new_state: AppState) -> bool:
        if not self.can_transition_to(new_state):
            self._logger.warning("Transicao invalida: %s -> %s", self._state.value, new_state.value)
            return False

        if new_state == self._state:
            return True

        previous_state = self._state
        self._state = new_state
        self._logger.info("Transicao de estado: %s -> %s", previous_state.value, new_state.value)
        self.state_changed.emit(previous_state, new_state)
        return True
