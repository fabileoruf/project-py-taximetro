"""Persistencia incremental de las carreras terminadas (fase 2)."""

import json
import os
from pathlib import Path


class JsonHistory:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / "history.jsonl"

    def all(self):
        if not self.path.exists():
            return []
        with self.path.open(encoding="utf-8") as stream:
            return [json.loads(line) for line in stream if line.strip()]

    def save(self, trip):
        # El ID evita duplicar una carrera si se reintenta una escritura.
        if any(row["id"] == trip["id"] for row in self.all()):
            return
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(trip, ensure_ascii=False) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
