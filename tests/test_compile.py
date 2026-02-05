from pathlib import Path
import py_compile


def test_python_sources_compile() -> None:
    root = Path(__file__).resolve().parents[1] / "src" / "clawless"
    for path in root.rglob("*.py"):
        py_compile.compile(str(path), doraise=True)
