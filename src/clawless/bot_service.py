from __future__ import annotations

import json
import os
import time
from pathlib import Path

from clawless.agent import Agent, LangChainLLMClient, LLMClient, Message
from clawless.config import ConfigManager, coerce_config_roots, ensure_paths, normalize_mcp_servers
from clawless.db import connect, init_db
from clawless.heartbeat import run_heartbeat
from clawless.logging_utils import create_log_writer
from clawless.paths import PathRoots, PathSandbox
from clawless.router import route_message
from clawless.scheduler import SchedulerService
from clawless.telegram.adapter import TelegramAdapter
from clawless.tools.base import ToolRegistry
from clawless.tools.file_tools import FileTools
from clawless.tools.mcp_tools import create_loader
from clawless.tools.skill_tools import SkillRunner
from clawless.tracks import TrackManager

DEFAULT_CONFIG_ROOT = Path.home() / ".clawless"


def build_tools(sandbox: PathSandbox, config) -> ToolRegistry:
    registry = ToolRegistry()
    FileTools(sandbox).register(registry)
    SkillRunner(sandbox).register(registry)
    for server in normalize_mcp_servers(config.mcp_servers):
        try:
            loader = create_loader(server)
            loader.register(registry)
        except Exception as exc:  # noqa: BLE001
            print(f"Failed to load MCP server {server.name}: {exc}")
    return registry


def build_agent(config, tools: ToolRegistry, config_path: Path) -> Agent:
    if not config.llm.connection_string or not config.llm.api_key:
        raise RuntimeError(
            "LLM connection_string and api_key must be configured. "
            f"Config path: {config_path}"
        )
    llm: LLMClient = LangChainLLMClient(
        connection_string=config.llm.connection_string,
        api_key=config.llm.api_key,
    )
    return Agent(llm, tools)


def main() -> None:
    config_root = Path(os.environ.get("CLAWLESS_CONFIG_ROOT", str(DEFAULT_CONFIG_ROOT)))
    config_root = config_root.expanduser().resolve()
    manager = ConfigManager(config_root)
    config = manager.load()
    config = coerce_config_roots(config)
    ensure_paths(config.paths)
    log_writer = create_log_writer(Path(config.paths.shared_root))

    db_path = Path(config.paths.internal_root) / "clawless.db"
    conn = connect(db_path)
    init_db(conn)

    sandbox = PathSandbox(
        PathRoots(
            config_root=config.paths.config_root,
            internal_root=config.paths.internal_root,
            shared_root=config.paths.shared_root,
        )
    )
    tools = build_tools(sandbox, config)
    agent = build_agent(config, tools, manager.config_path)
    tracks = TrackManager(conn)

    if not config.telegram.token or not config.telegram.owner_user_id:
        raise RuntimeError(
            "Telegram token and owner_user_id must be configured. "
            f"Config path: {manager.config_path}"
        )
    telegram = TelegramAdapter(config.telegram.token, config.telegram.owner_user_id)

    def send(chat_id: int, text: str) -> None:
        telegram.send_message(chat_id, text)
        log_writer.write(f"send chat_id={chat_id} text={text}")

    def agent_call(prompt: str, track_name: str | None = None) -> str:
        track = tracks.get_or_create(track_name or "default")
        tracks.mark_active(track.id)
        messages = [Message("user", prompt)]
        response = agent.run(track.summary, messages)
        tracks.append_message(track.id, "user", prompt)
        tracks.append_message(track.id, "assistant", response)
        return response

    def on_job(payload: dict) -> None:
        prompt = str(payload.get("prompt", ""))
        track_name = payload.get("track_name")
        response = agent_call(prompt, track_name)
        chat_id = _get_last_chat_id(conn)
        if chat_id:
            send(chat_id, response)

    scheduler = SchedulerService(conn, on_job)
    scheduler.start()
    scheduler.schedule_jobs()

    def heartbeat_job() -> None:
        result = run_heartbeat(config.heartbeat, config.paths.shared_root, lambda p: agent_call(p, "default"))
        if result.suppressed:
            log_writer.write("heartbeat suppressed")
            return
        log_writer.write(f"heartbeat message={result.message}")
        chat_id = _get_last_chat_id(conn)
        if chat_id:
            send(chat_id, result.message)

    if config.heartbeat.enabled:
        scheduler.scheduler.add_job(
            heartbeat_job,
            "interval",
            minutes=config.heartbeat.interval_minutes,
            id="heartbeat",
            replace_existing=True,
        )

    print("Clawless bot service started.")
    while True:
        try:
            updates = telegram.poll()
            for update in updates:
                _set_last_chat_id(conn, update.chat_id)
                log_writer.write(f"recv chat_id={update.chat_id} text={update.text}")
                routed = route_message(update.text)
                if routed.text.startswith("/track"):
                    response = _handle_track_command(routed.text, tracks)
                    send(update.chat_id, response)
                    continue
                track_name = routed.track_name
                if not track_name:
                    last = tracks.get_last_active()
                    track_name = last.name if last else "default"
                track = tracks.get_or_create(track_name)
                tracks.mark_active(track.id)
                tracks.append_message(track.id, "user", routed.text)
                recent = tracks.recent_messages(track.id, limit=20)
                messages = [Message(m["role"], m["content"]) for m in recent]
                response = agent.run(track.summary, messages)
                tracks.append_message(track.id, "assistant", response)
                send(update.chat_id, response)
        except Exception as exc:  # noqa: BLE001
            print(f"Error: {exc}")
            log_writer.write(f"error {exc}")
            time.sleep(2)


def _set_last_chat_id(conn, chat_id: int) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES ('last_chat_id', ?)",
        (str(chat_id),),
    )
    conn.commit()


def _get_last_chat_id(conn) -> int | None:
    row = conn.execute(
        "SELECT value FROM settings WHERE key = 'last_chat_id'"
    ).fetchone()
    if not row:
        return None
    try:
        return int(row["value"])
    except (TypeError, ValueError):
        return None


def _handle_track_command(text: str, tracks: TrackManager) -> str:
    parts = text.strip().split()
    if len(parts) == 1 or parts[1] == "list":
        items = tracks.list_tracks()
        if not items:
            return "No tracks yet."
        return "Tracks: " + ", ".join(t.name for t in items)
    if parts[1] == "set" and len(parts) >= 3:
        name = parts[2]
        track = tracks.get_or_create(name)
        tracks.mark_active(track.id)
        return f"Active track set to {name}."
    if parts[1] == "rename" and len(parts) >= 4:
        old, new = parts[2], parts[3]
        track = tracks.get_by_name(old)
        if not track:
            return f"Track not found: {old}"
        tracks.rename(track.id, new)
        return f"Renamed {old} to {new}."
    if parts[1] == "archive" and len(parts) >= 3:
        name = parts[2]
        track = tracks.get_by_name(name)
        if not track:
            return f"Track not found: {name}"
        tracks.archive(track.id)
        return f"Archived track {name}."
    return "Usage: /track list | /track set <name> | /track rename <old> <new> | /track archive <name>"


if __name__ == "__main__":
    main()
