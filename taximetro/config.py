"""Configuración externa, validada al empezar cada carrera."""

from decimal import Decimal, InvalidOperation
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_rates(path=ROOT / "config.json"):
    from .domain import Rates
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return Rates(Decimal(str(data["stopped"])), Decimal(str(data["moving"])))
    except (OSError, ValueError, KeyError, TypeError, InvalidOperation) as error:
        raise ValueError("Configuración de tarifas inválida. Revisa config.json.") from error
