from pathlib import Path

from clawless.paths import PathRoots, PathSandbox
from clawless.tools.base import ToolRegistry
from clawless.tools.file_tools import FileTools


def test_file_tools_read_write(tmp_path: Path) -> None:
    roots = PathRoots(config_root=tmp_path / "config", internal_root=tmp_path / "internal", shared_root=tmp_path / "shared")
    sandbox = PathSandbox(roots)
    registry = ToolRegistry()
    FileTools(sandbox).register(registry)

    write = registry.get("write_file")
    read = registry.get("read_file")
    assert write and read

    write.handler({"path": "notes.txt", "content": "hello"})
    result = read.handler({"path": "notes.txt"})
    assert result["content"] == "hello"
