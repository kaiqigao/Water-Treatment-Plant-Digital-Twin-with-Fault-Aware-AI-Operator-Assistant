import json
import sqlite3
from threading import Lock
from pathlib import Path

from wtdt.runtime import SimulationSnapshot, TagValue


SCHEMA_PATH = Path(__file__).with_name("schema.sql")


class SQLiteHistorian:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self._lock = Lock()
        self.initialize()

    def initialize(self) -> None:
        with self._lock:
            self.connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
            self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def write_snapshot(self, snapshot: SimulationSnapshot, source: str = "runtime") -> None:
        self.write_tags(snapshot.tags, timestamp_utc=snapshot.timestamp_utc, source=source)

    def write_tags(
        self,
        tags: dict[str, TagValue],
        *,
        timestamp_utc: str,
        source: str,
        quality: str = "good",
    ) -> None:
        rows = [
            (timestamp_utc, tag, _serialize_value(value), quality, source)
            for tag, value in tags.items()
            if _is_scalar_tag(value)
        ]
        with self._lock:
            self.connection.executemany(
                """
                INSERT INTO tag_samples(timestamp_utc, tag, value, quality, source)
                VALUES (?, ?, ?, ?, ?)
                """,
                rows,
            )
            self.connection.commit()

    def read_recent(self, tag: str, limit: int = 120) -> list[dict[str, str]]:
        with self._lock:
            rows = self.connection.execute(
                """
                SELECT timestamp_utc, tag, value, quality, source
                FROM tag_samples
                WHERE tag = ?
                ORDER BY timestamp_utc DESC, id DESC
                LIMIT ?
                """,
                (tag, limit),
            ).fetchall()
        return [dict(row) for row in reversed(rows)]

    def read_latest(self) -> dict[str, str]:
        with self._lock:
            rows = self.connection.execute(
                """
                SELECT tag, value
                FROM tag_samples
                WHERE id IN (
                    SELECT MAX(id)
                    FROM tag_samples
                    GROUP BY tag
                )
                """
            ).fetchall()
        return {str(row["tag"]): str(row["value"]) for row in rows}


def _serialize_value(value: TagValue) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (float, int)):
        return f"{value}"
    return str(value)


def _is_scalar_tag(value: object) -> bool:
    return isinstance(value, (bool, int, float, str))


def parse_value(value: str) -> float | bool | str:
    if value == "true":
        return True
    if value == "false":
        return False
    try:
        return float(value)
    except ValueError:
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
