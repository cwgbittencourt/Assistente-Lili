from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app.stt.base import SpeechToTextBackend, TranscriptionResult

try:
    from faster_whisper import WhisperModel
except Exception as exc:  # pragma: no cover - depends on local runtime
    WhisperModel = None
    _faster_whisper_import_error = exc
else:
    _faster_whisper_import_error = None


@dataclass(frozen=True)
class FasterWhisperConfig:
    model_size: str
    device: str
    compute_type: str
    language: str | None
    beam_size: int


class FasterWhisperSTTBackend(SpeechToTextBackend):
    def __init__(self, config: FasterWhisperConfig) -> None:
        self._config = config
        self._model: WhisperModel | None = None

    def transcribe(self, audio: np.ndarray, sample_rate: int) -> TranscriptionResult:
        model = self._ensure_model()
        samples = np.asarray(audio, dtype=np.float32).reshape(-1)
        if samples.size == 0:
            raise ValueError("Nao ha audio para transcrever.")

        if sample_rate != 16000:
            raise ValueError(
                f"Sample rate nao suportado pelo backend atual: {sample_rate}. Esperado: 16000."
            )

        segments, info = model.transcribe(
            samples,
            language=self._config.language,
            beam_size=self._config.beam_size,
            vad_filter=True,
        )
        text = " ".join(segment.text.strip() for segment in segments).strip()
        if not text:
            text = ""

        duration_seconds = samples.size / float(sample_rate)
        confidence = getattr(info, "language_probability", None)
        return TranscriptionResult(
            text=text,
            duration_seconds=duration_seconds,
            confidence=float(confidence) if confidence is not None else None,
        )

    def _ensure_model(self) -> WhisperModel:
        if WhisperModel is None:
            raise RuntimeError(
                "Falha ao importar faster-whisper. "
                f"Erro original: {_faster_whisper_import_error}"
            )

        if self._model is None:
            self._model = WhisperModel(
                self._config.model_size,
                device=self._config.device,
                compute_type=self._config.compute_type,
            )

        return self._model
