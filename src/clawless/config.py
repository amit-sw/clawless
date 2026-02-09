from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Optional

DEFAULT_CONFIG_FILENAME = "config.json"
DEFAULT_HEARTBEAT_PROMPT = (
    "You are running a heartbeat check. If HEARTBEAT.md exists, read it. "
    "Identify anything that needs the user's attention. "
    "If nothing needs attention, reply exactly with HEARTBEAT_OK."
)


def _as_path(value: str | Path) -> Path:
    return value if isinstance(value, Path) else Path(value)


@dataclass
class TelegramConfig:
    token: str = ""
    owner_user_id: int = 0


@dataclass
class LLMConfig:
    connection_string: str = ""
    api_key: str = ""


@dataclass
class PathsConfig:
    config_root: Path = Path("./config")
    internal_root: Path = Path("./internal")
    shared_root: Path = Path("./shared")


@dataclass
class MCPServerConfig:
    name: str
    url: str
    bearer_token: str = ""
    list_method: str = "tools/list"
    call_method: str = "tools/call"


@dataclass
class HeartbeatConfig:
    enabled: bool = True
    interval_minutes: int = 30
    active_hours: Optional[str] = None  # "HH:MM-HH:MM" in local time
    prompt: str = DEFAULT_HEARTBEAT_PROMPT
    checklist_path: str = "HEARTBEAT.md"


@dataclass
class GmailConfig:
    enabled: bool = False


@dataclass
class AppConfig:
    telegram: TelegramConfig = field(default_factory=TelegramConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    paths: PathsConfig = field(default_factory=PathsConfig)
    mcp_servers: list[MCPServerConfig] = field(default_factory=list)
    heartbeat: HeartbeatConfig = field(default_factory=HeartbeatConfig)
    gmail: GmailConfig = field(default_factory=GmailConfig)

    def to_dict(self) -> dict[str, Any]:
        return {
            "telegram": {
                "token": self.telegram.token,
                "owner_user_id": self.telegram.owner_user_id,
            },
            "llm": {
                "connection_string": self.llm.connection_string,
                "api_key": self.llm.api_key,
            },
            "paths": {
                "config_root": str(self.paths.config_root),
                "internal_root": str(self.paths.internal_root),
                "shared_root": str(self.paths.shared_root),
            },
            "mcp_servers": [
                {
                    "name": srv.name,
                    "url": srv.url,
                    "bearer_token": srv.bearer_token,
                    "list_method": srv.list_method,
                    "call_method": srv.call_method,
                }
                for srv in self.mcp_servers
            ],
            "heartbeat": {
                "enabled": self.heartbeat.enabled,
                "interval_minutes": self.heartbeat.interval_minutes,
                "active_hours": self.heartbeat.active_hours,
                "prompt": self.heartbeat.prompt,
                "checklist_path": self.heartbeat.checklist_path,
            },
            "gmail": {
                "enabled": self.gmail.enabled,
            },
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AppConfig":
        telegram = payload.get("telegram", {})
        llm = payload.get("llm", {})
        paths = payload.get("paths", {})
        heartbeat = payload.get("heartbeat", {})
        gmail = payload.get("gmail", {})
        mcp_servers = payload.get("mcp_servers", [])
        return cls(
            telegram=TelegramConfig(
                token=str(telegram.get("token", "")),
                owner_user_id=int(telegram.get("owner_user_id", 0) or 0),
            ),
            llm=LLMConfig(
                connection_string=str(llm.get("connection_string", "")),
                api_key=str(llm.get("api_key", "")),
            ),
            paths=PathsConfig(
                config_root=_as_path(paths.get("config_root", "./config")),
                internal_root=_as_path(paths.get("internal_root", "./internal")),
                shared_root=_as_path(paths.get("shared_root", "./shared")),
            ),
            mcp_servers=[
                MCPServerConfig(
                    name=str(item.get("name", "")),
                    url=str(item.get("url", "")),
                    bearer_token=str(item.get("bearer_token", "")),
                    list_method=str(item.get("list_method", "tools/list")),
                    call_method=str(item.get("call_method", "tools/call")),
                )
                for item in mcp_servers
                if item
            ],
            heartbeat=HeartbeatConfig(
                enabled=bool(heartbeat.get("enabled", True)),
                interval_minutes=int(heartbeat.get("interval_minutes", 30)),
                active_hours=heartbeat.get("active_hours", None),
                prompt=str(heartbeat.get("prompt", DEFAULT_HEARTBEAT_PROMPT)),
                checklist_path=str(heartbeat.get("checklist_path", "HEARTBEAT.md")),
            ),
            gmail=GmailConfig(
                enabled=bool(gmail.get("enabled", False)),
            ),
        )


class ConfigManager:
    def __init__(self, config_root: Path | str):
        self.config_root = _as_path(config_root)
        self.config_path = self.config_root / DEFAULT_CONFIG_FILENAME

    def load(self) -> AppConfig:
        if not self.config_path.exists():
            return AppConfig()
        data = json.loads(self.config_path.read_text(encoding="utf-8"))
        config = AppConfig.from_dict(data)
        config.paths.config_root = self.config_root
        return config

    def save(self, config: AppConfig) -> None:
        self.config_root.mkdir(parents=True, exist_ok=True)
        config.paths.config_root = self.config_root
        self.config_path.write_text(
            json.dumps(config.to_dict(), indent=2, sort_keys=True),
            encoding="utf-8",
        )


def ensure_paths(paths: PathsConfig) -> None:
    for root in (paths.config_root, paths.internal_root, paths.shared_root):
        Path(root).mkdir(parents=True, exist_ok=True)
    Path(paths.internal_root, "skills").mkdir(parents=True, exist_ok=True)
    Path(paths.shared_root, "logs").mkdir(parents=True, exist_ok=True)


def parse_active_hours(value: Optional[str]) -> Optional[tuple[int, int]]:
    if not value:
        return None
    try:
        start_str, end_str = value.split("-", 1)
        start_h, start_m = (int(x) for x in start_str.split(":", 1))
        end_h, end_m = (int(x) for x in end_str.split(":", 1))
    except Exception as exc:  # noqa: BLE001
        raise ValueError("active_hours must be HH:MM-HH:MM") from exc
    return (start_h * 60 + start_m, end_h * 60 + end_m)


def active_hours_contains(value: Optional[str], minutes_since_midnight: int) -> bool:
    window = parse_active_hours(value)
    if window is None:
        return True
    start, end = window
    if start <= end:
        return start <= minutes_since_midnight <= end
    return minutes_since_midnight >= start or minutes_since_midnight <= end


def coerce_config_roots(config: AppConfig) -> AppConfig:
    config.paths.config_root = _as_path(config.paths.config_root).expanduser().resolve()
    config.paths.internal_root = _as_path(config.paths.internal_root).expanduser().resolve()
    config.paths.shared_root = _as_path(config.paths.shared_root).expanduser().resolve()
    return config


def normalize_mcp_servers(servers: Iterable[MCPServerConfig]) -> list[MCPServerConfig]:
    return [srv for srv in servers if srv.name and srv.url]
