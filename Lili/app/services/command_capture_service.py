from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from PySide6.QtCore import QObject, Signal, Slot

from app.audio import SimpleVoiceActivityDetector
from app.core.logger import get_logger


@dataclass(frozen=True)
class CommandCaptureResult:
    audio: np.ndarray
    duration_seconds: float
    speech_detected: bool


class CommandCaptureService(QObject):
    capture_started = Signal()
    capture_finished = Signal(object)
    capture_discarded = Signal(str)
    metrics_updated = Signal(float, bool, float, float)
    error_occurred = Signal(str)

    def __init__(
        self,
        sample_rate: int,
        silence_timeout_ms: int,
        max_duration_ms: int,
        min_duration_ms: int,
        vad_threshold: float,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._logger = get_logger("lili.services.command_capture")
        self._sample_rate = sample_rate
        self._silence_timeout_samples = max(0, int(sample_rate * silence_timeout_ms / 1000))
        self._max_duration_samples = max(1, int(sample_rate * max_duration_ms / 1000))
        self._min_duration_samples = max(0, int(sample_rate * min_duration_ms / 1000))
        self._vad = SimpleVoiceActivityDetector(vad_threshold)
        self._is_capturing = False
        self._chunks: list[np.ndarray] = []
        self._total_samples = 0
        self._speech_samples = 0
        self._silence_samples = 0
        self._speech_detected = False
        self._speech_peak_rms = 0.0
        self._silence_ratio = 0.35

    @property
    def is_capturing(self) -> bool:
        return self._is_capturing

    def start_capture(self) -> None:
        self._reset_buffers()
        self._is_capturing = True
        self._logger.info("Captura de comando iniciada")
        self.capture_started.emit()

    def cancel_capture(self, reason: str = "Captura cancelada") -> None:
        if not self._is_capturing:
            return

        self._logger.info("Captura de comando cancelada: %s", reason)
        self._reset_buffers()
        self._is_capturing = False
        self.capture_discarded.emit(reason)

    @Slot(object)
    def process_samples(self, samples: object) -> None:
        if not self._is_capturing:
            return

        try:
            audio = np.asarray(samples, dtype=np.float32).reshape(-1)
            if audio.size == 0:
                return

            vad_decision = self._vad.analyze(audio)
            speech_active = self._is_speech_active(vad_decision.rms)
            self._chunks.append(audio.copy())
            self._total_samples += audio.size

            if speech_active:
                self._speech_detected = True
                self._speech_samples += audio.size
                self._silence_samples = 0
                self._speech_peak_rms = max(self._speech_peak_rms, vad_decision.rms)
            elif self._speech_detected:
                self._silence_samples += audio.size

            duration_seconds = self._total_samples / self._sample_rate
            silence_seconds = self._silence_samples / self._sample_rate
            self.metrics_updated.emit(
                vad_decision.rms,
                speech_active,
                duration_seconds,
                silence_seconds,
            )

            if self._speech_detected and self._silence_samples >= self._silence_timeout_samples:
                self._finish_capture(trim_trailing_silence=True)
                return

            if self._total_samples >= self._max_duration_samples:
                self._finish_capture(trim_trailing_silence=self._speech_detected)
        except Exception as exc:  # pragma: no cover - defensive path
            message = f"Falha na captura do comando: {exc}"
            self._logger.exception(message)
            self.error_occurred.emit(message)
            self.cancel_capture(message)

    def _finish_capture(self, trim_trailing_silence: bool) -> None:
        audio = np.concatenate(self._chunks) if self._chunks else np.empty(0, dtype=np.float32)
        if trim_trailing_silence and self._silence_samples > 0:
            audio = audio[:-self._silence_samples] if self._silence_samples < audio.size else np.empty(
                0,
                dtype=np.float32,
            )

        result = CommandCaptureResult(
            audio=audio,
            duration_seconds=(audio.size / self._sample_rate) if audio.size else 0.0,
            speech_detected=self._speech_detected,
        )
        self._is_capturing = False

        if not result.speech_detected or result.audio.size < self._min_duration_samples:
            reason = "Captura descartada por falta de fala valida"
            self._logger.info(reason)
            self._reset_buffers()
            self.capture_discarded.emit(reason)
            return

        self._logger.info(
            "Captura de comando concluida: duracao=%.2fs amostras=%s",
            result.duration_seconds,
            result.audio.size,
        )
        self._reset_buffers()
        self.capture_finished.emit(result)

    def _reset_buffers(self) -> None:
        self._chunks = []
        self._total_samples = 0
        self._speech_samples = 0
        self._silence_samples = 0
        self._speech_detected = False
        self._speech_peak_rms = 0.0

    def _is_speech_active(self, rms: float) -> bool:
        if not self._speech_detected:
            return rms >= max(self._vad.rms_threshold, 0.02)

        dynamic_threshold = max(0.015, self._speech_peak_rms * self._silence_ratio)
        return rms >= dynamic_threshold
