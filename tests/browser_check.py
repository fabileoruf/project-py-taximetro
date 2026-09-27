"""Prueba real de navegador con datos temporales y reloj controlado.

Ejecutar: .venv/bin/python tests/browser_check.py
"""

from pathlib import Path
import secrets
import sys
import tempfile
from threading import Thread

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from playwright.sync_api import sync_playwright, expect
from werkzeug.serving import make_server

from taximetro.domain import Taximeter
from taximetro.events import EventLog
from taximetro.security import create_credentials
from taximetro.service import MeterService
from taximetro.storage import JsonHistory
from taximetro.web import create_app
from test_domain import Clock


def run():
    screenshots = Path(__file__).resolve().parent.parent / "docs" / "images"
    screenshots.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as directory:
        password = secrets.token_urlsafe(20)
        create_credentials(directory, password)
        clock = Clock()
        service = MeterService(JsonHistory(directory), EventLog(directory),
                                factory=lambda rates: Taximeter(rates, clock))
        server = make_server("127.0.0.1", 0, create_app(directory, service), threaded=True)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                context = browser.new_context(viewport={"width": 1440, "height": 1080})
                page = context.new_page()
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(f"http://127.0.0.1:{server.server_port}")
                page.screenshot(path=str(screenshots / "acceso.png"), full_page=True)
                page.get_by_label("Contraseña", exact=True).fill(password)
                page.get_by_role("button", name="Entrar al taxímetro").click()
                expect(page.get_by_role("button", name="Iniciar carrera")).to_be_enabled()
                page.screenshot(path=str(screenshots / "panel.png"), full_page=True)
                page.get_by_role("button", name="Iniciar carrera").click()
                expect(page.locator("#state-badge")).to_have_text("PARADO")
                clock.advance(60)
                expect(page.locator("#fare")).to_have_text("1,20")
                page.get_by_role("button", name="En movimiento").click()
                expect(page.locator("#state-badge")).to_have_text("EN MOVIMIENTO")
                clock.advance(120)
                expect(page.locator("#fare")).to_have_text("7,20")
                page.screenshot(path=str(screenshots / "carrera.png"), full_page=True)
                page.get_by_role("button", name="Finalizar carrera").click()
                expect(page.locator("#receipt")).to_contain_text("7,20 €")
                expect(page.locator("#history-body tr")).to_have_count(1)
                page.get_by_role("button", name="Iniciar carrera").click()
                expect(page.locator("#state-badge")).to_have_text("PARADO")
                clock.advance(30)
                page.get_by_role("button", name="Finalizar carrera").click()
                expect(page.locator("#history-body tr")).to_have_count(2)
                expect(page.locator("#total-today")).to_have_text("7,80")
                page.screenshot(path=str(screenshots / "historial.png"), full_page=True)
                page.locator("#history-date").fill("2000-01-01")
                page.locator("#history-date").dispatch_event("change")
                expect(page.locator("#history-body tr")).to_have_count(0)
                page.get_by_role("button", name="Ver todas").click()
                expect(page.locator("#history-body tr")).to_have_count(2)
                for width, height, name in ((768, 1024, "tablet"), (390, 844, "movil")):
                    page.set_viewport_size({"width": width, "height": height})
                    page.screenshot(path=str(screenshots / f"{name}.png"), full_page=True)
                    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), name
                context.set_offline(True)
                expect(page.locator("#connection")).to_have_text("Sin conexión", timeout=10000)
                expect(page.locator("#start")).to_be_disabled()
                context.set_offline(False)
                expect(page.locator("#connection")).to_have_text("Sistema conectado", timeout=10000)
                page.get_by_role("button", name="Cerrar sesión").click()
                expect(page.get_by_role("button", name="Entrar al taxímetro")).to_be_visible()
                assert not errors, errors
                browser.close()
                print("PASS: acceso, carrera mixta, nueva carrera, historial, filtros, tablet, móvil, desconexión y cierre de sesión.")
        finally:
            server.shutdown()
            thread.join(timeout=5)


if __name__ == "__main__":
    run()
