from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtCore import QThread
from PySide6.QtWidgets import QApplication

from app.ai import ChatService, MockChatBackend, OllamaChatBackend, OllamaClientConfig
from app.audio import AudioInputConfig, EarconService, MicrophoneInputStream
from app.config import AppConfig, load_config
from app.core import AppState, AppStateMachine
from app.core.logger import setup_logging
from app.services import CommandCaptureService, OrchestrationService
from app.stt import (
    FasterWhisperConfig,
    FasterWhisperSTTBackend,
    MockSpeechToTextBackend,
    OpenAIWhisperSTTBackend,
    STTService,
)
from app.tts import Pyttsx3TextToSpeechBackend, TTSService
from app.ui.main_window import MainWindow
from app.wakeword import WakeWordSTTConfig, WakeWordSTTService


def _create_stt_service(config: AppConfig, project_root: Path) -> STTService:
    if config.stt_provider == "mock":
        return STTService(
            backend=MockSpeechToTextBackend(fixed_text=config.stt_mock_text),
            sample_rate=config.audio_sample_rate,
        )

    if config.stt_provider == "faster_whisper":
        return STTService(
            backend=FasterWhisperSTTBackend(
                FasterWhisperConfig(
                    model_size=config.stt_model,
                    device=config.stt_device,
                    compute_type=config.stt_compute_type,
                    language=config.stt_language or None,
                    beam_size=config.stt_beam_size,
                )
            ),
            sample_rate=config.audio_sample_rate,
        )

    if config.stt_provider == "openai_whisper":
        return STTService(
            backend=OpenAIWhisperSTTBackend(
                model_size=config.stt_model,
                language=config.stt_language or None,
                device=config.stt_device,
                download_root=project_root / config.stt_model_download_root,
            ),
            sample_rate=config.audio_sample_rate,
        )

    raise RuntimeError(f"Provider de STT nao suportado: {config.stt_provider}")


def _create_chat_service(config: AppConfig) -> ChatService:
    if config.chat_provider == "mock":
        return ChatService(
            backend=MockChatBackend(response_prefix=config.chat_mock_response_prefix),
        )

    if config.chat_provider in {"ollama", "ollama_local"}:
        return ChatService(
            backend=OllamaChatBackend(
                OllamaClientConfig(
                    base_url=config.chat_base_url,
                    model=config.chat_model,
                    timeout_seconds=config.chat_timeout_seconds,
                )
            ),
        )

    return ChatService(
        backend=MockChatBackend(response_prefix=config.chat_mock_response_prefix),
    )


def _create_tts_service(config: AppConfig) -> TTSService:
    if config.tts_provider != "pyttsx3":
        raise RuntimeError(f"Provider de TTS nao suportado: {config.tts_provider}")

    return TTSService(
        backend=Pyttsx3TextToSpeechBackend(
            rate=config.tts_rate,
            volume=config.tts_volume,
            voice_id=config.tts_voice_id or None,
        )
    )


def _create_wakeword_service(
    config: AppConfig,
    phrases: list[str],
) -> WakeWordSTTService:
    backend = FasterWhisperSTTBackend(
        FasterWhisperConfig(
            model_size=config.wakeword_fallback_model,
            device=config.wakeword_fallback_device,
            compute_type=config.wakeword_fallback_compute_type,
            language=config.wakeword_fallback_language or None,
            beam_size=config.wakeword_fallback_beam_size,
        )
    )
    fallback_config = WakeWordSTTConfig(
        sample_rate=config.audio_sample_rate,
        vad_threshold=config.wakeword_fallback_vad_threshold,
        min_duration_ms=config.wakeword_fallback_min_duration_ms,
        max_duration_ms=config.wakeword_fallback_max_duration_ms,
        silence_timeout_ms=config.wakeword_fallback_silence_timeout_ms,
        cooldown_ms=config.wakeword_fallback_cooldown_ms,
    )
    return WakeWordSTTService(
        backend=backend,
        config=fallback_config,
        phrases=phrases,
    )


def _parse_phrase_list(raw_phrases: str) -> list[str]:
    if not raw_phrases:
        return []
    return [item.strip() for item in raw_phrases.split(",") if item.strip()]


