import json
from pathlib import Path
import tempfile
import unittest

from taximetro.config import load_rates
from taximetro.domain import Taximeter
from taximetro.storage import JsonHistory


class PersistenceTests(unittest.TestCase):
    def test_trip_survives_new_instance_and_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            trip = Taximeter().finish()
            JsonHistory(directory).save(trip)
            reopened = JsonHistory(directory)
            reopened.save(trip)
            self.assertEqual(reopened.all(), [trip])

    def test_external_rates_and_invalid_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(json.dumps({"stopped": "0.10", "moving": "0.20"}))
            self.assertEqual(str(load_rates(path).moving), "0.20")
            for data in ('{}', '[]', '{"stopped": "NaN", "moving": "0.05"}', 'broken'):
                path.write_text(data)
                with self.assertRaises(ValueError):
                    load_rates(path)

    def test_corrupt_history_is_reported_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.jsonl"
            path.write_text("broken\n")
            with self.assertRaises(ValueError):
                JsonHistory(directory).save(Taximeter().finish())
            self.assertEqual(path.read_text(), "broken\n")
