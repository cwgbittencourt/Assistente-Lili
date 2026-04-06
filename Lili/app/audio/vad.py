from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class VoiceActivityDecision:
    rms: float
    speech_active: bool


class SimpleVoiceActivityDetector:
    def __init__(self, rms_threshold: float) -> None:
        self._rms_threshold = max(0.0, rms_threshold)

    @property
    def rms_threshold(self) -> float:
        return self._rms_threshold

    def analyze(self, samples: np.ndarray) -> VoiceActivityDecision:
        mono = np.asarray(samples, dtype=np.float32).reshape(-1)
        if mono.size == 0:
            return VoiceActivityDecision(rms=0.0, speech_active=False)

        rms = float(np.sqrt(np.mean(np.square(mono), dtype=np.float32)))
        return VoiceActivityDecision(rms=rms, speech_active=rms >= self._rms_threshold)
