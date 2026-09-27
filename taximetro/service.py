"""Casos de uso compartidos por terminal, interfaz gráfica y API."""

from datetime import datetime
from decimal import Decimal
from threading import RLock
from zoneinfo import ZoneInfo

from .config import ROOT, load_rates
from .domain import Taximeter

MADRID = ZoneInfo("Europe/Madrid")


class Conflict(ValueError):
    """Un comando incompatible con el estado actual de la carrera."""


class MeterService:
    def __init__(self, history, events, config_path=ROOT / "config.json", factory=Taximeter):
        self.repository = history
        self.events = events
        self.config_path = config_path
        self.factory = factory
        self.meter = None
        self.lock = RLock()
        self.recovered = history.recover() if hasattr(history, "recover") else None
        if self.recovered:
            events.write("trip_recovered", trip_id=self.recovered["id"], status="interrupted")
        events.write("startup")

    def _checkpoint(self, trip):
        if hasattr(self.repository, "checkpoint"):
            self.repository.checkpoint(trip)

    def start(self):
        with self.lock:
            if self.meter:
                raise Conflict("Ya hay una carrera activa. Finalízala antes de iniciar otra.")
            meter = self.factory(load_rates(self.config_path))
            self._checkpoint(meter.snapshot())
            self.meter = meter
            self.events.write("trip_started", trip_id=self.meter.id)
            return self.meter.snapshot()

    def change(self, state):
        with self.lock:
            if not self.meter:
                raise Conflict("Primero inicia una carrera.")
            self.meter.change_state(state)
            self._checkpoint(self.meter.snapshot())
            self.events.write("state_changed", trip_id=self.meter.id, state=state)
            return self.meter.snapshot()

    def finish(self):
        with self.lock:
            if not self.meter:
                raise Conflict("No hay ninguna carrera activa.")
            trip = self.meter.finish()
            # Sólo se libera el taxímetro cuando la escritura ha tenido éxito.
            self.repository.save(trip)
            self.events.write("trip_finished", trip_id=trip["id"], total=trip["total"])
            self.meter = None
            return trip

    def history(self, day=None):
        with self.lock:
            rows = self.repository.all()
            if day:
                datetime.strptime(day, "%Y-%m-%d")
                rows = [row for row in rows if datetime.fromisoformat(row["started_at"])
                        .astimezone(MADRID).date().isoformat() == day]
            return sorted(rows, key=lambda row: row["started_at"], reverse=True)

    def status(self):
        with self.lock:
            today = datetime.now(MADRID).date().isoformat()
            rows = self.history(today)
            rates = self.meter.rates if self.meter else load_rates(self.config_path)
            active = self.meter.snapshot() if self.meter else None
            if active:
                self._checkpoint(active)
            return {
                "active": active, "recovered_trip": self.recovered,
                "rates": {"stopped": str(rates.stopped), "moving": str(rates.moving)},
                "today": today, "trips_today": len(rows),
                "total_today": str(sum((Decimal(row["total"]) for row in rows), Decimal("0.00"))),
            }
