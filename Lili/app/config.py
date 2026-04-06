from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


_DOTENV_LOADED = False


@dataclass(frozen=True)
class AppConfig:
    app_name: str = "Lili"
    log_level: str = "INFO"

    input_device_index: int | None = None
    audio_sample_rate: int = 16000
    audio_channels: int = 1
    audio_blocksize: int = 1280

    wakeword_phrases: str = "lili,jarvis"
    wakeword_fallback_model: str = "tiny"
    wakeword_fallback_device: str = "cpu"
    wakeword_fallback_compute_type: str = "int8"
    wakeword_fallback_language: str = "pt"
    wakeword_fallback_beam_size: int = 1
    wakeword_fallback_vad_threshold: float = 0.02
    wakeword_fallback_min_duration_ms: int = 300
    wakeword_fallback_max_duration_ms: int = 1200
    wakeword_fallback_silence_timeout_ms: int = 400
    wakeword_fallback_cooldown_ms: int = 1500

    command_silence_timeout_ms: int = 1500
    command_max_duration_ms: int = 8000
    command_min_duration_ms: int = 500
    command_vad_threshold: float = 0.02

    stt_provider: str = "faster_whisper"
    stt_mock_text: str = "ligar a luz da sala"
    stt_model: str = "small"
    stt_model_download_root: str = "models/whisper"
    stt_device: str = "cpu"
    stt_compute_type: str = "int8"
    stt_language: str = "pt"
    stt_beam_size: int = 1

    chat_provider: str = "mock"
    chat_mock_response_prefix: str = "Resposta mock para:"
    chat_base_url: str = "http://localhost:11434"
    chat_model: str = "qwen2.5:7b-instruct"
    chat_timeout_seconds: float = 60.0

    tts_provider: str = "pyttsx3"
    tts_rate: int = 180
    tts_volume: float = 1.0
    tts_voice_id: str = ""


def _load_dotenv() -> None:
    global _DOTENV_LOADED
    if _DOTENV_LOADED:
        return

    env_file = os.getenv("APP_ENV_FILE")
    env_path = Path(env_file).expanduser() if env_file else Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists() or not env_path.is_file():
        _DOTENV_LOADED = True
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        name, value = line.split("=", 1)
        key = name.strip()
        if not key or key in os.environ:
            continue

        parsed_value = value.strip()
        if parsed_value and parsed_value[0] == parsed_value[-1] and parsed_value[0] in {'"', "'"}:
            parsed_value = parsed_value[1:-1]
        os.environ[key] = parsed_value

    _DOTENV_LOADED = True


def _read_int(name: str, default: int | None) -> int | None:
    raw_value = os.getenv(name)
    if raw_value is None or raw_value.strip() == "":
        return default
    return int(raw_value)


def _read_float(name: str, default: float) -> float:
    raw_value = os.getenv(name)
    if raw_value is None or raw_value.strip() == "":
        return default
    return float(raw_value)


def _read_str(name: str, default: str) -> str:
    raw_value = os.getenv(name)
    if raw_value is None or raw_value.strip() == "":
        return default
    return raw_value.strip()


def _read_csv(name: str, default: str) -> str:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip()

def _read_prefixed_phrase_lists(prefix: str) -> list[str]:
    phrases: list[str] = []
    for key, value in os.environ.items():
        if not key.startswith(prefix):
            continue
        if not value:
            continue
        phrases.append(value)
    return phrases

def _merge_phrase_sources(*sources: str) -> str:
    merged: list[str] = []
    seen = set()
    for source in sources:
        if not source:
            continue
        for item in source.split(","):
            phrase = item.strip()
            if not phrase or phrase in seen:
                continue
            seen.add(phrase)
            merged.append(phrase)
    return ",".join(merged)



