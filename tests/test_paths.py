from pathlib import Path

import pytest

from clawless.paths import PathRoots, PathSandbox


def test_path_sandbox_allows_within(tmp_path: Path) -> None:
    roots = PathRoots(config_root=tmp_path / "config", internal_root=tmp_path / "internal", shared_root=tmp_path / "shared")
    sandbox = PathSandbox(roots)
    resolved = sandbox.resolve_shared("notes/todo.txt")
    assert str(resolved).startswith(str((tmp_path / "shared").resolve()))


def test_path_sandbox_blocks_escape(tmp_path: Path) -> None:
    roots = PathRoots(config_root=tmp_path / "config", internal_root=tmp_path / "internal", shared_root=tmp_path / "shared")
    sandbox = PathSandbox(roots)
    with pytest.raises(PermissionError):
        sandbox.resolve_shared("../config/secret.txt")
