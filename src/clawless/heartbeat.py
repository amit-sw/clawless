from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

from clawless.config import HeartbeatConfig, active_hours_contains


@dataclass
class HeartbeatResult:
    message: str
    suppressed: bool


def run_heartbeat(config: HeartbeatConfig, shared_root: Path, agent_fn) -> HeartbeatResult:
    now = time.localtime()
    minutes = now.tm_hour * 60 + now.tm_min
    if not active_hours_contains(config.active_hours, minutes):
        return HeartbeatResult("", True)
    checklist_path = (shared_root / config.checklist_path).resolve()
    checklist_text = ""
    if checklist_path.exists():
        checklist_text = checklist_path.read_text(encoding="utf-8")
    prompt = config.prompt
    if checklist_text:
        prompt = f"{prompt}\n\nHEARTBEAT.md:\n{checklist_text}"
    response = agent_fn(prompt)
    suppressed = response.strip() == "HEARTBEAT_OK"
    return HeartbeatResult(response, suppressed)
