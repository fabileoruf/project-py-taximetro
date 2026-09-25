"""Cálculo puro del precio: tiempo monotónico y aritmética decimal."""

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
import time
from uuid import uuid4

SECOND = Decimal(1_000_000_000)


@dataclass(frozen=True)
class Rates:
    stopped: Decimal = Decimal("0.02")
    moving: Decimal = Decimal("0.05")

    def __post_init__(self):
        for rate in (self.stopped, self.moving):
            if not isinstance(rate, Decimal) or not rate.is_finite() or rate <= 0:
                raise ValueError("Las tarifas deben ser números positivos y finitos.")


class Taximeter:
    """Una carrera. Consultar el contador no altera ni redondea sus tramos."""

    def __init__(self, rates=None, clock=time.monotonic_ns):
        self.rates = rates or Rates()
        self.clock = clock
        self.id = str(uuid4())
        self.started_at = datetime.now(timezone.utc).isoformat()
        self.state = "stopped"
        self.elapsed = {"stopped": 0, "moving": 0}
        self.last_tick = self.clock()
        self.finished = False

    def _times(self):
        values = self.elapsed.copy()
        if not self.finished:
            values[self.state] += max(0, self.clock() - self.last_tick)
        return values

    def change_state(self, state):
        if self.finished:
            raise ValueError("La carrera ya ha finalizado.")
        if state not in ("stopped", "moving"):
            raise ValueError("Estado no válido: usa stopped o moving.")
        now = self.clock()
        self.elapsed[self.state] += max(0, now - self.last_tick)
        self.last_tick = now
        self.state = state

    def snapshot(self):
        values = self._times()
        total = sum(Decimal(values[state]) / SECOND * getattr(self.rates, state)
                    for state in values)
        return {
            "id": self.id, "started_at": self.started_at, "state": self.state,
            "stopped_ns": values["stopped"], "moving_ns": values["moving"],
            "duration_seconds": round(sum(values.values()) / 1_000_000_000, 3),
            "total": str(total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            "rates": {"stopped": str(self.rates.stopped), "moving": str(self.rates.moving)},
        }

    def finish(self):
        if not self.finished:
            self.change_state(self.state)
            self.finished = True
            self.ended_at = datetime.now(timezone.utc).isoformat()
        return {**self.snapshot(), "ended_at": self.ended_at, "status": "completed"}
