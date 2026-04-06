from __future__ import annotations

import numpy as np

from app.audio import EarconService
from app.core import AppState


def test_earcon_service_plays_supported_state_cues() -> None:
    played: list[tuple[np.ndarray, int, bool]] = []
    stop_calls: list[str] = []
    service = EarconService(
        sample_rate=16000,
        volume=0.2,
        play_fn=lambda samples, sample_rate, blocking=False: played.append(
            (samples, sample_rate, blocking)
        ),
        stop_fn=lambda: stop_calls.append("stop"),
    )

    service.play_for_state(AppState.AGUARDANDO_WAKE_WORD)
    service.play_for_state(AppState.ENVIANDO_PARA_IA)

    assert len(played) == 2
    assert len(stop_calls) == 2
    for samples, sample_rate, blocking in played:
        assert sample_rate == 16000
        assert blocking is False
        assert samples.dtype == np.float32
        assert samples.size > 0
        assert float(np.max(np.abs(samples))) <= 0.2 + 1e-6


def test_earcon_service_ignores_unsupported_states() -> None:
    played: list[np.ndarray] = []
    service = EarconService(
        play_fn=lambda samples, *_args, **_kwargs: played.append(samples),
        stop_fn=lambda: None,
    )

    service.play_for_state(AppState.CAPTURANDO_COMANDO)

    assert played == []
