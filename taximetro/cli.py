"""Interfaz de terminal de la fase 1."""

from .domain import Taximeter

HELP = """
TAXITECH · Taxímetro digital
Tarifas: parado 0,02 €/s · en movimiento 0,05 €/s.
i = iniciar · p = parado · m = movimiento · e = estado
f = finalizar · a = ayuda · q = salir
El tiempo se cobra continuamente, aunque no escribas comandos.
Cada carrera empieza en estado parado. Pulsa Enter después del comando.
"""


def run():
    print(HELP)
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
                meter = Taximeter()
                print("Carrera iniciada. Taxi parado.")
            elif command in ("p", "m", "e", "f"):
                if not meter:
                    raise ValueError("Primero inicia una carrera con i.")
                if command in ("p", "m"):
                    meter.change_state("stopped" if command == "p" else "moving")
                result = meter.finish() if command == "f" else meter.snapshot()
                print(f"{result['state']} · {result['duration_seconds']:.1f} s · {result['total']} €")
                if command == "f":
                    meter = None
                    print("Carrera finalizada. Puedes iniciar otra con i.")
            elif command == "q":
                if meter:
                    print(f"Carrera finalizada al salir: {meter.finish()['total']} €")
                print("Hasta pronto.")
                break
            else:
                print("Comando desconocido. Escribe a para ver la ayuda.")
        except ValueError as error:
            print(f"Aviso: {error}")
