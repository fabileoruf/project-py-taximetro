"""Interfaz de terminal de la fase 1."""

from .domain import Taximeter
from .config import ROOT, load_rates
from .events import EventLog
from .storage import JsonHistory
import os
from pathlib import Path

HELP = """
TAXITECH · Taxímetro digital
Tarifas cargadas desde config.json al iniciar cada carrera.
i = iniciar · p = parado · m = movimiento · e = estado
f = finalizar · h = historial · a = ayuda · q = salir
El tiempo se cobra continuamente, aunque no escribas comandos.
Cada carrera empieza en estado parado. Pulsa Enter después del comando.
"""


def run():
    print(HELP)
    directory = Path(os.environ.get("TAXIMETRO_DATA", ROOT / "data"))
    history = JsonHistory(directory)
    events = EventLog(directory)
    events.write("startup", interface="cli")
    meter = None
    while True:
        try:
            command = input("taxi> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            command = "q"
        try:
            if command == "a":
                print(HELP)
            elif command == "i":
                if meter:
                    raise ValueError("Finaliza la carrera actual antes de iniciar otra.")
                meter = Taximeter(load_rates())
                events.write("trip_started", trip_id=meter.id)
                print(f"Carrera iniciada. Parado: {meter.rates.stopped} €/s; movimiento: {meter.rates.moving} €/s.")
            elif command in ("p", "m", "e", "f"):
                if not meter:
                    raise ValueError("Primero inicia una carrera con i.")
                if command in ("p", "m"):
                    meter.change_state("stopped" if command == "p" else "moving")
                    events.write("state_changed", trip_id=meter.id, state=meter.state)
                result = meter.finish() if command == "f" else meter.snapshot()
                print(f"{result['state']} · {result['duration_seconds']:.1f} s · {result['total']} €")
                if command == "f":
                    history.save(result)
                    events.write("trip_finished", trip_id=meter.id, total=result["total"])
                    meter = None
                    print("Carrera finalizada. Puedes iniciar otra con i.")
            elif command == "h":
                rows = history.all()
                for row in rows:
                    print(f"{row['started_at']} · {row['duration_seconds']:.1f} s · {row['total']} €")
                if not rows:
                    print("Todavía no hay carreras guardadas.")
            elif command == "q":
                if meter:
                    result = meter.finish()
                    history.save(result)
                    events.write("trip_finished", trip_id=meter.id, total=result["total"])
                    print(f"Carrera finalizada al salir: {result['total']} €")
                print("Hasta pronto.")
                break
            else:
                print("Comando desconocido. Escribe a para ver la ayuda.")
        except (ValueError, OSError) as error:
            events.write("error", message=str(error))
            print(f"Aviso: {error}")
