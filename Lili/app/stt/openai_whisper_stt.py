from __future__ import annotations

import os
from pathlib import Path

import numpy as np

from app.stt.base import SpeechToTextBackend, TranscriptionResult

try:
    import imageio_ffmpeg
except Exception as exc:  # pragma: no cover - depends on local runtime
    imageio_ffmpeg = None
    _imageio_ffmpeg_import_error = exc
else:
    _imageio_ffmpeg_import_error = None

try:
    import whisper
except Exception as exc:  # pragma: no cover - depends on local runtime
    whisper = None
    _whisper_import_error = exc
else:
    _whisper_import_error = None


class OpenAIWhisperSTTBackend(SpeechToTextBackend):
    def __init__(
        self,
        model_size: str,
        language: str | None,
        device: str,
        download_root: Path,
    ) -> None:
        self._model_size = model_size
        self._language = language
        self._device = device
        self._download_root = Path(download_root)
        self._model = None

    def transcribe(self, audio: np.ndarray, sample_rate: int) -> TranscriptionResult:
        self._ensure_ffmpeg()
        model = self._ensure_model()
        samples = np.asarray(audio, dtype=np.float32).reshape(-1)
        if samples.size == 0:
            raise ValueError("Nao ha audio para transcrever.")

        if sample_rate != 16000:
            raise ValueError(
                f"Sample rate nao suportado pelo backend atual: {sample_rate}. Esperado: 16000."
            )

        result = model.transcribe(
            samples,
            language=self._language,
            fp16=False,
            verbose=False,
        )
        text = str(result.get("text", "")).strip()
        duration_seconds = samples.size / float(sample_rate)
        return TranscriptionResult(
            text=text,
            duration_seconds=duration_seconds,
            confidence=None,
        )

    def _ensure_ffmpeg(self) -> None:
        if imageio_ffmpeg is None:
            raise RuntimeError(
                "Falha ao importar imageio-ffmpeg. "
                f"Erro original: {_imageio_ffmpeg_import_error}"
            )

        ffmpeg_executable = Path(imageio_ffmpeg.get_ffmpeg_exe())
        ffmpeg_dir = str(ffmpeg_executable.parent)
        current_path = os.environ.get("PATH", "")
        if ffmpeg_dir not in current_path.split(os.pathsep):
            os.environ["PATH"] = ffmpeg_dir + os.pathsep + current_path

    def _ensure_model(self):
        if whisper is None:
            raise RuntimeError(
                "Falha ao importar openai-whisper. "
                f"Erro original: {_whisper_import_error}"
            )

        if self._model is None:
            self._download_root.mkdir(parents=True, exist_ok=True)
            self._model = whisper.load_model(
                self._model_size,
                device=self._device,
                download_root=str(self._download_root),
            )

        return self._model
