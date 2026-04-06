import numpy as np

from app.services import CommandCaptureService


def test_command_capture_finishes_after_silence() -> None:
    service = CommandCaptureService(
        sample_rate=16000,
        silence_timeout_ms=400,
        max_duration_ms=3000,
        min_duration_ms=200,
        vad_threshold=0.02,
    )
    captured = []
    service.capture_finished.connect(captured.append)

    speech = np.full(1280, 0.08, dtype=np.float32)
    silence = np.zeros(1280, dtype=np.float32)

    service.start_capture()
    for _ in range(4):
        service.process_samples(speech)
    for _ in range(6):
        service.process_samples(silence)

    assert len(captured) == 1
    assert captured[0].speech_detected is True
    assert captured[0].duration_seconds > 0


def test_command_capture_discards_when_no_valid_speech() -> None:
    service = CommandCaptureService(
        sample_rate=16000,
        silence_timeout_ms=400,
        max_duration_ms=400,
        min_duration_ms=200,
        vad_threshold=0.02,
    )
    discarded = []
    service.capture_discarded.connect(discarded.append)

    silence = np.zeros(1280, dtype=np.float32)

    service.start_capture()
    for _ in range(5):
        service.process_samples(silence)

    assert discarded == ["Captura descartada por falta de fala valida"]
