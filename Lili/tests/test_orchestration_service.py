from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from app.core import AppState, AppStateMachine
from app.services.orchestration_service import OrchestrationService


class _FakeWakeWordService(QObject):
    wake_word_detected = Signal(float)
    error_occurred = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.enabled = True

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled


class _FakeCommandCaptureService(QObject):
    capture_started = Signal()
    capture_finished = Signal(object)
    capture_discarded = Signal(str)
    error_occurred = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.start_calls = 0
        self.cancel_reasons: list[str] = []

    def start_capture(self) -> None:
        self.start_calls += 1

    def cancel_capture(self, reason: str = "Captura cancelada") -> None:
        self.cancel_reasons.append(reason)


class _FakeSTTService(QObject):
    transcription_started = Signal()
    transcription_completed = Signal(object)
    error_occurred = Signal(str)

    def transcribe_capture(self, capture_result: object) -> None:
        del capture_result


class _FakeChatService(QObject):
    request_started = Signal(str)
    response_completed = Signal(object)
    error_occurred = Signal(str)

    def ask(self, prompt: str) -> None:
        self.request_started.emit(prompt)


class _FakeTTSService(QObject):
    speech_started = Signal(str)
    speech_finished = Signal(object)
    error_occurred = Signal(str)

    def speak(self, text: str) -> None:
        self.speech_started.emit(text)


def _build_orchestration(initial_state: AppState = AppState.AGUARDANDO_WAKE_WORD):
    state_machine = AppStateMachine(initial_state=initial_state)
    wakeword_service = _FakeWakeWordService()
    command_capture_service = _FakeCommandCaptureService()
    stt_service = _FakeSTTService()
    chat_service = _FakeChatService()
    tts_service = _FakeTTSService()
    orchestration = OrchestrationService(
        state_machine=state_machine,
        wakeword_service=wakeword_service,
        command_capture_service=command_capture_service,
        stt_service=stt_service,
        chat_service=chat_service,
        tts_service=tts_service,
        wakeword_rearm_delay_ms=0,
    )
    return (
        orchestration,
        state_machine,
        wakeword_service,
        command_capture_service,
        stt_service,
        chat_service,
        tts_service,
    )


def test_chat_error_recovers_to_waiting_state() -> None:
    (
        orchestration,
        state_machine,
        wakeword_service,
        _command_capture_service,
        _stt_service,
        chat_service,
        _tts_service,
    ) = _build_orchestration(initial_state=AppState.ENVIANDO_PARA_IA)
    statuses: list[str] = []
    responses: list[str] = []
    orchestration.status_text_changed.connect(statuses.append)
    orchestration.response_text_changed.connect(responses.append)

    wakeword_service.set_enabled(False)
    chat_service.error_occurred.emit("Falha ao enviar pergunta para o chat: timeout")

    assert state_machine.current_state == AppState.AGUARDANDO_WAKE_WORD
    assert wakeword_service.enabled is True
    assert responses[-1] == "Falha ao enviar pergunta para o chat: timeout"
    assert statuses[-1] == "Falha ao enviar pergunta para o chat: timeout Reiniciando escuta."


def test_wakeword_error_recovers_to_waiting_state() -> None:
    (
        orchestration,
        state_machine,
        wakeword_service,
        command_capture_service,
        _stt_service,
        _chat_service,
        _tts_service,
    ) = _build_orchestration()
    statuses: list[str] = []
    orchestration.status_text_changed.connect(statuses.append)

    wakeword_service.set_enabled(True)
    wakeword_service.error_occurred.emit("Falha critica na ativacao")

    assert state_machine.current_state == AppState.AGUARDANDO_WAKE_WORD
    assert wakeword_service.enabled is True
    assert command_capture_service.cancel_reasons[-1] == "Captura cancelada por falha no pipeline"
    assert statuses[-1] == "Falha critica na ativacao Reiniciando escuta."
