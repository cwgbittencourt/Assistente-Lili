import importlib
import os


def test_load_config_reads_values_from_env_file(tmp_path, monkeypatch) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(
            [
                "APP_NAME=Lili Teste",
                "WAKEWORD_PHRASES=lili,jarvis",
                "COMMAND_VAD_THRESHOLD=0.03",
                "STT_MOCK_TEXT=abrir navegador",
                "CHAT_MOCK_RESPONSE_PREFIX=Mock custom:",
                "TTS_VOICE_ID=voz-padrao",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("APP_ENV_FILE", str(env_path))
    config_module = importlib.import_module("app.config")
    config_module = importlib.reload(config_module)

    config = config_module.load_config()

    assert config.app_name == "Lili Teste"
    assert config.wakeword_phrases == "lili,jarvis"
    assert config.command_vad_threshold == 0.03
    assert config.stt_mock_text == "abrir navegador"
    assert config.chat_mock_response_prefix == "Mock custom:"
    assert config.tts_voice_id == "voz-padrao"

    monkeypatch.delenv("APP_ENV_FILE", raising=False)
    importlib.reload(config_module)
    os.environ.pop("APP_NAME", None)
    os.environ.pop("WAKEWORD_PHRASES", None)
    os.environ.pop("COMMAND_VAD_THRESHOLD", None)
    os.environ.pop("STT_MOCK_TEXT", None)
    os.environ.pop("CHAT_MOCK_RESPONSE_PREFIX", None)
    os.environ.pop("TTS_VOICE_ID", None)
