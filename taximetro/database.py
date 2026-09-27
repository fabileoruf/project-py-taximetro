"""SQLite: integridad, transacciones y recuperación tras un reinicio."""

from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
import sqlite3

from .storage import JsonHistory

SCHEMA = """
CREATE TABLE IF NOT EXISTS trips (
    id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    ended_at TEXT NOT NULL,
    stopped_ns INTEGER NOT NULL CHECK(stopped_ns >= 0),
    moving_ns INTEGER NOT NULL CHECK(moving_ns >= 0),
    stopped_rate TEXT NOT NULL,
    moving_rate TEXT NOT NULL,
    total_cents INTEGER NOT NULL CHECK(total_cents >= 0),
    state TEXT NOT NULL CHECK(state IN ('stopped', 'moving')),
    status TEXT NOT NULL CHECK(status IN ('completed', 'interrupted'))
);
CREATE INDEX IF NOT EXISTS trips_started_at ON trips(started_at);
CREATE TABLE IF NOT EXISTS active_trip (
    slot INTEGER PRIMARY KEY CHECK(slot = 1),
    snapshot TEXT NOT NULL CHECK(json_valid(snapshot))
);
"""


class SQLiteHistory:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / "taximetro.sqlite3"
        with self.connection() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.executescript(SCHEMA)
        # Migración repetible y transaccional del archivo de la fase 2.
        legacy = JsonHistory(directory).all()
        with self.connection() as connection:
            for trip in legacy:
                self._insert(connection, trip)

    @contextmanager
    def connection(self):
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def _insert(self, connection, trip):
        cents = int(Decimal(trip["total"]) * 100)
        connection.execute("""
            INSERT INTO trips VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO NOTHING
        """, (trip["id"], trip["started_at"], trip["ended_at"],
              trip["stopped_ns"], trip["moving_ns"], trip["rates"]["stopped"],
              trip["rates"]["moving"], cents, trip["state"], trip["status"]))

    def save(self, trip):
        with self.connection() as connection:
            self._insert(connection, trip)
            connection.execute("DELETE FROM active_trip WHERE json_extract(snapshot, '$.id') = ?", (trip["id"],))

    def all(self):
        with self.connection() as connection:
            rows = connection.execute("SELECT * FROM trips ORDER BY started_at DESC").fetchall()
        return [{"id": row["id"], "started_at": row["started_at"], "ended_at": row["ended_at"],
                 "stopped_ns": row["stopped_ns"], "moving_ns": row["moving_ns"],
                 "duration_seconds": round((row["stopped_ns"] + row["moving_ns"]) / 1_000_000_000, 3),
                 "rates": {"stopped": row["stopped_rate"], "moving": row["moving_rate"]},
                 "total": f"{Decimal(row['total_cents']) / 100:.2f}",
                 "state": row["state"], "status": row["status"]} for row in rows]

    def checkpoint(self, trip):
        snapshot = {**trip, "checkpoint_at": datetime.now(timezone.utc).isoformat()}
        with self.connection() as connection:
            connection.execute("INSERT INTO active_trip VALUES (1, ?) ON CONFLICT(slot) DO UPDATE SET snapshot=excluded.snapshot",
                               (json.dumps(snapshot),))

    def recover(self):
        with self.connection() as connection:
            row = connection.execute("SELECT snapshot FROM active_trip WHERE slot=1").fetchone()
            if not row:
                return None
            trip = json.loads(row["snapshot"])
            trip["ended_at"] = trip.pop("checkpoint_at")
            trip["status"] = "interrupted"
            self._insert(connection, trip)
            connection.execute("DELETE FROM active_trip WHERE slot=1")
            return trip
