from __future__ import annotations

from PySide6.QtCore import QObject, QTimer, Signal

from app.ai import ChatResponse, ChatService
from app.core import AppState, AppStateMachine
from app.core.logger import get_logger
from app.services.command_capture_service import CommandCaptureResult, CommandCaptureService
from app.stt import STTService, TranscriptionResult
from app.tts import SpeechSynthesisResult, TTSService
from app.wakeword import WakeWordSTTService


class OrchestrationService(QObject):
    status_text_changed = Signal(str)
    user_text_changed = Signal(str)
    response_text_changed = Signal(str)

    chat_requested = Signal(str)
    tts_requested = Signal(str)

    def __init__(
        self,
        state_machine: AppStateMachine,
        wakeword_service: WakeWordSTTService,
        command_capture_service: CommandCaptureService,
        stt_service: STTService,
        chat_service: ChatService,
        tts_service: TTSService,
        wakeword_rearm_delay_ms: int,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._logger = get_logger("lili.services.orchestration")
        self._state_machine = state_machine
        self._wakeword_service = wakeword_service
        self._command_capture_service = command_capture_service
        self._stt_service = stt_service
        self._chat_service = chat_service
        self._tts_service = tts_service
        self._wakeword_rearm_delay_ms = wakeword_rearm_delay_ms

        self.chat_requested.connect(self._chat_service.ask)
        self.tts_requested.connect(self._tts_service.speak)
        self._connect_services()

    def _connect_services(self) -> None:
        self._wakeword_service.wake_word_detected.connect(self._handle_wake_word_detected)
        self._wakeword_service.error_occurred.connect(self._handle_wakeword_error)

        self._command_capture_service.capture_started.connect(self._handle_command_capture_started)
        self._command_capture_service.capture_finished.connect(self._handle_command_capture_finished)
        self._command_capture_service.capture_finished.connect(self._stt_service.transcribe_capture)
        self._command_capture_service.capture_discarded.connect(self._handle_command_capture_discarded)
        self._command_capture_service.error_occurred.connect(self._handle_command_capture_error)

        self._stt_service.transcription_started.connect(self._handle_transcription_started)
        self._stt_service.transcription_completed.connect(self._handle_transcription_completed)
        self._stt_service.error_occurred.connect(self._handle_stt_error)

        self._chat_service.request_started.connect(self._handle_chat_started)
        self._chat_service.response_completed.connect(self._handle_chat_completed)
        self._chat_service.error_occurred.connect(self._handle_chat_error)

        self._tts_service.speech_started.connect(self._handle_speech_started)
        self._tts_service.speech_finished.connect(self._handle_speech_finished)
        self._tts_service.error_occurred.connect(self._handle_tts_error)

    def _handle_wake_word_detected(self, score: float) -> None:
        self._logger.info("Ativacao detectada com score %.6f", score)
        if not self._state_machine.transition_to(AppState.WAKE_WORD_DETECTADA):
            return

        self.status_text_changed.emit(f"Ativacao detectada com score {score:.6f}")
        self._wakeword_service.set_enabled(False)
        if self._state_machine.transition_to(AppState.CAPTURANDO_COMANDO):
            self._command_capture_service.start_capture()
        else:
            self._wakeword_service.set_enabled(True)

    def _handle_command_capture_started(self) -> None:
        self.user_text_changed.emit("Ouvindo comando...")
        self.response_text_changed.emit("Aguardando resposta da IA...")
        self.status_text_changed.emit("Capturando comando de voz...")

    def _handle_command_capture_finished(self, result: CommandCaptureResult) -> None:
        self._logger.info("Comando capturado com %.2fs de audio", result.duration_seconds)
        if self._state_machine.transition_to(AppState.TRANSCREVENDO):
            self.user_text_changed.emit(
                f"Transcrevendo comando capturado ({result.duration_seconds:.2f}s)..."
            )
            self.status_text_changed.emit("Transcrevendo comando...")

    def _handle_command_capture_discarded(self, reason: str) -> None:
        self._logger.info("Captura de comando descartada: %s", reason)
        self._wakeword_service.set_enabled(True)
        self.user_text_changed.emit(reason)
        self.status_text_changed.emit(reason)
        self._state_machine.transition_to(AppState.AGUARDANDO_WAKE_WORD)

    def _handle_transcription_started(self) -> None:
        self.status_text_changed.emit("Transcrevendo comando...")

    def _handle_transcription_completed(self, result: TranscriptionResult) -> None:
        self._logger.info("Texto transcrito pelo mock: %s", result.text)
        self.user_text_changed.emit(result.text)
        if self._state_machine.transition_to(AppState.ENVIANDO_PARA_IA):
            self.status_text_changed.emit("Enviando comando para IA...")
            self.chat_requested.emit(result.text)

    def _handle_chat_started(self, prompt: str) -> None:
        self._logger.info("Enviando prompt para chat mock: %s", prompt)
        self.status_text_changed.emit("Enviando comando para IA...")

    def _handle_chat_completed(self, response: ChatResponse) -> None:
        self._logger.info("Resposta do chat mock: %s", response.text)
        self.response_text_changed.emit(response.text)
        if self._state_machine.transition_to(AppState.REPRODUZINDO_RESPOSTA):
            self.status_text_changed.emit("Reproduzindo resposta...")
            self.tts_requested.emit(response.text)

    def _handle_speech_started(self, text: str) -> None:
        self._logger.info("Iniciando reproducao TTS: %s", text)
        self.status_text_changed.emit("Reproduzindo resposta...")

    def _handle_speech_finished(self, result: SpeechSynthesisResult) -> None:
        self._logger.info("TTS finalizado: %s", result.text)
        self.status_text_changed.emit("Rearmando ativacao...")
        self._schedule_wakeword_rearm()

    def stop_tts(self) -> None:
        if self._current_state_is_reproducing():
            self.status_text_changed.emit("Resposta interrompida manualmente.")
        self._tts_service.stop()
        self._schedule_wakeword_rearm(delay_ms=0)

    def _current_state_is_reproducing(self) -> bool:
        return self._state_machine.current_state == AppState.REPRODUZINDO_RESPOSTA

    def _handle_wakeword_error(self, message: str) -> None:
        self._logger.warning("Falha recuperavel na ativacao: %s", message)
        self._recover_from_pipeline_error(message, rearm_delay_ms=self._wakeword_rearm_delay_ms)

    def _handle_command_capture_error(self, message: str) -> None:
        self._logger.warning("Falha recuperavel na captura de comando: %s", message)
        self.status_text_changed.emit(message)
        self._wakeword_service.set_enabled(True)
        self._state_machine.transition_to(AppState.AGUARDANDO_WAKE_WORD)

    def _handle_stt_error(self, message: str) -> None:
        self._logger.warning("Falha recuperavel no STT: %s", message)
        self.user_text_changed.emit(message)
        self.response_text_changed.emit("Aguardando resposta da IA...")
        self._recover_from_pipeline_error(message)

    def _handle_chat_error(self, message: str) -> None:
        self._logger.warning("Falha recuperavel no chat: %s", message)
        self.response_text_changed.emit(message)
        self._recover_from_pipeline_error(message)

    def _handle_tts_error(self, message: str) -> None:
        self._logger.warning("Falha recuperavel no TTS: %s", message)
        self._recover_from_pipeline_error(message)

    def _handle_critical_error(self, message: str) -> None:
        self._logger.error(message)
        self.status_text_changed.emit(message)
        self._state_machine.transition_to(AppState.ERRO)

    def _recover_from_pipeline_error(self, message: str, rearm_delay_ms: int = 0) -> None:
        self.status_text_changed.emit(f"{message} Reiniciando escuta.")
        self._command_capture_service.cancel_capture("Captura cancelada por falha no pipeline")
        self._wakeword_service.set_enabled(False)
        if rearm_delay_ms > 0:
            self._schedule_wakeword_rearm(delay_ms=rearm_delay_ms)
            return

        self._wakeword_service.set_enabled(True)
        self._state_machine.transition_to(AppState.AGUARDANDO_WAKE_WORD)

    def _schedule_wakeword_rearm(self, delay_ms: int | None = None) -> None:
        def rearm_wake_word() -> None:
            self._wakeword_service.set_enabled(True)
            self._state_machine.transition_to(AppState.AGUARDANDO_WAKE_WORD)

        QTimer.singleShot(
            self._wakeword_rearm_delay_ms if delay_ms is None else delay_ms,
            rearm_wake_word,
        )
