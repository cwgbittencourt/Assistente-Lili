from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from time import monotonic
import re
import unicodedata

import numpy as np
from PySide6.QtCore import QObject, Signal, Slot

from app.audio import SimpleVoiceActivityDetector
from app.core.logger import get_logger
from app.stt.base import SpeechToTextBackend


@dataclass(frozen=True)
class WakeWordSTTConfig:
    sample_rate: int
    vad_threshold: float
    min_duration_ms: int
    max_duration_ms: int
    silence_timeout_ms: int
    cooldown_ms: int


class WakeWordSTTService(QObject):
    wake_word_detected = Signal(float)
    transcription_updated = Signal(str, bool)
    error_occurred = Signal(str)

    def __init__(
        self,
        backend: SpeechToTextBackend,
        config: WakeWordSTTConfig,
        phrases: list[str],
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._logger = get_logger("lili.activation.stt")
        self._backend = backend
        self._config = config
        self._vad = SimpleVoiceActivityDetector(config.vad_threshold)
        self._enabled = True
        self._phrases = self._normalize_phrases(phrases)
        self._cooldown_seconds = max(0.0, config.cooldown_ms / 1000.0)
        self._last_detection_time = -1.0
        self._is_capturing = False
        self._transcribing = False
        self._chunks: list[np.ndarray] = []
        self._total_samples = 0
        self._silence_samples = 0
        self._speech_detected = False
        self._silence_timeout_samples = max(
            1,
            int(config.sample_rate * config.silence_timeout_ms / 1000),
        )
        self._min_duration_samples = max(
            1,
            int(config.sample_rate * config.min_duration_ms / 1000),
        )
        self._max_duration_samples = max(
            self._min_duration_samples,
            int(config.sample_rate * config.max_duration_ms / 1000),
        )

    def set_enabled(self, enabled: bool) -> None:
        if enabled != self._enabled:
            self.reset()
        self._enabled = enabled

    def set_phrases(self, phrases: list[str]) -> None:
        self._phrases = self._normalize_phrases(phrases)

    def reset(self) -> None:
        self._reset_buffers()
        self._transcribing = False

    @Slot(object)
    def process_samples(self, samples: object) -> None:
        if not self._enabled or self._transcribing:
            return

        try:
            audio = np.asarray(samples, dtype=np.float32).reshape(-1)
            if audio.size == 0:
                return

            decision = self._vad.analyze(audio)
            speech_active = decision.speech_active
        except Exception as exc:  # pragma: no cover - defensive path
            message = f"Falha na ativacao por texto: {exc}"
            self._logger.exception(message)
            self.error_occurred.emit(message)
            return

        if not self._is_capturing:
            if not speech_active or self._is_in_cooldown():
                return
            self._start_capture()

        self._append_audio(audio, speech_active)

        if self._should_finish_capture():
            self._finish_capture()

    def _start_capture(self) -> None:
        self._reset_buffers()
        self._is_capturing = True

    def _append_audio(self, audio: np.ndarray, speech_active: bool) -> None:
        self._chunks.append(audio.copy())
        self._total_samples += audio.size
        if speech_active:
            self._speech_detected = True
            self._silence_samples = 0
        elif self._speech_detected:
            self._silence_samples += audio.size

    def _should_finish_capture(self) -> bool:
        if self._total_samples >= self._max_duration_samples:
            return True
        if self._speech_detected and self._silence_samples >= self._silence_timeout_samples:
            return True
        return False

    def _finish_capture(self) -> None:
        audio = np.concatenate(self._chunks) if self._chunks else np.empty(0, dtype=np.float32)
        self._is_capturing = False
        self._reset_buffers()

        if audio.size < self._min_duration_samples:
            return

        self._transcribing = True
        try:
            result = self._backend.transcribe(audio, self._config.sample_rate)
        except Exception as exc:
            message = f"Falha no STT da ativacao por texto: {exc}"
            self._logger.exception(message)
            self.error_occurred.emit(message)
            self._transcribing = False
            return

        text = result.text or ""
        normalized = self._normalize_text(text)
        detected_phrase = self._match_phrase(normalized)
        self._log_comparison(text, normalized, detected_phrase)
        if detected_phrase:
            self._last_detection_time = monotonic()
            self._logger.info(
                "Ativacao detectada via STT: '%s' texto='%s'",
                detected_phrase,
                text,
            )
            self.transcription_updated.emit(text, True)
            self.wake_word_detected.emit(1.0)
        else:
            self._logger.debug("Fallback STT ignorado: texto='%s'", text)
            self.transcription_updated.emit(text, False)
        self._transcribing = False

    def _log_comparison(self, raw_text: str, normalized_text: str, detected_phrase: str | None) -> None:
        try:
            log_path = Path(__file__).resolve().parent.parent.parent / "log.txt"
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            phrases = ", ".join(self._phrases) if self._phrases else "(vazio)"
            detected = detected_phrase or "-"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with log_path.open("a", encoding="utf-8") as handle:
                handle.write(
                    f"{timestamp} | raw={raw_text!r} | normalized={normalized_text!r} | "
                    f"phrases={phrases!r} | detected={detected!r}\n"
                )
        except Exception:
            return

    def _reset_buffers(self) -> None:
        self._chunks = []
        self._total_samples = 0
        self._silence_samples = 0
        self._speech_detected = False

    def _is_in_cooldown(self) -> bool:
        if self._last_detection_time < 0:
            return False
        return (monotonic() - self._last_detection_time) < self._cooldown_seconds

    def _normalize_phrases(self, phrases: list[str]) -> list[str]:
        normalized = []
        for phrase in phrases:
            text = self._normalize_text(phrase)
            if text:
                normalized.append(text)
        return normalized

    def _normalize_text(self, text: str) -> str:
        lowered = text.strip().lower()
        normalized = unicodedata.normalize("NFKD", lowered)
        without_accents = "".join(ch for ch in normalized if not unicodedata.combining(ch))
        cleaned = re.sub(r"[^a-z\\s]", " ", without_accents)
        return re.sub(r"\\s+", " ", cleaned).strip()

    def _match_phrase(self, normalized_text: str) -> str | None:
        if not normalized_text or not self._phrases:
            return None
        words = set(normalized_text.split())
        for phrase in self._phrases:
            if not phrase:
                continue
            if phrase in words:
                return phrase
            if " " in phrase and phrase in normalized_text:
                return phrase
        return None
