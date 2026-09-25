from decimal import Decimal
import unittest

from taximetro.domain import Rates, Taximeter


class Clock:
    def __init__(self):
        self.now = 0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += int(Decimal(str(seconds)) * 1_000_000_000)


class FareTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.meter = Taximeter(clock=self.clock)

    def test_mixed_trip_60_seconds_stopped_120_moving(self):
        self.clock.advance(60)
        self.meter.change_state("moving")
        self.clock.advance(120)
        result = self.meter.finish()
        self.assertEqual(result["total"], "7.20")
        self.assertEqual(result["duration_seconds"], 180)

    def test_sampling_does_not_round_each_segment(self):
        for _ in range(100):
            self.clock.advance("0.1")
            self.meter.snapshot()
        self.assertEqual(self.meter.finish()["total"], "0.20")

    def test_same_state_does_not_double_charge(self):
        self.clock.advance(10)
        self.meter.change_state("stopped")
        self.clock.advance(10)
        self.assertEqual(self.meter.finish()["total"], "0.40")

    def test_final_total_is_frozen(self):
        self.clock.advance(10)
        first = self.meter.finish()
        self.clock.advance(100)
        self.assertEqual(self.meter.finish(), first)
        with self.assertRaises(ValueError):
            self.meter.change_state("moving")

    def test_invalid_state_preserves_trip(self):
        with self.assertRaises(ValueError):
            self.meter.change_state("flying")
        self.assertEqual(self.meter.state, "stopped")

    def test_invalid_rates(self):
        for value in ("0", "-1", "NaN", "Infinity"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                Rates(stopped=Decimal(value))

    def test_half_cent_rounds_up_at_end(self):
        self.clock.advance("0.25")
        self.assertEqual(self.meter.finish()["total"], "0.01")


if __name__ == "__main__":
    unittest.main()
