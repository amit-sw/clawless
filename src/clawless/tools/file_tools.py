from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from clawless.paths import PathSandbox
from clawless.tools.base import Tool, ToolRegistry


class FileTools:
    def __init__(self, sandbox: PathSandbox):
        self.sandbox = sandbox

    def register(self, registry: ToolRegistry) -> None:
        registry.register(
            Tool(
                name="read_file",
                description="Read a text file from shared_root.",
                input_schema={"path": "relative path under shared_root"},
                handler=self.read_file,
            )
        )
        registry.register(
            Tool(
                name="write_file",
                description="Write a text file to shared_root (overwrite).",
                input_schema={
                    "path": "relative path under shared_root",
                    "content": "full file content",
                },
                handler=self.write_file,
            )
        )
        registry.register(
            Tool(
                name="list_dir",
                description="List entries under a directory in shared_root.",
                input_schema={"path": "relative path under shared_root"},
                handler=self.list_dir,
            )
        )

    def read_file(self, args: dict[str, Any]) -> dict[str, Any]:
        path = self._resolve(args.get("path", ""))
        content = path.read_text(encoding="utf-8")
        return {
            "path": str(path),
            "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
            "content": content,
        }

    def write_file(self, args: dict[str, Any]) -> dict[str, Any]:
        path = self._resolve(args.get("path", ""))
        path.parent.mkdir(parents=True, exist_ok=True)
        content = str(args.get("content", ""))
        path.write_text(content, encoding="utf-8")
        return {
            "path": str(path),
            "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        }

    def list_dir(self, args: dict[str, Any]) -> dict[str, Any]:
        path = self._resolve(args.get("path", "."))
        if not path.exists():
            return {"path": str(path), "entries": []}
        entries = []
        for entry in sorted(path.iterdir(), key=lambda p: p.name):
            entries.append({
                "name": entry.name,
                "is_dir": entry.is_dir(),
            })
        return {"path": str(path), "entries": entries}

    def _resolve(self, relative: str) -> Path:
        return self.sandbox.resolve_shared(relative)
