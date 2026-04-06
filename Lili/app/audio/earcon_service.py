from __future__ import annotations

from collections.abc import Callable

import numpy as np
import sounddevice as sd

from app.core import AppState
from app.core.logger import get_logger


class EarconService:
    def __init__(
        self,
        sample_rate: int = 24000,
        volume: float = 0.18,
        enabled: bool = True,
        play_fn: Callable[..., object] | None = None,
        stop_fn: Callable[[], object] | None = None,
    ) -> None:
        self._sample_rate = sample_rate
        self._volume = max(0.0, min(volume, 1.0))
        self._enabled = enabled
        self._play_fn = play_fn or sd.play
        self._stop_fn = stop_fn or sd.stop
        self._logger = get_logger("lili.audio.earcon")

    def play_for_state(self, state: AppState) -> None:
        if not self._enabled:
            return

        samples = self._build_samples_for_state(state)
        if samples is None:
            return

        try:
            self._stop_fn()
        except Exception:
            self._logger.debug("Falha ao interromper cue anterior", exc_info=True)

        try:
            self._play_fn(samples, self._sample_rate, blocking=False)
        except Exception as exc:
            self._logger.warning("Falha ao reproduzir cue de estado %s: %s", state.value, exc)

    def _build_samples_for_state(self, state: AppState) -> np.ndarray | None:
        if state == AppState.AGUARDANDO_WAKE_WORD:
            return self._build_ready_cue()

        if state == AppState.ENVIANDO_PARA_IA:
            return self._build_sending_cue()

        return None

    def _build_ready_cue(self) -> np.ndarray:
        # Timbre mais brilhante e ascendente para indicar "pronto para ouvir".
        notes = [
            self._tone(523.25, 0.055, harmonics=(1.0, 0.25, 0.08)),
            self._silence(0.016),
            self._tone(659.25, 0.060, harmonics=(1.0, 0.22, 0.07)),
            self._silence(0.012),
            self._tone(783.99, 0.075, harmonics=(1.0, 0.18, 0.05)),
        ]
        return self._finalize(np.concatenate(notes))

    def _build_sending_cue(self) -> np.ndarray:
        # Timbre mais focado e levemente mais grave para indicar "enviando/processando".
        notes = [
            self._tone(392.0, 0.070, harmonics=(1.0, 0.45), tremolo_hz=9.0),
            self._silence(0.020),
            self._tone(466.16, 0.095, harmonics=(1.0, 0.35), tremolo_hz=12.0),
        ]
        return self._finalize(np.concatenate(notes))

    def _tone(
        self,
        frequency_hz: float,
        duration_seconds: float,
        harmonics: tuple[float, ...],
        tremolo_hz: float = 0.0,
    ) -> np.ndarray:
        sample_count = max(1, int(self._sample_rate * duration_seconds))
        timeline = np.linspace(0.0, duration_seconds, sample_count, endpoint=False, dtype=np.float32)
        signal = np.zeros(sample_count, dtype=np.float32)

        for index, gain in enumerate(harmonics, start=1):
            signal += gain * np.sin(2.0 * np.pi * frequency_hz * index * timeline, dtype=np.float32)

        if tremolo_hz > 0.0:
            tremolo = 0.82 + 0.18 * np.sin(2.0 * np.pi * tremolo_hz * timeline, dtype=np.float32)
            signal *= tremolo.astype(np.float32)

        attack = max(1, int(sample_count * 0.12))
        release = max(1, int(sample_count * 0.22))
        sustain = max(0, sample_count - attack - release)
        envelope = np.concatenate(
            [
                np.linspace(0.0, 1.0, attack, endpoint=False, dtype=np.float32),
                np.ones(sustain, dtype=np.float32),
                np.linspace(1.0, 0.0, release, endpoint=True, dtype=np.float32),
            ]
        )
        if envelope.size < sample_count:
            envelope = np.pad(envelope, (0, sample_count - envelope.size))

        return (signal[:sample_count] * envelope[:sample_count]).astype(np.float32)

    def _silence(self, duration_seconds: float) -> np.ndarray:
        sample_count = max(1, int(self._sample_rate * duration_seconds))
        return np.zeros(sample_count, dtype=np.float32)

    def _finalize(self, samples: np.ndarray) -> np.ndarray:
        peak = float(np.max(np.abs(samples))) if samples.size else 0.0
        normalized = samples if peak <= 0.0 else samples / peak
        return (normalized * self._volume).astype(np.float32)
