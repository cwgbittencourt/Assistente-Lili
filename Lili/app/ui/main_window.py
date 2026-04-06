from __future__ import annotations

import numpy as np
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.ai.providers import (
    ChatProviderConfig,
    PROVIDER_ORDER,
    PROVIDERS,
    get_provider_spec,
)
from app.audio import MicrophoneInputStream
from app.core import AppState, AppStateMachine
from app.tts import TextToSpeechVoice
from app.ui.widgets import WaveformWidget


class MainWindow(QMainWindow):
    tts_voice_selected = Signal(object)
    tts_stop_requested = Signal()
    chat_models_requested = Signal(object)
    chat_config_changed = Signal(object)
    wakeword_fallback_apply_requested = Signal(object)
    wakeword_fallback_reset_requested = Signal()

    _STATE_LABELS = {
        AppState.INICIALIZANDO: "Inicializando",
        AppState.AGUARDANDO_WAKE_WORD: "Aguardando ativacao",
        AppState.WAKE_WORD_DETECTADA: "Ativacao detectada",
        AppState.CAPTURANDO_COMANDO: "Capturando comando",
        AppState.TRANSCREVENDO: "Transcrevendo",
        AppState.ENVIANDO_PARA_IA: "Enviando para IA",
        AppState.REPRODUZINDO_RESPOSTA: "Reproduzindo resposta",
        AppState.ERRO: "Erro",
    }

    _STATE_BADGES = {
        AppState.INICIALIZANDO: "#cfeef0",
        AppState.AGUARDANDO_WAKE_WORD: "#d4e8f7",
        AppState.WAKE_WORD_DETECTADA: "#f6e0c9",
        AppState.CAPTURANDO_COMANDO: "#d9e4ff",
        AppState.TRANSCREVENDO: "#e6dcfb",
        AppState.ENVIANDO_PARA_IA: "#eadff6",
        AppState.REPRODUZINDO_RESPOSTA: "#f5d4e5",
        AppState.ERRO: "#f7c7c7",
    }

    _PROCESSING_STATES = {
        AppState.CAPTURANDO_COMANDO,
        AppState.TRANSCREVENDO,
        AppState.ENVIANDO_PARA_IA,
        AppState.REPRODUZINDO_RESPOSTA,
    }

    def __init__(
        self,
        app_name: str,
        microphone_stream: MicrophoneInputStream,
        state_machine: AppStateMachine,
        available_tts_voices: list[TextToSpeechVoice],
        selected_tts_voice_id: str | None,
        initial_chat_provider: str,
        initial_chat_model: str,
        chat_base_url: str,
        chat_timeout_seconds: float,
    ) -> None:
        super().__init__()
        self._microphone_stream = microphone_stream
        self._state_machine = state_machine
        self._available_tts_voices = available_tts_voices
        self._selected_tts_voice_id = selected_tts_voice_id
        self._device_items_loaded = False
        self._tts_voice_items_loaded = False
        self._chat_items_loaded = False
        self._chat_model_items_loaded = False
        self._active_device_name = "Nenhum dispositivo ativo"
        self._status_message_override: str | None = None
        self._current_state = self._state_machine.current_state
        self.status_detail_label = None
        self.processing_indicator = None
        self._command_duration = 0.0
        self._command_silence = 0.0
        self._command_speech_active = False
        self.command_metric_duration = None
        self.command_metric_silence = None
        self.command_metric_activity = None
        self.command_capture_label = None
        self._wakeword_fallback_enabled = False
        self._wakeword_fallback_phrases: list[str] = []
        self._wakeword_fallback_tuning = ""
        self._wakeword_fallback_last_text = ""
        self._wakeword_fallback_last_detected = False
        self._wakeword_custom_phrase = ""
        self._chat_provider_key = initial_chat_provider
        self._chat_model_name = initial_chat_model
        self._chat_base_url_override = chat_base_url
        self._chat_timeout_seconds = chat_timeout_seconds
        self._provider_model_selection: dict[str, str] = {}
        self._tts_wave_timer = QTimer(self)
        self._tts_wave_timer.setInterval(60)
        self._tts_wave_timer.timeout.connect(self._tick_tts_waveform)
        self._tts_wave_phase = 0.0
        self.setWindowTitle(app_name)
        self.setMinimumSize(1560, 900)
        self.resize(1680, 940)
        self._apply_styles()

        root = QWidget(self)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        layout.addWidget(self._build_header(app_name))
        layout.addWidget(self._build_main_panels(), 1)
        layout.addWidget(self._build_footer_bar())

        self.setCentralWidget(root)
        self._populate_input_devices()
        self._populate_tts_voices()
        self._connect_audio_signals()
        self._connect_chat_signals()
        self._refresh_status_text()
        self._refresh_state_badge()
        self._refresh_processing_indicator()
        self._refresh_command_metrics()

    def set_status_text(self, text: str) -> None:
        self._status_message_override = text
        if self.status_detail_label is not None:
            self.status_detail_label.setText(text)

    def set_user_text(self, text: str) -> None:
        self.user_text_label.setPlainText(text)

    def set_response_text(self, text: str) -> None:
        self.response_text_label.setPlainText(text)

    def start_response_waveform(self, _text: str | None = None) -> None:
        if not self._tts_wave_timer.isActive():
            self._tts_wave_timer.start()

    def stop_response_waveform(self, _result: object | None = None) -> None:
        if self._tts_wave_timer.isActive():
            self._tts_wave_timer.stop()
        self.response_waveform_widget.clear()

    def closeEvent(self, event: QCloseEvent) -> None:
        self._microphone_stream.stop()
        super().closeEvent(event)

    def _build_header(self, app_name: str) -> QWidget:
        card = QFrame(self)
        card.setObjectName("heroCard")
        card.setMinimumHeight(100)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(16)

        title_column = QVBoxLayout()
        title_column.setContentsMargins(0, 0, 0, 0)
        title_column.setSpacing(2)

        title = QLabel(app_name)
        title.setObjectName("heroTitle")
        subtitle = QLabel("Assistente local com ativacao por texto, comando de voz e resposta falada")
        subtitle.setObjectName("heroSubtitle")
        title_column.addWidget(title)
        title_column.addWidget(subtitle)
        top_row.addLayout(title_column, 2)

        metrics_row = QHBoxLayout()
        metrics_row.setContentsMargins(0, 0, 0, 0)
        metrics_row.setSpacing(10)
        self.device_chip = self._create_metric_card("Entrada ativa", "Nenhuma")
        self.flow_chip = self._create_metric_card("Pipeline", "Ativacao -> comando -> resposta")
        self.processing_chip = self._create_metric_card("Processamento", "Em espera")
        metrics_row.addWidget(self.device_chip, 1)
        metrics_row.addWidget(self.flow_chip, 1)
        metrics_row.addWidget(self.processing_chip, 1)
        metrics_container = QWidget(card)
        metrics_container.setLayout(metrics_row)
        top_row.addWidget(metrics_container, 3)

        self.state_badge = QLabel()
        self.state_badge.setObjectName("stateBadge")
        self.state_badge.setAlignment(Qt.AlignCenter)
        self.state_badge.setMinimumHeight(56)
        self.state_badge.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        top_row.addWidget(self.state_badge, 0, Qt.AlignTop)
        layout.addLayout(top_row)
        return card

    def _build_status_strip(self) -> QWidget:
        card = QFrame(self)
        card.setObjectName("statusStrip")
        card.setMinimumHeight(76)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(10)

        status_row = QHBoxLayout()
        status_row.setContentsMargins(0, 0, 0, 0)
        status_row.setSpacing(12)

        label = QLabel("Status atual")
        label.setObjectName("sectionEyebrow")
        self.status_detail_label = QLabel()
        self.status_detail_label.setObjectName("statusDetail")
        self.status_detail_label.setWordWrap(True)

        status_column = QVBoxLayout()
        status_column.setContentsMargins(0, 0, 0, 0)
        status_column.setSpacing(4)
        status_column.addWidget(label)
        status_column.addWidget(self.status_detail_label)
        status_row.addLayout(status_column, 1)

        self.processing_indicator = QProgressBar(card)
        self.processing_indicator.setObjectName("processingIndicator")
        self.processing_indicator.setTextVisible(False)
        self.processing_indicator.setFixedWidth(220)
        self.processing_indicator.hide()
        status_row.addWidget(self.processing_indicator, 0, Qt.AlignVCenter)
        layout.addLayout(status_row)
        return card

    def _build_audio_panel(self) -> QGroupBox:
        group = QGroupBox("Sinal e ativacao")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(20)
        group.setMinimumHeight(520)

        intro = QLabel("Monitore o microfone, troque a entrada e acompanhe a ativacao por texto.")
        intro.setObjectName("panelIntro")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        waveform_card = QFrame(group)
        waveform_card.setObjectName("meterCard")
        waveform_layout = QVBoxLayout(waveform_card)
        waveform_layout.setContentsMargins(14, 12, 14, 12)
        waveform_layout.setSpacing(10)

        waveform_title = QLabel("Sinal de ativacao")
        waveform_title.setObjectName("metricTitle")
        self.waveform_widget = WaveformWidget(waveform_card)
        self.waveform_widget.setMinimumHeight(170)
        self.waveform_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        waveform_layout.addWidget(waveform_title)
        waveform_layout.addWidget(self.waveform_widget, 1)
        layout.addWidget(waveform_card)

        self.level_meter = self._create_meter("Microfone", "Nivel do microfone: %p%")

        kpi_grid = QGridLayout()
        kpi_grid.setContentsMargins(0, 0, 0, 0)
        kpi_grid.setHorizontalSpacing(14)
        kpi_grid.setVerticalSpacing(14)
        kpi_grid.addWidget(self.level_meter.parentWidget(), 0, 0)
        for col in range(1):
            kpi_grid.setColumnStretch(col, 1)
        layout.addLayout(kpi_grid)

        telemetry_card = QFrame(group)
        telemetry_card.setObjectName("telemetryCard")
        telemetry_layout = QVBoxLayout(telemetry_card)
        telemetry_layout.setContentsMargins(16, 12, 16, 12)
        telemetry_layout.setSpacing(8)

        self.wake_word_fallback_label = QLabel()
        self.wake_word_fallback_label.setObjectName("telemetryText")
        self.wake_word_fallback_label.setAlignment(Qt.AlignLeft)
        self.wake_word_fallback_label.setWordWrap(True)
        telemetry_layout.addWidget(self.wake_word_fallback_label)

        layout.addWidget(telemetry_card)
        return group

    def _build_config_panel(self) -> QGroupBox:
        group = QGroupBox("Configuracao")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(16)

        controls_card = QFrame(group)
        controls_card.setObjectName("controlsCard")
        controls_layout = QVBoxLayout(controls_card)
        controls_layout.setContentsMargins(18, 16, 18, 16)
        controls_layout.setSpacing(14)

        controls_grid = QGridLayout()
        controls_grid.setContentsMargins(0, 0, 0, 0)
        controls_grid.setHorizontalSpacing(16)
        controls_grid.setVerticalSpacing(12)

        device_label = QLabel("Microfone")
        device_label.setObjectName("sectionEyebrow")
        self.device_selector = QComboBox(group)
        self.device_selector.currentIndexChanged.connect(self._handle_device_selected)
        self.device_selector.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        controls_grid.addWidget(device_label, 0, 0)
        controls_grid.addWidget(self.device_selector, 1, 0)
        controls_grid.setColumnStretch(0, 1)
        controls_layout.addLayout(controls_grid)

        fallback_card = QFrame(group)
        fallback_card.setObjectName("fallbackCard")
        fallback_layout = QVBoxLayout(fallback_card)
        fallback_layout.setContentsMargins(16, 14, 16, 14)
        fallback_layout.setSpacing(12)

        fallback_label = QLabel("Ativacao por texto")
        fallback_label.setObjectName("sectionEyebrow")
        fallback_layout.addWidget(fallback_label)

        self.wakeword_fallback_input = QTextEdit(group)
        self.wakeword_fallback_input.setObjectName("inlineTextArea")
        self.wakeword_fallback_input.setPlaceholderText("Ex.: lili, hey lili")
        self.wakeword_fallback_input.setLineWrapMode(QTextEdit.WidgetWidth)
        self.wakeword_fallback_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.wakeword_fallback_input.setMinimumHeight(52)
        self.wakeword_fallback_input.setMaximumHeight(72)
        fallback_layout.addWidget(self.wakeword_fallback_input)

        buttons_row = QHBoxLayout()
        buttons_row.setContentsMargins(0, 0, 0, 0)
        buttons_row.setSpacing(12)
        self.wakeword_fallback_apply_button = QPushButton("Aplicar", group)
        self.wakeword_fallback_apply_button.setObjectName("fallbackApplyButton")
        self.wakeword_fallback_apply_button.clicked.connect(self._handle_fallback_apply_requested)
        self.wakeword_fallback_reset_button = QPushButton("Resetar", group)
        self.wakeword_fallback_reset_button.setObjectName("fallbackResetButton")
        self.wakeword_fallback_reset_button.clicked.connect(self._handle_fallback_reset_requested)
        buttons_row.addWidget(self.wakeword_fallback_apply_button)
        buttons_row.addWidget(self.wakeword_fallback_reset_button)
        buttons_row.addStretch(1)
        fallback_layout.addLayout(buttons_row)

        self.wakeword_fallback_feedback = QLabel()
        self.wakeword_fallback_feedback.setObjectName("supportText")
        self.wakeword_fallback_feedback.setAlignment(Qt.AlignLeft)
        self.wakeword_fallback_feedback.setWordWrap(True)
        fallback_layout.addWidget(self.wakeword_fallback_feedback)

        controls_layout.addWidget(fallback_card)
        layout.addWidget(controls_card)
        return group

    def _build_ai_config_panel(self) -> QGroupBox:
        group = QGroupBox("IA e voz")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(16)

        config_card = QFrame(group)
        config_card.setObjectName("controlsCard")
        config_layout = QVBoxLayout(config_card)
        config_layout.setContentsMargins(14, 12, 14, 12)
        config_layout.setSpacing(10)

        controls_row = QGridLayout()
        controls_row.setContentsMargins(0, 0, 0, 0)
        controls_row.setHorizontalSpacing(12)
        controls_row.setVerticalSpacing(8)

        provider_label = QLabel("Provider")
        provider_label.setObjectName("sectionEyebrow")
        model_label = QLabel("Modelo")
        model_label.setObjectName("sectionEyebrow")
        controls_row.addWidget(provider_label, 0, 0)
        controls_row.addWidget(model_label, 0, 1)

        self.chat_provider_selector = QComboBox(group)
        self.chat_provider_selector.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        controls_row.addWidget(self.chat_provider_selector, 1, 0)

        self.chat_model_selector = QComboBox(group)
        self.chat_model_selector.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        controls_row.addWidget(self.chat_model_selector, 1, 1)

        token_label = QLabel("Token")
        token_label.setObjectName("sectionEyebrow")
        controls_row.addWidget(token_label, 2, 0, 1, 2)

        self.chat_token_input = QLineEdit(group)
        self.chat_token_input.setEchoMode(QLineEdit.Password)
        self.chat_token_input.setPlaceholderText("Token de acesso (nao armazenado)")
        controls_row.addWidget(self.chat_token_input, 3, 0, 1, 2)

        self.chat_model_status_label = QLabel()
        self.chat_model_status_label.setObjectName("supportText")
        self.chat_model_status_label.setWordWrap(True)
        controls_row.addWidget(self.chat_model_status_label, 4, 0, 1, 2)

        audio_label = QLabel("Saida de audio")
        audio_label.setObjectName("sectionEyebrow")
        voice_label = QLabel("Voz")
        voice_label.setObjectName("sectionEyebrow")
        controls_row.addWidget(audio_label, 5, 0)
        controls_row.addWidget(voice_label, 5, 1)

        self.audio_output_selector = QComboBox(group)
        self.audio_output_selector.addItem("Padrao do sistema (pyttsx3)", None)
        self.audio_output_selector.setEnabled(False)
        controls_row.addWidget(self.audio_output_selector, 6, 0)

        self.tts_voice_selector = QComboBox(group)
        self.tts_voice_selector.currentIndexChanged.connect(self._handle_tts_voice_selected)
        controls_row.addWidget(self.tts_voice_selector, 6, 1)

        controls_row.setColumnStretch(0, 1)
        controls_row.setColumnStretch(1, 1)
        config_layout.addLayout(controls_row)

        self.tts_stop_button = QPushButton("Interromper fala", group)
        self.tts_stop_button.setObjectName("ttsStopButton")
        self.tts_stop_button.clicked.connect(self._handle_tts_stop_requested)
        config_layout.addWidget(self.tts_stop_button)

        layout.addWidget(config_card)
        return group

    def _build_main_panels(self) -> QWidget:
        container = QWidget(self)
        layout = QGridLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(18)
        layout.setVerticalSpacing(18)

        col_config = QWidget(container)
        config_layout = QVBoxLayout(col_config)
        config_layout.setContentsMargins(0, 0, 0, 0)
        config_layout.setSpacing(18)
        config_layout.addWidget(self._build_config_panel())
        config_layout.addWidget(self._build_ai_config_panel())
        col_config.setMinimumWidth(420)

        col_monitor = QWidget(container)
        monitor_layout = QVBoxLayout(col_monitor)
        monitor_layout.setContentsMargins(0, 0, 0, 0)
        monitor_layout.setSpacing(18)
        monitor_layout.addWidget(self._build_audio_panel())
        col_monitor.setMinimumWidth(520)

        col_interact = QWidget(container)
        interact_layout = QVBoxLayout(col_interact)
        interact_layout.setContentsMargins(0, 0, 0, 0)
        interact_layout.setSpacing(18)
        interact_layout.addWidget(self._build_user_panel())
        interact_layout.addWidget(self._build_response_panel())
        col_interact.setMinimumWidth(520)

        layout.addWidget(col_config, 0, 0)
        layout.addWidget(col_monitor, 0, 1)
        layout.addWidget(col_interact, 0, 2)
        layout.setColumnStretch(0, 4)
        layout.setColumnStretch(1, 4)
        layout.setColumnStretch(2, 4)
        return container

    def _build_footer_bar(self) -> QWidget:
        bar = QFrame(self)
        bar.setObjectName("footerBar")
        bar.setMinimumHeight(60)
        layout = QVBoxLayout(bar)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(6)

        self.command_capture_label = QLabel("Captura de comando inativa")
        self.command_capture_label.setObjectName("supportText")
        self.command_capture_label.setWordWrap(True)
        layout.addWidget(self.command_capture_label)
        return bar

    def _build_user_panel(self) -> QGroupBox:
        group = QGroupBox("Voce disse")
        group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        group.setMinimumHeight(180)
        layout = QVBoxLayout(group)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        intro = QLabel("Ultimo comando capturado ou texto em transcricao.")
        intro.setObjectName("panelIntro")
        layout.addWidget(intro)

        self.user_text_label = QTextEdit(group)
        self.user_text_label.setObjectName("contentCard")
        self.user_text_label.setReadOnly(True)
        self.user_text_label.setPlainText("Aguardando comando de voz...")
        self.user_text_label.setMinimumHeight(90)
        self.user_text_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.user_text_label.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        layout.addWidget(self.user_text_label, 1)
        return group

    def _build_response_panel(self) -> QGroupBox:
        group = QGroupBox("Lili respondeu")
        group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        group.setMinimumHeight(520)
        layout = QVBoxLayout(group)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(16)

        intro = QLabel("Resposta atual da IA, fase de execucao e configuracao da fala.")
        intro.setObjectName("panelIntro")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        self.response_text_label = QTextEdit(group)
        self.response_text_label.setObjectName("contentCard")
        self.response_text_label.setReadOnly(True)
        self.response_text_label.setPlainText("Aguardando resposta da IA...")
        self.response_text_label.setMinimumHeight(240)
        self.response_text_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.response_text_label.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        layout.addWidget(self.response_text_label, 1)

        response_wave_card = QFrame(group)
        response_wave_card.setObjectName("meterCard")
        response_wave_card.setMaximumHeight(140)
        response_wave_layout = QVBoxLayout(response_wave_card)
        response_wave_layout.setContentsMargins(14, 12, 14, 12)
        response_wave_layout.setSpacing(8)
        response_wave_title = QLabel("Sinal da resposta")
        response_wave_title.setObjectName("metricTitle")
        self.response_waveform_widget = WaveformWidget(response_wave_card)
        self.response_waveform_widget.setMinimumHeight(110)
        self.response_waveform_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        response_wave_layout.addWidget(response_wave_title)
        response_wave_layout.addWidget(self.response_waveform_widget, 1)
        layout.addWidget(response_wave_card)

        self.response_phase_label = QLabel("Nenhuma resposta em andamento")
        self.response_phase_label.setObjectName("supportText")
        self.response_phase_label.setWordWrap(True)
        layout.addWidget(self.response_phase_label)
        return group

    def _connect_audio_signals(self) -> None:
        self._microphone_stream.level_changed.connect(self._update_audio_level)
        self._microphone_stream.samples_changed.connect(self._update_waveform)
        self._microphone_stream.state_changed.connect(self._handle_stream_state_changed)
        self._microphone_stream.error_occurred.connect(self.set_status_text)
        self._microphone_stream.device_changed.connect(self._handle_device_changed)
        self._state_machine.state_changed.connect(self._handle_state_changed)

    def _connect_chat_signals(self) -> None:
        self.chat_provider_selector.currentIndexChanged.connect(self._handle_chat_provider_selected)
        self.chat_model_selector.currentIndexChanged.connect(self._handle_chat_model_selected)
        self.chat_token_input.editingFinished.connect(self._handle_chat_token_changed)

    def _create_metric_card(self, title: str, value: str) -> QFrame:
        card = QFrame(self)
        card.setObjectName("metricCard")
        card.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(4)

        title_label = QLabel(title)
        title_label.setObjectName("metricTitle")
        value_label = QLabel(value)
        value_label.setObjectName("metricValue")

        layout.addWidget(title_label)
        layout.addWidget(value_label)
        card.value_label = value_label  # type: ignore[attr-defined]
        return card

    def _create_meter(self, title: str, progress_format: str) -> QFrame:
        card = QFrame(self)
        card.setObjectName("meterCard")
        card.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        label = QLabel(title)
        label.setObjectName("metricTitle")
        meter = QProgressBar(card)
        meter.setRange(0, 100)
        meter.setValue(0)
        meter.setFormat(progress_format)
        meter.setTextVisible(True)

        layout.addWidget(label)
        layout.addWidget(meter)
        return meter

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow {
                background: #f1f3f4;
                font-family: "Bahnschrift";
            }
            QGroupBox {
                background: #ffffff;
                border: 1px solid #e3e7ea;
                border-radius: 18px;
                margin-top: 14px;
                padding-top: 12px;
                color: #1d2b33;
                font-size: 13px;
                font-weight: 600;
            }
            QGroupBox::title {
                left: 18px;
                padding: 0 6px;
            }
            #heroCard {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #d6eef0, stop:0.5 #e7f0f5, stop:1 #e5ecf8);
                border-radius: 24px;
                border: 1px solid #dbe6ec;
            }
            #heroTitle {
                color: #1a2a33;
                font-size: 30px;
                font-weight: 700;
            }
            #heroSubtitle {
                color: #5b6b73;
                font-size: 12px;
            }
            #stateBadge {
                color: #1a2a33;
                padding: 8px 14px;
                border-radius: 14px;
                font-weight: 700;
                min-width: 180px;
            }
            #statusStrip {
                background: #ffffff;
                border: 1px solid #dfe6eb;
                border-radius: 16px;
            }
            #footerBar {
                background: #ffffff;
                border: 1px solid #dfe6eb;
                border-radius: 16px;
            }
            #sectionEyebrow {
                color: #5d6b73;
                font-size: 11px;
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: 0.08em;
            }
            #statusDetail {
                color: #1a2a33;
                font-size: 15px;
                font-weight: 600;
            }
            #metricCard, #meterCard {
                background: #f7fafc;
                border: 1px solid #e3e7ea;
                border-radius: 14px;
                min-height: 56px;
            }
            #metricCard {
                padding-top: 2px;
                padding-bottom: 2px;
            }
            #metricTitle {
                color: #6b7b84;
                font-size: 11px;
                font-weight: 700;
                text-transform: uppercase;
            }
            #metricValue {
                color: #1a2a33;
                font-size: 15px;
                font-weight: 700;
            }
            #panelIntro {
                color: #5f6d76;
                font-size: 12px;
            }
            #supportText {
                color: #6b7a84;
                font-size: 12px;
            }
            #contentCard {
                background: #f7fafc;
                border: 1px solid #e3e7ea;
                border-radius: 14px;
                padding: 18px;
                color: #1a2a33;
                font-size: 16px;
                line-height: 1.35;
            }
            QComboBox {
                background: #ffffff;
                border: 1px solid #d7e0e6;
                border-radius: 10px;
                padding: 8px 10px;
                color: #1a2a33;
                min-height: 18px;
            }
            QLineEdit {
                background: #ffffff;
                border: 1px solid #d7e0e6;
                border-radius: 10px;
                padding: 8px 10px;
                color: #1a2a33;
                min-height: 34px;
            }
            #ttsStopButton {
                background: #cfe9e7;
                border: none;
                border-radius: 10px;
                color: #16343c;
                font-weight: 700;
                font-size: 13px;
                padding: 8px 12px;
                min-height: 20px;
            }
            #ttsStopButton:hover {
                background: #b9dfdb;
            }
            #ttsStopButton:pressed {
                background: #a4d3ce;
            }
            #fallbackApplyButton {
                background: #dfeaf2;
                border: none;
                border-radius: 10px;
                color: #1a2a33;
                font-weight: 700;
                font-size: 13px;
                padding: 8px 12px;
                min-height: 20px;
            }
            #fallbackApplyButton:hover {
                background: #cedeea;
            }
            #fallbackApplyButton:pressed {
                background: #bdd2e1;
            }
            #fallbackResetButton {
                background: #f1e7da;
                border: none;
                border-radius: 10px;
                color: #1a2a33;
                font-weight: 700;
                font-size: 13px;
                padding: 8px 12px;
                min-height: 20px;
            }
            #inlineTextArea {
                background: #ffffff;
                border: 1px solid #d7e0e6;
                border-radius: 10px;
                padding: 8px 10px;
                color: #1a2a33;
                font-size: 13px;
            }
            #fallbackResetButton:hover {
                background: #e6d9c9;
            }
            #fallbackResetButton:pressed {
                background: #dbcab5;
            }
            #controlsCard, #fallbackCard {
                background: #f7fafc;
                border: 1px solid #e3e7ea;
                border-radius: 14px;
            }
            #telemetryCard {
                background: #0f1d23;
                border: 1px solid #1c2b33;
                border-radius: 14px;
            }
            #telemetryText {
                color: #b8c6cc;
                font-size: 11px;
                font-family: "Consolas";
            }
            QProgressBar {
                background: #e9eff3;
                border: none;
                border-radius: 8px;
                color: #1a2a33;
                min-height: 18px;
                text-align: center;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #6fb8c1, stop:1 #8ec5b4);
                border-radius: 8px;
            }
            #processingIndicator {
                min-height: 10px;
                max-height: 10px;
                background: #efe6dc;
            }
            #processingIndicator::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #ddb7a0, stop:1 #cfe0c8);
                border-radius: 8px;
            }
            """
        )

    def _populate_input_devices(self) -> None:
        self._device_items_loaded = False
        self.device_selector.clear()
        self.device_selector.addItem("Padrao do sistema", None)

        for device in self._microphone_stream.list_input_devices():
            label = f"{device.index} - {device.name} [{device.hostapi_name}]"
            self.device_selector.addItem(label, device.index)

        active_device = self._microphone_stream.get_active_device()
        selected_index = self.device_selector.findData(active_device.index)
        if selected_index >= 0:
            self.device_selector.setCurrentIndex(selected_index)
        else:
            self.device_selector.setCurrentIndex(0)

        self._device_items_loaded = True

    def _populate_tts_voices(self) -> None:
        self._tts_voice_items_loaded = False
        self.tts_voice_selector.clear()
        self.tts_voice_selector.addItem("Voz padrao do sistema", "")

        for voice in self._available_tts_voices:
            label = voice.name
            if voice.languages:
                label = f"{voice.name} [{', '.join(voice.languages)}]"
            self.tts_voice_selector.addItem(label, voice.id)

        selected_index = self.tts_voice_selector.findData(self._selected_tts_voice_id or "")
        if selected_index >= 0:
            self.tts_voice_selector.setCurrentIndex(selected_index)
        else:
            self.tts_voice_selector.setCurrentIndex(0)

        self._tts_voice_items_loaded = True

    def _populate_chat_providers(self) -> None:
        self._chat_items_loaded = False
        self.chat_provider_selector.clear()
        for key in PROVIDER_ORDER:
            spec = PROVIDERS[key]
            self.chat_provider_selector.addItem(spec.label, spec.key)

        normalized = "ollama_local" if self._chat_provider_key == "ollama" else self._chat_provider_key
        if normalized not in PROVIDERS:
            normalized = "ollama_local" if "ollama_local" in PROVIDERS else "mock"
        index = self.chat_provider_selector.findData(normalized)
        if index >= 0:
            self.chat_provider_selector.setCurrentIndex(index)
        else:
            self.chat_provider_selector.setCurrentIndex(0)

        self._chat_items_loaded = True
        QTimer.singleShot(
            0,
            lambda: self._handle_chat_provider_selected(
                self.chat_provider_selector.currentIndex()
            ),
        )

    def initialize_chat_controls(self) -> None:
        self._populate_chat_providers()

    def _handle_device_selected(self, combo_index: int) -> None:
        if not self._device_items_loaded:
            return

        device_index = self.device_selector.itemData(combo_index)
        self._microphone_stream.set_device(device_index)

    def _handle_fallback_apply_requested(self) -> None:
        self._wakeword_custom_phrase = self.wakeword_fallback_input.toPlainText().strip()
        self.wakeword_fallback_apply_requested.emit(self._wakeword_custom_phrase)

    def _handle_fallback_reset_requested(self) -> None:
        self.wakeword_fallback_reset_requested.emit()

    def _handle_tts_voice_selected(self, combo_index: int) -> None:
        if not self._tts_voice_items_loaded:
            return

        voice_id = self.tts_voice_selector.itemData(combo_index)
        self._selected_tts_voice_id = None if voice_id in (None, "") else str(voice_id)
        self.tts_voice_selected.emit(self._selected_tts_voice_id)

    def _handle_tts_stop_requested(self) -> None:
        self.tts_stop_requested.emit()

    def _handle_chat_provider_selected(self, combo_index: int) -> None:
        if not self._chat_items_loaded:
            return
        provider_key = self.chat_provider_selector.itemData(combo_index)
        if not provider_key:
            return
        self._chat_provider_key = str(provider_key)
        spec = get_provider_spec(self._chat_provider_key)
        self.chat_token_input.setEnabled(spec.requires_token)
        self.chat_token_input.setVisible(spec.requires_token)
        self.chat_model_status_label.setText("")
        self._request_models_for_provider()

    def _handle_chat_model_selected(self, combo_index: int) -> None:
        if not self._chat_model_items_loaded:
            return
        model_name = self.chat_model_selector.itemData(combo_index)
        if not model_name:
            return
        self._chat_model_name = str(model_name)
        self._provider_model_selection[self._chat_provider_key] = self._chat_model_name
        self._emit_chat_config_changed()

    def _handle_chat_token_changed(self) -> None:
        if not self._chat_items_loaded:
            return
        self._request_models_for_provider()
        self._emit_chat_config_changed()

    def _request_models_for_provider(self) -> None:
        spec = get_provider_spec(self._chat_provider_key)
        self._chat_model_items_loaded = False
        self.chat_model_selector.clear()
        if not spec.supports_model_listing:
            self.chat_model_selector.addItem(spec.label, spec.key)
            self.chat_model_selector.setEnabled(False)
            self._chat_model_items_loaded = True
            self._chat_model_name = spec.key
            self._emit_chat_config_changed()
            return

        token = self.chat_token_input.text().strip()
        if spec.requires_token and not token:
            self.chat_model_selector.addItem("Informe o token para listar modelos", None)
            self.chat_model_selector.setEnabled(False)
            self.chat_model_status_label.setText("Token obrigatorio para listar modelos.")
            return

        self.chat_model_selector.addItem("Carregando modelos...", None)
        self.chat_model_selector.setEnabled(False)
        self.chat_model_status_label.setText("Buscando modelos...")
        self.chat_models_requested.emit(self._build_chat_config())

    def _emit_chat_config_changed(self) -> None:
        spec = get_provider_spec(self._chat_provider_key)
        token = self.chat_token_input.text().strip()
        if spec.requires_token and not token:
            return
        if not self._chat_model_name:
            return
        self.chat_config_changed.emit(self._build_chat_config())

    def _build_chat_config(self) -> ChatProviderConfig:
        base_url = None
        if self._chat_provider_key == "ollama_local" and self._chat_base_url_override:
            base_url = self._chat_base_url_override
        return ChatProviderConfig(
            provider=self._chat_provider_key,
            model=self._chat_model_name,
            api_key=self.chat_token_input.text().strip() or None,
            base_url=base_url,
            timeout_seconds=self._chat_timeout_seconds,
        )

    def set_available_chat_models(self, provider_key: str, models: list[str]) -> None:
        if provider_key != self._chat_provider_key:
            return
        self._chat_model_items_loaded = False
        self.chat_model_selector.clear()
        if not models:
            self.chat_model_selector.addItem("Nenhum modelo encontrado", None)
            self.chat_model_selector.setEnabled(False)
            self.chat_model_status_label.setText("Nenhum modelo retornado pelo provider.")
            return

        for model in models:
            self.chat_model_selector.addItem(model, model)

        preferred = self._provider_model_selection.get(provider_key) or self._chat_model_name
        if preferred:
            preferred_index = self.chat_model_selector.findData(preferred)
            if preferred_index >= 0:
                self.chat_model_selector.setCurrentIndex(preferred_index)
            else:
                self.chat_model_selector.setCurrentIndex(0)
        else:
            self.chat_model_selector.setCurrentIndex(0)

        self.chat_model_selector.setEnabled(True)
        self._chat_model_items_loaded = True
        self._chat_model_name = str(self.chat_model_selector.currentData())
        self.chat_model_status_label.setText("")
        self._emit_chat_config_changed()

    def set_chat_model_error(self, provider_key: str, message: str) -> None:
        if provider_key != self._chat_provider_key:
            return
        self.chat_model_selector.clear()
        self.chat_model_selector.addItem("Falha ao listar modelos", None)
        self.chat_model_selector.setEnabled(False)
        self.chat_model_status_label.setText(message)

    def _update_audio_level(self, level: float) -> None:
        self.level_meter.setValue(int(level * 100))

    def _update_waveform(self, samples) -> None:
        self.waveform_widget.set_samples(samples)

    def _tick_tts_waveform(self) -> None:
        sample_count = 1024
        t = np.linspace(0.0, 2.0 * np.pi, sample_count, endpoint=False) + self._tts_wave_phase
        base = 0.25 * np.sin(t * 3.0) + 0.18 * np.sin(t * 7.0)
        noise = 0.08 * np.random.normal(0.0, 1.0, sample_count)
        envelope = 0.4 + 0.6 * np.random.random()
        samples = (base + noise) * envelope
        samples = np.clip(samples, -1.0, 1.0).astype(np.float32)
        self._tts_wave_phase = (self._tts_wave_phase + 0.35) % (2.0 * np.pi)
        self.response_waveform_widget.set_samples(samples)

    def _handle_stream_state_changed(self, running: bool) -> None:
        if running:
            active_device = self._microphone_stream.get_active_device()
            self._active_device_name = active_device.name
            self._status_message_override = None
            self._refresh_status_text()
            return

        self._active_device_name = "Microfone parado"
        self._refresh_status_text()

    def _handle_device_changed(self, device_name: str) -> None:
        self._active_device_name = device_name
        self._status_message_override = None
        self._refresh_status_text()

    def _handle_state_changed(self, previous_state: AppState, new_state: AppState) -> None:
        del previous_state
        self._current_state = new_state
        self._refresh_state_badge()
        self._refresh_status_text()
        self._refresh_processing_indicator()

    def _refresh_status_text(self) -> None:
        if self.status_detail_label is not None:
            if self._status_message_override:
                self.status_detail_label.setText(self._status_message_override)
            else:
                state_text = self._STATE_LABELS.get(self._current_state, self._current_state.value)
                self.status_detail_label.setText(
                    f"{state_text}. Entrada atual: {self._active_device_name}."
                )

        self.device_chip.value_label.setText(self._active_device_name)  # type: ignore[attr-defined]
        self._refresh_processing_indicator()

    def _refresh_state_badge(self) -> None:
        state_text = self._STATE_LABELS.get(self._current_state, self._current_state.value)
        badge_color = self._STATE_BADGES.get(self._current_state, "#d7c9f2")
        self.state_badge.setText(f"Estado: {state_text}")
        self.state_badge.setStyleSheet(
            f"background:{badge_color}; color:#2c1f3a; padding:9px 16px; border-radius:14px; font-weight:700;"
        )
        self.response_phase_label.setText(f"Fase atual: {state_text}")

    def _refresh_processing_indicator(self) -> None:
        active = self._current_state in self._PROCESSING_STATES
        if self.processing_indicator is not None:
            if active:
                self.processing_indicator.setRange(0, 0)
                self.processing_indicator.show()
            else:
                self.processing_indicator.hide()
                self.processing_indicator.setRange(0, 100)
                self.processing_indicator.setValue(0)

        processing_text = "Em andamento" if active else "Em espera"
        self.processing_chip.value_label.setText(processing_text)  # type: ignore[attr-defined]

    def _refresh_wakeword_fallback(self) -> None:
        status = "Ativo" if self._wakeword_fallback_enabled else "Desativado"
        phrases = ", ".join(self._wakeword_fallback_phrases) or "nenhuma"
        last = self._wakeword_fallback_last_text.strip() or "—"
        last_flag = "detected" if self._wakeword_fallback_last_detected else "ignorado"
        tuning = self._wakeword_fallback_tuning or "padrao"
        self.wake_word_fallback_label.setText(
            (
                f"Ativacao por texto: {status} | Frases: {phrases} | Ultimo: {last} ({last_flag}) | "
                f"{tuning}"
            )
        )

    def _refresh_command_metrics(self) -> None:
        activity_text = "Ativa" if self._command_speech_active else "Monitorando"
        if self.command_metric_duration is not None:
            self.command_metric_duration.value_label.setText(  # type: ignore[attr-defined]
                f"{self._command_duration:.2f}s"
            )
        if self.command_metric_silence is not None:
            self.command_metric_silence.value_label.setText(  # type: ignore[attr-defined]
                f"{self._command_silence:.2f}s"
            )
        if self.command_metric_activity is not None:
            self.command_metric_activity.value_label.setText(activity_text)  # type: ignore[attr-defined]

    def set_wakeword_fallback_status(
        self,
        enabled: bool,
        phrases: list[str],
        tuning: str,
    ) -> None:
        self._wakeword_fallback_enabled = enabled
        self._wakeword_fallback_phrases = list(phrases)
        self._wakeword_fallback_tuning = tuning
        if phrases:
            self.wakeword_fallback_input.setPlainText(", ".join(phrases))
        self._refresh_wakeword_fallback()

    def set_wakeword_fallback_transcription(self, text: str, detected: bool) -> None:
        self._wakeword_fallback_last_text = text
        self._wakeword_fallback_last_detected = detected
        self._refresh_wakeword_fallback()

    def show_wakeword_fallback_feedback(self, message: str) -> None:
        self.wakeword_fallback_feedback.setText(message)
        QTimer.singleShot(2000, lambda: self.wakeword_fallback_feedback.setText(""))

    def set_command_capture_metrics(
        self,
        rms: float,
        speech_active: bool,
        duration_seconds: float,
        silence_seconds: float,
    ) -> None:
        self._command_duration = duration_seconds
        self._command_silence = silence_seconds
        self._command_speech_active = speech_active
        self._refresh_command_metrics()
        speech_text = "sim" if speech_active else "nao"
        if self.command_capture_label is not None:
            self.command_capture_label.setText(
                (
                    f"Captura: {duration_seconds:.2f}s | "
                    f"Silencio: {silence_seconds:.2f}s | "
                    f"RMS do comando: {rms:.4f} | "
                    f"Speech: {speech_text}"
                )
            )
