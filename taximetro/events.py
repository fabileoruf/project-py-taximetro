"""Eventos JSON con rotación; nunca se registran contraseñas."""

from datetime import datetime, timezone
import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


class EventLog:
    def __init__(self, directory):
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(f"taximetro.{directory.resolve()}")
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False
        if not self.logger.handlers:
            handler = RotatingFileHandler(directory / "operations.jsonl", maxBytes=1_000_000,
                                          backupCount=3, encoding="utf-8")
            handler.setFormatter(logging.Formatter("%(message)s"))
            self.logger.addHandler(handler)

    def write(self, event, **fields):
        self.logger.info(json.dumps({"timestamp": datetime.now(timezone.utc).isoformat(),
                                     "event": event, **fields}, ensure_ascii=False))
