"""Sincroniza el catálogo local con el tablero GitHub de este proyecto.

Requiere gh autenticado. Sólo se ejecuta de forma explícita, nunca al arrancar
el taxímetro. Repetirlo actualiza los mismos títulos sin duplicar tarjetas.
"""

import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent.parent
OWNER = "fabileoruf"
NUMBER = "3"
PROJECT = "PVT_kwHOEAsJps4Bk1b7"


def gh(*arguments):
    result = subprocess.run(["gh", *arguments], check=True, text=True,
                            capture_output=True, timeout=45)
    return json.loads(result.stdout) if result.stdout.strip() else None


def main():
    fields = gh("project", "field-list", NUMBER, "--owner", OWNER, "--format", "json")["fields"]
    phase_field = next(field for field in fields if field["name"] == "Status")
    progress_field = next(field for field in fields if field["name"] == "Progreso")
    existing = gh("project", "item-list", NUMBER, "--owner", OWNER, "--limit", "100", "--format", "json")["items"]
    by_title = {item["title"]: item["id"] for item in existing}
    for task in json.loads((ROOT / "docs" / "tasks.json").read_text()):
        title = task["title"]
        if title not in by_title:
            body = (f"Fase {task['phase']} del taxímetro.\n\nEvidencia: {task['evidence']}\n\n"
                    "Repositorio: https://github.com/fabileoruf/project-py-taximetro")
            item = gh("project", "item-create", NUMBER, "--owner", OWNER, "--title", title,
                      "--body", body, "--format", "json")
            by_title[title] = item["id"]
        phase = next(option["id"] for option in phase_field["options"] if option["name"].startswith(f"Fase {task['phase']} "))
        progress = next(option["id"] for option in progress_field["options"] if option["name"] == task["progress"])
        for field_id, option in ((phase_field["id"], phase), (progress_field["id"], progress)):
            gh("project", "item-edit", "--id", by_title[title], "--project-id", PROJECT,
               "--field-id", field_id, "--single-select-option-id", option, "--format", "json")
        print(f"{title}: {task['progress']}", flush=True)
    gh("project", "link", NUMBER, "--owner", OWNER, "--repo", f"{OWNER}/project-py-taximetro")


if __name__ == "__main__":
    main()
