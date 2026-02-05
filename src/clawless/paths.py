from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PathRoots:
    config_root: Path
    internal_root: Path
    shared_root: Path


class PathSandbox:
    def __init__(self, roots: PathRoots):
        self.roots = PathRoots(
            config_root=Path(roots.config_root).expanduser().resolve(),
            internal_root=Path(roots.internal_root).expanduser().resolve(),
            shared_root=Path(roots.shared_root).expanduser().resolve(),
        )

    def resolve_in_root(self, root: Path, relative: str | Path) -> Path:
        candidate = (Path(root) / relative).expanduser().resolve()
        if not self._is_within(candidate, root):
            raise PermissionError(f"Path escapes sandbox root: {candidate}")
        return candidate

    def resolve_config(self, relative: str | Path) -> Path:
        return self.resolve_in_root(self.roots.config_root, relative)

    def resolve_internal(self, relative: str | Path) -> Path:
        return self.resolve_in_root(self.roots.internal_root, relative)

    def resolve_shared(self, relative: str | Path) -> Path:
        return self.resolve_in_root(self.roots.shared_root, relative)

    @staticmethod
    def _is_within(path: Path, root: Path) -> bool:
        try:
            path.relative_to(root)
            return True
        except ValueError:
            return False
