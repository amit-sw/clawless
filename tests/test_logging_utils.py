from pathlib import Path

from clawless.logging_utils import build_log_path


def test_build_log_path_structure(tmp_path: Path) -> None:
    path = build_log_path(tmp_path, start_ts=1700000000)
    parts = path.relative_to(tmp_path).parts
    assert parts[0] == "logs"
    assert len(parts) == 5
    assert parts[-1].startswith("file")
