from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import sounddevice as sd
from PySide6.QtCore import QObject, Signal

from app.audio.level_meter import AudioLevelMeter
from app.core.logger import get_logger


@dataclass(frozen=True)
class AudioInputConfig:
    sample_rate: int = 16000
    channels: int = 1
    blocksize: int = 1024
    device_index: int | None = None


@dataclass(frozen=True)
class AudioInputDevice:
    index: int
    name: str
    max_input_channels: int
    hostapi_name: str


class MicrophoneInputStream(QObject):
    level_changed = Signal(float)
    samples_changed = Signal(object)
    state_changed = Signal(bool)
    error_occurred = Signal(str)
    device_changed = Signal(str)

    def __init__(self, config: AudioInputConfig, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._config = config
        self._stream: sd.InputStream | None = None
        self._level_meter = AudioLevelMeter()
        self._logger = get_logger("lili.audio.input_stream")

    def start(self) -> None:
        if self._stream is not None:
            return

        try:
            active_device = self.get_active_device()
            self._stream = sd.InputStream(
                samplerate=self._config.sample_rate,
                channels=self._config.channels,
                blocksize=self._config.blocksize,
                dtype="float32",
                device=self._config.device_index,
                callback=self._on_audio_block,
            )
            self._stream.start()
        except Exception as exc:
            self._stream = None
            message = f"Nao foi possivel iniciar o microfone: {exc}"
            self._logger.exception(message)
            self.error_occurred.emit(message)
            return

        self._logger.info(
            "Captura de microfone iniciada (sample_rate=%s, channels=%s, blocksize=%s, device=%s)",
            self._config.sample_rate,
            self._config.channels,
            self._config.blocksize,
            active_device.name,
        )
        self.device_changed.emit(active_device.name)
        self.state_changed.emit(True)

    def stop(self) -> None:
        if self._stream is None:
            return

        stream = self._stream
        self._stream = None

        try:
            stream.stop()
            stream.close()
        except Exception as exc:
            message = f"Falha ao encerrar o microfone: {exc}"
            self._logger.exception(message)
            self.error_occurred.emit(message)
        else:
            self._logger.info("Captura de microfone encerrada")
            self.state_changed.emit(False)
            self.level_changed.emit(0.0)
            self.samples_changed.emit(np.zeros(self._config.blocksize, dtype=np.float32))

    def _on_audio_block(
        self,
        indata: Any,
        frames: int,
        time_info: Any,
        status: sd.CallbackFlags,
    ) -> None:
        del frames, time_info

        if status:
            self._logger.debug("Status do stream de audio: %s", status)

        samples = np.asarray(indata, dtype=np.float32)
        if samples.ndim > 1:
            mono_samples = np.mean(samples, axis=1)
        else:
            mono_samples = samples.reshape(-1)

        level = self._level_meter.calculate(mono_samples)
        self.level_changed.emit(level)
        self.samples_changed.emit(mono_samples.copy())

    def list_input_devices(self) -> list[AudioInputDevice]:
        devices = sd.query_devices()
        hostapis = sd.query_hostapis()
        input_devices: list[AudioInputDevice] = []

        for index, raw_device in enumerate(devices):
            max_input_channels = int(raw_device["max_input_channels"])
            if max_input_channels <= 0:
                continue

            hostapi_index = int(raw_device["hostapi"])
            hostapi_name = str(hostapis[hostapi_index]["name"])
            input_devices.append(
                AudioInputDevice(
                    index=index,
                    name=str(raw_device["name"]),
                    max_input_channels=max_input_channels,
                    hostapi_name=hostapi_name,
                )
            )

        return input_devices

    def get_active_device(self) -> AudioInputDevice:
        if self._config.device_index is None:
            default_input_index = int(sd.default.device[0])
            device_index = default_input_index
        else:
            device_index = self._config.device_index

        for device in self.list_input_devices():
            if device.index == device_index:
                return device

        device_info = sd.query_devices(device_index)
        hostapi_name = str(sd.query_hostapis(int(device_info["hostapi"]))["name"])
        return AudioInputDevice(
            index=device_index,
            name=str(device_info["name"]),
            max_input_channels=int(device_info["max_input_channels"]),
            hostapi_name=hostapi_name,
        )

    def set_device(self, device_index: int | None) -> None:
        should_restart = self._stream is not None
        if should_restart:
            self.stop()

        self._config = AudioInputConfig(
            sample_rate=self._config.sample_rate,
            channels=self._config.channels,
            blocksize=self._config.blocksize,
            device_index=device_index,
        )

        self._logger.info("Dispositivo de entrada alterado para %s", device_index)
        if should_restart:
            self.start()
