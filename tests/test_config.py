from hermes_trading_relay.config import RelayConfig


def test_config_defaults(monkeypatch):
    for key in [
        "HERMES_RELAY_COMMAND",
        "HERMES_RELAY_PROFILE",
        "HERMES_RELAY_MODEL",
        "HERMES_RELAY_PROVIDER",
        "HERMES_RELAY_HOST",
        "HERMES_RELAY_PORT",
        "HERMES_RELAY_TIMEOUT",
    ]:
        monkeypatch.delenv(key, raising=False)

    cfg = RelayConfig.from_env()

    assert cfg.hermes_command == ["hermes"]
    assert cfg.hermes_profile is None
    assert cfg.host == "127.0.0.1"
    assert cfg.port == 8765
    assert cfg.request_timeout_seconds == 300


def test_config_env_overrides(monkeypatch):
    monkeypatch.setenv("HERMES_RELAY_COMMAND", "python -m hermes")
    monkeypatch.setenv("HERMES_RELAY_PROFILE", "trading")
    monkeypatch.setenv("HERMES_RELAY_PORT", "9999")

    cfg = RelayConfig.from_env()

    assert cfg.hermes_command == ["python", "-m", "hermes"]
    assert cfg.hermes_profile == "trading"
    assert cfg.port == 9999
