from __future__ import annotations

import numpy as np


class AudioLevelMeter:
    def __init__(self, floor: float = 1.0e-6, min_db: float = -60.0, max_db: float = 0.0) -> None:
        self._floor = floor
        self._min_db = min_db
        self._max_db = max_db

    def calculate(self, samples: np.ndarray) -> float:
        if samples.size == 0:
            return 0.0

        mono = samples.astype(np.float32, copy=False).reshape(-1)
        rms = max(float(np.sqrt(np.mean(np.square(mono)))), self._floor)
        db = 20.0 * float(np.log10(rms))
        normalized = (db - self._min_db) / (self._max_db - self._min_db)
        return max(0.0, min(normalized, 1.0))
