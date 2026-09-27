from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from taximetro.database import SQLiteHistory
from taximetro.domain import Taximeter
from taximetro.events import EventLog
from taximetro.lease import application_lock
from taximetro.service import Conflict, MeterService
from taximetro.storage import JsonHistory
from test_domain import Clock


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.repository = SQLiteHistory(self.directory)
        self.clock = Clock()
        self.events = EventLog(self.directory)
        self.service = MeterService(self.repository, self.events,
                                    factory=lambda rates: Taximeter(rates, self.clock))

    def test_completed_trip_survives_restart(self):
        self.service.start()
        self.clock.advance(60)
        receipt = self.service.finish()
        reopened = SQLiteHistory(self.directory)
        self.assertEqual(reopened.all(), [receipt])
        self.assertIsNone(reopened.recover())
        with reopened.connection() as connection:
            self.assertEqual(connection.execute("PRAGMA integrity_check").fetchone()[0], "ok")

    def test_interrupted_trip_is_recovered_without_charging_downtime(self):
        self.service.start()
        self.clock.advance(60)
        self.service.status()  # último registro duradero: 1,20 €
        self.clock.advance(3600)
        restarted = MeterService(SQLiteHistory(self.directory), self.events)
        self.assertIsNone(restarted.status()["active"])
        self.assertEqual(restarted.recovered["total"], "1.20")
        self.assertEqual(restarted.history()[0]["status"], "interrupted")
        again = MeterService(SQLiteHistory(self.directory), self.events)
        self.assertIsNone(again.recovered)
        self.assertEqual(len(again.history()), 1)

    def test_failed_save_can_be_retried_without_losing_or_duplicating_fare(self):
        self.service.start()
        self.clock.advance(60)
        with patch.object(self.repository, "save", side_effect=sqlite3.OperationalError("disk full")):
            with self.assertRaises(sqlite3.OperationalError):
                self.service.finish()
        self.assertIsNotNone(self.service.meter)
        self.clock.advance(600)
        self.assertEqual(self.service.finish()["total"], "1.20")
        self.assertEqual(len(self.repository.all()), 1)

    def test_failed_start_checkpoint_does_not_start_unrecorded_trip(self):
        with patch.object(self.repository, "checkpoint", side_effect=sqlite3.OperationalError("disk full")):
            with self.assertRaises(sqlite3.OperationalError):
                self.service.start()
        self.assertIsNone(self.service.meter)

    def test_parallel_start_requests_create_one_trip(self):
        def start():
            try:
                self.service.start()
                return True
            except Conflict:
                return False
        with ThreadPoolExecutor(max_workers=6) as pool:
            self.assertEqual(sum(pool.map(lambda _: start(), range(6))), 1)

    def test_rate_change_applies_only_to_next_trip(self):
        config = self.directory / "config.json"
        config.write_text('{"stopped":"0.02","moving":"0.05"}')
        self.service.config_path = config
        self.service.start()
        config.write_text('{"stopped":"0.10","moving":"0.20"}')
        self.clock.advance(60)
        self.assertEqual(self.service.finish()["total"], "1.20")
        self.service.start()
        self.clock.advance(60)
        self.assertEqual(self.service.finish()["total"], "6.00")

    def test_legacy_migration_is_idempotent(self):
        trip = Taximeter().finish()
        JsonHistory(self.directory).save(trip)
        self.assertEqual(SQLiteHistory(self.directory).all(), [trip])
        self.assertEqual(SQLiteHistory(self.directory).all(), [trip])

    def test_legacy_migration_rolls_back_on_invalid_record(self):
        good = Taximeter().finish()
        bad = {**Taximeter().finish(), "stopped_ns": -1}
        (self.directory / "history.jsonl").write_text(json.dumps(good) + "\n" + json.dumps(bad) + "\n")
        with self.assertRaises(sqlite3.IntegrityError):
            SQLiteHistory(self.directory)
        self.assertEqual(self.repository.all(), [])

    def test_history_uses_madrid_calendar_day(self):
        trip = {**Taximeter().finish(), "started_at": "2026-09-26T23:30:00+00:00"}
        self.repository.save(trip)
        self.assertEqual(len(self.service.history("2026-09-27")), 1)
        self.assertEqual(self.service.history("2026-09-26"), [])

    def test_only_one_process_lease_per_data_directory(self):
        with application_lock(self.directory):
            with self.assertRaises(ValueError):
                with application_lock(self.directory):
                    self.fail("Un segundo proceso no debe poder entrar")
        with application_lock(self.directory):
            pass
