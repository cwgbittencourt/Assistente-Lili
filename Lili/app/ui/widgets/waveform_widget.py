from __future__ import annotations

from collections import deque

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QWidget


class WaveformWidget(QWidget):
    def __init__(self, parent: QWidget | None = None, bar_count: int = 64) -> None:
        super().__init__(parent)
        self._bar_count = bar_count
        self._history = deque([0.0] * bar_count, maxlen=bar_count)
        self._background_color = QColor("#f1fbfd")
        self._grid_color = QColor("#dceff2")
        self._bar_color = QColor("#84cbc5")
        self._peak_color = QColor("#f0aeca")
        self.setMinimumHeight(160)

    def set_samples(self, samples: np.ndarray) -> None:
        if samples.size == 0:
            return

        mono = samples.astype(np.float32, copy=False).reshape(-1)
        bucket_size = max(1, mono.size // self._bar_count)
        bucket_count = max(1, mono.size // bucket_size)
        trimmed = mono[: bucket_count * bucket_size]
        reshaped = trimmed.reshape(bucket_count, bucket_size)
        amplitudes = np.max(np.abs(reshaped), axis=1)

        for amplitude in amplitudes:
            self._history.append(float(amplitude))

        self.update()

    def clear(self) -> None:
        self._history.clear()
        self._history.extend([0.0] * self._bar_count)
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        del event

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.fillRect(self.rect(), self._background_color)
        self._draw_grid(painter)
        self._draw_bars(painter)

    def _draw_grid(self, painter: QPainter) -> None:
        painter.save()
        painter.setPen(QPen(self._grid_color, 1))
        height = float(self.height())
        width = float(self.width())

        for fraction in (0.25, 0.5, 0.75):
            y = height * fraction
            painter.drawLine(QPointF(0.0, y), QPointF(width, y))

        painter.restore()

    def _draw_bars(self, painter: QPainter) -> None:
        painter.save()
        values = list(self._history)
        if not values:
            painter.restore()
            return

        width = float(self.width())
        height = float(self.height())
        bar_width = max(3.0, width / (len(values) * 1.6))
        gap = bar_width * 0.6
        total_width = len(values) * bar_width + max(0, len(values) - 1) * gap
        start_x = (width - total_width) / 2.0
        center_y = height / 2.0

        painter.setPen(Qt.NoPen)
        for index, value in enumerate(values):
            normalized = max(0.04, min(float(value), 1.0))
            bar_height = normalized * (height * 0.9)
            rect = QRectF(
                start_x + index * (bar_width + gap),
                center_y - bar_height / 2.0,
                bar_width,
                bar_height,
            )
            color = self._peak_color if normalized > 0.75 else self._bar_color
            painter.setBrush(color)
            painter.drawRoundedRect(rect, bar_width / 2.0, bar_width / 2.0)

        painter.restore()