def _format_activation_tuning(config: AppConfig) -> str:
    return (
        f"janela={config.wakeword_fallback_min_duration_ms}-"
        f"{config.wakeword_fallback_max_duration_ms}ms | "
        f"silencio={config.wakeword_fallback_silence_timeout_ms}ms | "
        f"vad={config.wakeword_fallback_vad_threshold:.3f} | "
        f"cooldown={config.wakeword_fallback_cooldown_ms}ms | "
        f"modelo={config.wakeword_fallback_model}/{config.wakeword_fallback_compute_type}"
    )


def _get_env_path() -> Path:
    env_file = os.getenv("APP_ENV_FILE")
    if env_file:
        return Path(env_file).expanduser()
    return Path(__file__).resolve().parent.parent / ".env"


def _persist_env_value(key: str, value: str) -> None:
    env_path = _get_env_path()
    if not env_path.exists() or not env_path.is_file():
        return

    lines = env_path.read_text(encoding="utf-8").splitlines()
    updated = False
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in line:
            continue
        name, _ = line.split("=", 1)
        if name.strip() == key:
            lines[index] = f"{key}={value}"
            updated = True
            break

    if not updated:
        lines.append(f"{key}={value}")

    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    config = load_config()
    logger = setup_logging(config.log_level)
    state_machine = AppStateMachine()
    earcon_service = EarconService(sample_rate=config.audio_sample_rate)
    logger.info("Inicializando app %s", config.app_name)
    project_root = Path(__file__).resolve().parent.parent
    phrases = _parse_phrase_list(config.wakeword_phrases)
    wakeword_service = _create_wakeword_service(config, phrases)

    app = QApplication(sys.argv)
    microphone_stream = MicrophoneInputStream(
        AudioInputConfig(
            sample_rate=config.audio_sample_rate,
            channels=config.audio_channels,
            blocksize=config.audio_blocksize,
            device_index=config.input_device_index,
        )
    )
    wakeword_thread = QThread()
    command_capture_service = CommandCaptureService(
        sample_rate=config.audio_sample_rate,
        silence_timeout_ms=config.command_silence_timeout_ms,
        max_duration_ms=config.command_max_duration_ms,
        min_duration_ms=config.command_min_duration_ms,
        vad_threshold=config.command_vad_threshold,
    )
    stt_thread = QThread()
    try:
        stt_service = _create_stt_service(config, project_root)
        chat_service = _create_chat_service(config)
        tts_service = _create_tts_service(config)
    except RuntimeError as exc:
        state_machine.transition_to(AppState.ERRO)
        logger.exception("Falha ao inicializar providers configurados: %s", exc)
        return 1

    try:
        available_tts_voices = tts_service.list_voices()
    except Exception as exc:
        logger.warning("Nao foi possivel listar vozes TTS: %s", exc)
        available_tts_voices = []
    selected_tts_voice_id = tts_service.get_selected_voice_id()

    chat_thread = QThread()
    tts_thread = QThread()
    wakeword_service.moveToThread(wakeword_thread)
    stt_service.moveToThread(stt_thread)
    chat_service.moveToThread(chat_thread)
    tts_service.moveToThread(tts_thread)
    wakeword_thread.start()
    stt_thread.start()
    chat_thread.start()
    tts_thread.start()

    for device in microphone_stream.list_input_devices():
        logger.info(
            "Dispositivo de entrada: index=%s nome=%s hostapi=%s canais=%s",
            device.index,
            device.name,
            device.hostapi_name,
            device.max_input_channels,
        )

    window = MainWindow(
        config.app_name,
        microphone_stream,
        state_machine,
        available_tts_voices=available_tts_voices,
        selected_tts_voice_id=selected_tts_voice_id,
        initial_chat_provider=config.chat_provider,
        initial_chat_model=config.chat_model,
        chat_base_url=config.chat_base_url,
        chat_timeout_seconds=config.chat_timeout_seconds,
    )
    window.set_wakeword_fallback_status(
        enabled=True,
        phrases=phrases,
        tuning=_format_activation_tuning(config),
    )
    wakeword_service.transcription_updated.connect(window.set_wakeword_fallback_transcription)
    command_capture_service.metrics_updated.connect(window.set_command_capture_metrics)
    orchestration_service = OrchestrationService(
        state_machine=state_machine,
        wakeword_service=wakeword_service,
        command_capture_service=command_capture_service,
        stt_service=stt_service,
        chat_service=chat_service,
        tts_service=tts_service,
        wakeword_rearm_delay_ms=min(1500, config.wakeword_fallback_cooldown_ms),
    )
    orchestration_service.status_text_changed.connect(window.set_status_text)
    orchestration_service.user_text_changed.connect(window.set_user_text)
    orchestration_service.response_text_changed.connect(window.set_response_text)
    tts_service.speech_started.connect(window.start_response_waveform)
    tts_service.speech_finished.connect(window.stop_response_waveform)
    window.tts_voice_selected.connect(tts_service.set_voice)
    window.chat_models_requested.connect(chat_service.list_available_models)
    window.chat_config_changed.connect(chat_service.configure_provider)
    def apply_activation_phrase(phrase_text: str) -> None:
        updated_phrases = _parse_phrase_list(phrase_text)
        wakeword_service.set_phrases(updated_phrases)
        window.set_wakeword_fallback_status(
            enabled=True,
            phrases=updated_phrases,
            tuning=_format_activation_tuning(config),
        )
        _persist_env_value("WAKEWORD_PHRASES", ",".join(updated_phrases))
        window.show_wakeword_fallback_feedback("Frases aplicadas e salvas no .env")

    window.wakeword_fallback_apply_requested.connect(apply_activation_phrase)

    def reset_activation_phrase() -> None:
        default_phrases = _parse_phrase_list(config.wakeword_phrases)
        wakeword_service.set_phrases(default_phrases)
        window.set_wakeword_fallback_status(
            enabled=True,
            phrases=default_phrases,
            tuning=_format_activation_tuning(config),
        )
        _persist_env_value("WAKEWORD_PHRASES", ",".join(default_phrases))
        window.show_wakeword_fallback_feedback("Frases resetadas para o padrao")

    window.wakeword_fallback_reset_requested.connect(reset_activation_phrase)
    wakeword_service.set_phrases(phrases)
    chat_service.models_listed.connect(window.set_available_chat_models)
    chat_service.models_list_error.connect(window.set_chat_model_error)
    window.initialize_chat_controls()
    window.tts_stop_requested.connect(orchestration_service.stop_tts)
    window.tts_stop_requested.connect(window.stop_response_waveform)
    state_machine.state_changed.connect(lambda _previous, new: earcon_service.play_for_state(new))

    def handle_microphone_state_changed(running: bool) -> None:
        if running:
            state_machine.transition_to(AppState.AGUARDANDO_WAKE_WORD)

    def handle_microphone_error(message: str) -> None:
        logger.warning("Falha recuperavel no microfone: %s", message)
        command_capture_service.cancel_capture("Captura cancelada por falha no microfone")
        wakeword_service.set_enabled(False)
        state_machine.transition_to(AppState.AGUARDANDO_WAKE_WORD)
        window.set_status_text(f"{message} Ajuste a entrada e tente novamente.")

    microphone_stream.state_changed.connect(handle_microphone_state_changed)
    microphone_stream.error_occurred.connect(handle_microphone_error)
    microphone_stream.samples_changed.connect(wakeword_service.process_samples)
    microphone_stream.samples_changed.connect(command_capture_service.process_samples)

    window.show()
    microphone_stream.start()

    app.aboutToQuit.connect(microphone_stream.stop)
    app.aboutToQuit.connect(command_capture_service.cancel_capture)
    app.aboutToQuit.connect(wakeword_thread.quit)
    app.aboutToQuit.connect(lambda: wakeword_thread.wait())
    app.aboutToQuit.connect(stt_thread.quit)
    app.aboutToQuit.connect(lambda: stt_thread.wait())
    app.aboutToQuit.connect(chat_thread.quit)
    app.aboutToQuit.connect(lambda: chat_thread.wait())
    app.aboutToQuit.connect(tts_service.stop)
    app.aboutToQuit.connect(tts_thread.quit)
    app.aboutToQuit.connect(lambda: tts_thread.wait())

    logger.info("Janela principal exibida com sucesso")
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