def load_config() -> AppConfig:
    _load_dotenv()

    base_phrases = _read_csv("WAKEWORD_PHRASES", AppConfig.wakeword_phrases)
    fallback_phrase_sources = _read_prefixed_phrase_lists("WAKEWORD_FALLBACK_PHRASES_")
    merged_phrases = _merge_phrase_sources(base_phrases, *fallback_phrase_sources)

    return AppConfig(
        app_name=_read_str("APP_NAME", AppConfig.app_name),
        log_level=_read_str("LOG_LEVEL", AppConfig.log_level),
        input_device_index=_read_int("INPUT_DEVICE_INDEX", AppConfig.input_device_index),
        audio_sample_rate=_read_int("AUDIO_SAMPLE_RATE", AppConfig.audio_sample_rate)
        or AppConfig.audio_sample_rate,
        audio_channels=_read_int("AUDIO_CHANNELS", AppConfig.audio_channels)
        or AppConfig.audio_channels,
        audio_blocksize=_read_int("AUDIO_BLOCKSIZE", AppConfig.audio_blocksize)
        or AppConfig.audio_blocksize,
        wakeword_phrases=merged_phrases,
        wakeword_fallback_model=_read_str(
            "WAKEWORD_FALLBACK_MODEL",
            AppConfig.wakeword_fallback_model,
        ),
        wakeword_fallback_device=_read_str(
            "WAKEWORD_FALLBACK_DEVICE",
            AppConfig.wakeword_fallback_device,
        ),
        wakeword_fallback_compute_type=_read_str(
            "WAKEWORD_FALLBACK_COMPUTE_TYPE",
            AppConfig.wakeword_fallback_compute_type,
        ),
        wakeword_fallback_language=_read_str(
            "WAKEWORD_FALLBACK_LANGUAGE",
            AppConfig.wakeword_fallback_language,
        ),
        wakeword_fallback_beam_size=_read_int(
            "WAKEWORD_FALLBACK_BEAM_SIZE",
            AppConfig.wakeword_fallback_beam_size,
        )
        or AppConfig.wakeword_fallback_beam_size,
        wakeword_fallback_vad_threshold=_read_float(
            "WAKEWORD_FALLBACK_VAD_THRESHOLD",
            AppConfig.wakeword_fallback_vad_threshold,
        ),
        wakeword_fallback_min_duration_ms=_read_int(
            "WAKEWORD_FALLBACK_MIN_DURATION_MS",
            AppConfig.wakeword_fallback_min_duration_ms,
        )
        or AppConfig.wakeword_fallback_min_duration_ms,
        wakeword_fallback_max_duration_ms=_read_int(
            "WAKEWORD_FALLBACK_MAX_DURATION_MS",
            AppConfig.wakeword_fallback_max_duration_ms,
        )
        or AppConfig.wakeword_fallback_max_duration_ms,
        wakeword_fallback_silence_timeout_ms=_read_int(
            "WAKEWORD_FALLBACK_SILENCE_TIMEOUT_MS",
            AppConfig.wakeword_fallback_silence_timeout_ms,
        )
        or AppConfig.wakeword_fallback_silence_timeout_ms,
        wakeword_fallback_cooldown_ms=_read_int(
            "WAKEWORD_FALLBACK_COOLDOWN_MS",
            AppConfig.wakeword_fallback_cooldown_ms,
        )
        or AppConfig.wakeword_fallback_cooldown_ms,
        command_silence_timeout_ms=_read_int(
            "COMMAND_SILENCE_TIMEOUT_MS",
            AppConfig.command_silence_timeout_ms,
        )
        or AppConfig.command_silence_timeout_ms,
        command_max_duration_ms=_read_int(
            "COMMAND_MAX_DURATION_MS",
            AppConfig.command_max_duration_ms,
        )
        or AppConfig.command_max_duration_ms,
        command_min_duration_ms=_read_int(
            "COMMAND_MIN_DURATION_MS",
            AppConfig.command_min_duration_ms,
        )
        or AppConfig.command_min_duration_ms,
        command_vad_threshold=_read_float(
            "COMMAND_VAD_THRESHOLD",
            AppConfig.command_vad_threshold,
        ),
        stt_provider=_read_str("STT_PROVIDER", AppConfig.stt_provider),
        stt_mock_text=_read_str("STT_MOCK_TEXT", AppConfig.stt_mock_text),
        stt_model=_read_str("STT_MODEL", AppConfig.stt_model),
        stt_model_download_root=_read_str(
            "STT_MODEL_DOWNLOAD_ROOT",
            AppConfig.stt_model_download_root,
        ),
        stt_device=_read_str("STT_DEVICE", AppConfig.stt_device),
        stt_compute_type=_read_str("STT_COMPUTE_TYPE", AppConfig.stt_compute_type),
        stt_language=_read_str("STT_LANGUAGE", AppConfig.stt_language),
        stt_beam_size=_read_int("STT_BEAM_SIZE", AppConfig.stt_beam_size)
        or AppConfig.stt_beam_size,
        chat_provider=_read_str("CHAT_PROVIDER", AppConfig.chat_provider),
        chat_mock_response_prefix=_read_str(
            "CHAT_MOCK_RESPONSE_PREFIX",
            AppConfig.chat_mock_response_prefix,
        ),
        chat_base_url=_read_str("CHAT_BASE_URL", AppConfig.chat_base_url),
        chat_model=_read_str("CHAT_MODEL", AppConfig.chat_model),
        chat_timeout_seconds=_read_float(
            "CHAT_TIMEOUT_SECONDS",
            AppConfig.chat_timeout_seconds,
        ),
        tts_provider=_read_str("TTS_PROVIDER", AppConfig.tts_provider),
        tts_rate=_read_int("TTS_RATE", AppConfig.tts_rate) or AppConfig.tts_rate,
        tts_volume=_read_float("TTS_VOLUME", AppConfig.tts_volume),
        tts_voice_id=_read_str("TTS_VOICE_ID", AppConfig.tts_voice_id),
    )
