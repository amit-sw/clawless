from pathlib import Path

from clawless.db import connect, init_db
from clawless.tracks import TrackManager


def test_track_create_and_last_active(tmp_path: Path) -> None:
    conn = connect(tmp_path / "db.sqlite")
    init_db(conn)
    manager = TrackManager(conn)

    track = manager.get_or_create("work")
    manager.mark_active(track.id)

    last = manager.get_last_active()
    assert last is not None
    assert last.name == "work"
