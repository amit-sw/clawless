from pathlib import Path

from clawless.config import HeartbeatConfig
from clawless.heartbeat import run_heartbeat


def test_heartbeat_suppresses_ok(tmp_path: Path) -> None:
    config = HeartbeatConfig(enabled=True, interval_minutes=30, active_hours=None)

    def agent_fn(prompt: str) -> str:
        return "HEARTBEAT_OK"

    result = run_heartbeat(config, tmp_path, agent_fn)
    assert result.suppressed is True


def test_heartbeat_includes_checklist(tmp_path: Path) -> None:
    checklist = tmp_path / "HEARTBEAT.md"
    checklist.write_text("Check backlog", encoding="utf-8")
    config = HeartbeatConfig(enabled=True, interval_minutes=30, active_hours=None)

    captured = {}

    def agent_fn(prompt: str) -> str:
        captured["prompt"] = prompt
        return "OK"

    run_heartbeat(config, tmp_path, agent_fn)
    assert "Check backlog" in captured["prompt"]
