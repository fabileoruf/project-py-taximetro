"""Instala y ejecuta TaxiTech con un comando: python3 iniciar.py.

Sólo requiere Python 3.11+ en macOS o Linux. Docker es opcional.
"""

from pathlib import Path
import os
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parent


def main():
    if sys.version_info < (3, 11):
        raise SystemExit("Necesitas Python 3.11 o posterior.")
    os.chdir(ROOT)
    python = ROOT / ".venv" / "bin" / "python"
    if not python.exists():
        print("Preparando el entorno Python del proyecto…", flush=True)
        venv.EnvBuilder(with_pip=True).create(ROOT / ".venv")
    check = """
from importlib.metadata import version, PackageNotFoundError
from pathlib import Path
import sys
try:
    for line in Path('requirements.txt').read_text().splitlines():
        package, expected = line.split('==')
        if version(package) != expected:
            sys.exit(1)
except PackageNotFoundError:
    sys.exit(1)
"""
    if subprocess.run([str(python), "-c", check]).returncode:
        subprocess.run([str(python), "-m", "pip", "install", "-r", "requirements.txt"], check=True)
    subprocess.run([str(python), "-m", "taximetro", "setup"], check=True)
    arguments = sys.argv[1:] or ["web"]
    os.execv(str(python), [str(python), "-m", "taximetro", *arguments])


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as error:
        raise SystemExit(f"No se pudo completar la preparación (código {error.returncode}).")
