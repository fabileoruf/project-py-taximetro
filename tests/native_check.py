"""Prueba del comando de arranque, terminal y persistencia entre procesos."""

import http.cookiejar
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
PYTHON = ROOT / ".venv" / "bin" / "python"


def run():
    with tempfile.TemporaryDirectory() as directory:
        env = {**os.environ, "TAXIMETRO_DATA": directory, "PYTHONUNBUFFERED": "1"}
        password = secrets.token_urlsafe(20)
        setup = subprocess.run([str(PYTHON), "-m", "taximetro", "setup"], cwd=ROOT, env=env,
                               input=f"{password}\n{password}\n", text=True, capture_output=True, timeout=30)
        assert setup.returncode == 0, setup.stderr
        credentials = Path(directory, "credentials.json").read_text()
        assert password not in credentials
        cli = subprocess.run([str(PYTHON), "taximeter.py"], cwd=ROOT, env=env,
                             input=f"{password}\ni\nm\np\nf\nh\nq\n", text=True, capture_output=True, timeout=30)
        assert cli.returncode == 0, cli.stderr
        assert "Carrera finalizada y guardada" in cli.stdout
        assert password not in cli.stdout + cli.stderr
        with socket.socket() as port_socket:
            port_socket.bind(("127.0.0.1", 0))
            port = port_socket.getsockname()[1]
        base = f"http://127.0.0.1:{port}"
        process = None
        log = open(Path(directory, "server.log"), "w")
        try:
            def launch():
                process = subprocess.Popen([sys.executable, "iniciar.py", "web", "--port", str(port)],
                                           cwd=ROOT, env=env, stdout=log, stderr=log)
                for _ in range(200):
                    if process.poll() is not None:
                        raise AssertionError(Path(directory, "server.log").read_text())
                    try:
                        with urllib.request.urlopen(base + "/health", timeout=1) as response:
                            if response.status == 200:
                                return process
                    except OSError:
                        time.sleep(0.1)
                process.terminate()
                process.wait(timeout=10)
                raise AssertionError("El servidor no arrancó")

            process = launch()
            opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
            csrf = None

            def request(path, method="GET", data=None):
                headers = {"Content-Type": "application/json"}
                if csrf:
                    headers["X-CSRF-Token"] = csrf
                body = json.dumps(data).encode() if data is not None else (b"{}" if method != "GET" else None)
                with opener.open(urllib.request.Request(base + path, data=body, method=method, headers=headers), timeout=10) as response:
                    return json.load(response)

            csrf = request("/api/csrf")["csrf"]
            csrf = request("/api/login", "POST", {"password": password})["csrf"]
            assert len(request("/api/trips")["trips"]) == 1
            request("/api/trips", "POST")
            time.sleep(0.3)
            receipt = request("/api/trips/current/finish", "POST")["trip"]
            request("/api/trips", "POST")
            time.sleep(0.3)
            checkpoint = request("/api/status")["active"]
            process.terminate()
            process.wait(timeout=10)
            process = launch()
            trips = request("/api/trips")["trips"]
            assert len(trips) == 3
            assert any(trip["id"] == receipt["id"] for trip in trips)
            recovered = next(trip for trip in trips if trip["id"] == checkpoint["id"])
            assert recovered["status"] == "interrupted"
            assert recovered["total"] == checkpoint["total"]
            assert request("/api/status")["active"] is None
            print("PASS: primer acceso, contraseña con hash, CLI, arranque con Python, API, reinicio e historial persistente.")
        finally:
            if process and process.poll() is None:
                process.terminate()
                process.wait(timeout=10)
            log.close()


if __name__ == "__main__":
    run()
