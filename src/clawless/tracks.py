from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Iterable


@dataclass
class Track:
    id: int
    name: str
    summary: str
    last_active: int


class TrackManager:
    def __init__(self, conn):
        self.conn = conn

    def get_or_create(self, name: str) -> Track:
        track = self.get_by_name(name)
        if track:
            return track
        now = int(time.time())
        cursor = self.conn.execute(
            "INSERT INTO tracks (name, summary, last_active) VALUES (?, '', ?)",
            (name, now),
        )
        self.conn.commit()
        return Track(cursor.lastrowid, name, "", now)

    def get_by_name(self, name: str) -> Track | None:
        row = self.conn.execute(
            "SELECT id, name, summary, last_active FROM tracks WHERE name = ?",
            (name,),
        ).fetchone()
        if not row:
            return None
        return Track(row["id"], row["name"], row["summary"], row["last_active"])

    def list_tracks(self) -> list[Track]:
        rows = self.conn.execute(
            "SELECT id, name, summary, last_active FROM tracks ORDER BY name"
        ).fetchall()
        return [Track(r["id"], r["name"], r["summary"], r["last_active"]) for r in rows]

    def mark_active(self, track_id: int) -> None:
        now = int(time.time())
        self.conn.execute(
            "UPDATE tracks SET last_active = ? WHERE id = ?",
            (now, track_id),
        )
        self.conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES ('last_track_id', ?)",
            (str(track_id),),
        )
        self.conn.commit()

    def get_last_active(self) -> Track | None:
        row = self.conn.execute(
            "SELECT value FROM settings WHERE key = 'last_track_id'"
        ).fetchone()
        if not row:
            return None
        try:
            track_id = int(row["value"])
        except (TypeError, ValueError):
            return None
        return self.get_by_id(track_id)

    def get_by_id(self, track_id: int) -> Track | None:
        row = self.conn.execute(
            "SELECT id, name, summary, last_active FROM tracks WHERE id = ?",
            (track_id,),
        ).fetchone()
        if not row:
            return None
        return Track(row["id"], row["name"], row["summary"], row["last_active"])

    def update_summary(self, track_id: int, summary: str) -> None:
        self.conn.execute(
            "UPDATE tracks SET summary = ? WHERE id = ?",
            (summary, track_id),
        )
        self.conn.commit()

    def rename(self, track_id: int, new_name: str) -> None:
        self.conn.execute(
            "UPDATE tracks SET name = ? WHERE id = ?",
            (new_name, track_id),
        )
        self.conn.commit()

    def archive(self, track_id: int) -> None:
        self.conn.execute(
            "DELETE FROM tracks WHERE id = ?",
            (track_id,),
        )
        self.conn.execute(
            "DELETE FROM messages WHERE track_id = ?",
            (track_id,),
        )
        self.conn.execute(
            "DELETE FROM memories WHERE track_id = ?",
            (track_id,),
        )
        self.conn.commit()

    def append_message(self, track_id: int, role: str, content: str) -> None:
        now = int(time.time())
        self.conn.execute(
            "INSERT INTO messages (track_id, role, content, ts) VALUES (?, ?, ?, ?)",
            (track_id, role, content, now),
        )
        self.conn.commit()

    def recent_messages(self, track_id: int, limit: int = 20) -> list[dict[str, str]]:
        rows = self.conn.execute(
            "SELECT role, content FROM messages WHERE track_id = ? ORDER BY id DESC LIMIT ?",
            (track_id, limit),
        ).fetchall()
        items = [{"role": r["role"], "content": r["content"]} for r in rows]
        return list(reversed(items))
