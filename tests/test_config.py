from pathlib import Path

from clawless.config import AppConfig, ConfigManager


def test_config_roundtrip(tmp_path: Path) -> None:
    manager = ConfigManager(tmp_path)
    config = AppConfig()
    config.telegram.token = "abc"
    config.telegram.owner_user_id = 42
    manager.save(config)
    loaded = manager.load()
    assert loaded.telegram.token == "abc"
    assert loaded.telegram.owner_user_id == 42
