"""Interfaz de terminal sobre los mismos casos de uso de la interfaz web."""

import os
from pathlib import Path

from .config import ROOT
from .events import EventLog
from .service import MeterService
from .database import SQLiteHistory
import sqlite3

HELP = """
TAXITECH · Taxímetro digital
Tarifas cargadas desde config.json al iniciar cada carrera.
i = iniciar · p = parado · m = movimiento · e = estado
f = finalizar · h = historial · a = ayuda · q = salir
El tiempo se cobra continuamente, aunque no escribas comandos.
Cada carrera empieza en estado parado. Pulsa Enter después del comando.
"""


def display(trip):
    state = "parado" if trip["state"] == "stopped" else "en movimiento"
    print(f"{state} · {trip['duration_seconds']:.1f} s · {trip['total']} €")


def run():
    print(HELP)
    directory = Path(os.environ.get("TAXIMETRO_DATA", ROOT / "data"))
    events = EventLog(directory)
    service = MeterService(SQLiteHistory(directory), events,
                           os.environ.get("TAXIMETRO_CONFIG", ROOT / "config.json"))
    if service.recovered:
        print("Se ha recuperado una carrera interrumpida hasta su último registro. Consulta h.")
    while True:
        try:
            command = input("taxi> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            command = "q"
        try:
            if command == "a":
                print(HELP)
            elif command == "i":
                trip = service.start()
                print(f"Carrera iniciada. Parado: {trip['rates']['stopped']} €/s; movimiento: {trip['rates']['moving']} €/s.")
            elif command in ("p", "m"):
                display(service.change("stopped" if command == "p" else "moving"))
            elif command == "e":
                trip = service.status()["active"]
                if trip:
                    display(trip)
                else:
                    print("No hay ninguna carrera activa. Inicia una con i.")
            elif command == "f":
                display(service.finish())
                print("Carrera finalizada y guardada. Puedes iniciar otra con i.")
            elif command == "h":
                rows = service.history()
                for row in rows:
                    print(f"{row['started_at']} · {row['duration_seconds']:.1f} s · {row['total']} €")
                if not rows:
                    print("Todavía no hay carreras guardadas.")
            elif command == "q":
                if service.meter:
                    print(f"Carrera finalizada al salir: {service.finish()['total']} €")
                print("Hasta pronto.")
                break
            else:
                print("Comando desconocido. Escribe a para ver la ayuda.")
        except (ValueError, OSError, sqlite3.Error) as error:
            events.write("error", message=str(error))
            print(f"Aviso: {error}")
            if command == "q":
                raise
