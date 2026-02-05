from __future__ import annotations

import importlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from clawless.paths import PathSandbox
from clawless.tools.base import Tool, ToolRegistry


@dataclass
class SkillDefinition:
    name: str
    description: str
    entrypoint: str


class SkillRunner:
    def __init__(self, sandbox: PathSandbox):
        self.sandbox = sandbox
        self.skills_root = self.sandbox.resolve_internal("skills")

    def load_skills(self) -> list[SkillDefinition]:
        if not self.skills_root.exists():
            return []
        skills: list[SkillDefinition] = []
        for entry in sorted(self.skills_root.iterdir(), key=lambda p: p.name):
            if not entry.is_dir():
                continue
            manifest = entry / "skill.json"
            if not manifest.exists():
                continue
            data = json.loads(manifest.read_text(encoding="utf-8"))
            name = str(data.get("name", entry.name))
            description = str(data.get("description", ""))
            entrypoint = str(data.get("entrypoint", ""))
            if name and entrypoint:
                skills.append(SkillDefinition(name, description, entrypoint))
        return skills

    def register(self, registry: ToolRegistry) -> None:
        for skill in self.load_skills():
            registry.register(
                Tool(
                    name=skill.name,
                    description=skill.description or f"Skill {skill.name}",
                    input_schema={"args": "tool-specific args"},
                    handler=self._make_handler(skill),
                )
            )

    def _make_handler(self, skill: SkillDefinition) -> Callable[[dict[str, Any]], dict[str, Any]]:
        def _handler(args: dict[str, Any]) -> dict[str, Any]:
            if str(self.skills_root) not in sys.path:
                sys.path.insert(0, str(self.skills_root))
            module_path, func_name = skill.entrypoint.split(":", 1)
            module = importlib.import_module(module_path)
            func = getattr(module, func_name)
            return func(args)

        return _handler
