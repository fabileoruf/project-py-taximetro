"""Entradas de la aplicación: setup, cli y web."""

import argparse
from getpass import getpass
import os
from pathlib import Path

from .config import ROOT
from .lease import application_lock
from .security import load_credentials, setup, verify


def main():
    parser = argparse.ArgumentParser(description="TaxiTech · Taxímetro digital")
    parser.add_argument("command", choices=("setup", "cli", "web"), nargs="?", default="web")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    directory = Path(os.environ.get("TAXIMETRO_DATA", ROOT / "data"))
    try:
        with application_lock(directory):
            if args.command == "setup":
                setup(directory)
                return
            credentials = load_credentials(directory)
            if args.command == "cli":
                if not verify(credentials, getpass("Contraseña: ")):
                    raise ValueError("Contraseña incorrecta.")
                from .cli import run
                run()
            else:
                from waitress import serve
                from .web import create_app
                app = create_app(directory)
                print(f"TaxiTech disponible en http://{args.host}:{args.port}", flush=True)
                serve(app, host=args.host, port=args.port, threads=4)
    except (ValueError, OSError) as error:
        parser.exit(1, f"Error: {error}\n")


if __name__ == "__main__":
    main()
