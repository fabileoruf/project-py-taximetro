"""Interfaz web y API; las reglas del taxímetro viven en MeterService."""

from datetime import timedelta
import os
from pathlib import Path
import secrets
from threading import Lock
import time

from flask import Flask, jsonify, redirect, render_template, request, session
from werkzeug.exceptions import HTTPException

from .config import ROOT
from .events import EventLog
from .security import load_credentials, verify
from .service import Conflict, MeterService
from .storage import JsonHistory


def create_app(directory=None, service=None):
    directory = Path(directory or os.environ.get("TAXIMETRO_DATA", ROOT / "data"))
    credentials = load_credentials(directory)
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=credentials["session_secret"], MAX_CONTENT_LENGTH=4096,
        SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Strict",
        SESSION_COOKIE_SECURE=os.environ.get("TAXIMETRO_HTTPS") == "1",
        PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
    )
    events = EventLog(directory)
    service = service or MeterService(JsonHistory(directory), events,
                                     os.environ.get("TAXIMETRO_CONFIG", ROOT / "config.json"))
    app.extensions["meter_service"] = service
    failures = {}
    login_lock = Lock()

    def csrf():
        if "csrf" not in session:
            session["csrf"] = secrets.token_hex(32)
        return session["csrf"]

    @app.before_request
    def protect():
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            submitted = request.headers.get("X-CSRF-Token") or request.form.get("csrf", "")
            if not secrets.compare_digest(str(submitted).encode(), csrf().encode()):
                return jsonify(error="La sesión ha cambiado. Recarga la página."), 403
        if request.path.startswith("/api/") and request.path not in ("/api/csrf", "/api/login"):
            if not session.get("authenticated"):
                return jsonify(error="Inicia sesión para continuar."), 401

    @app.after_request
    def response_headers(response):
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' data:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        )
        return response

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    @app.get("/api/csrf")
    def api_csrf():
        return jsonify(csrf=csrf())

    @app.route("/login", methods=["GET", "POST"])
    @app.post("/api/login")
    def login():
        if request.method == "GET":
            if session.get("authenticated"):
                return redirect("/")
            return render_template("login.html", csrf=csrf(), error=None)
        payload = request.get_json(silent=True) if request.is_json else request.form
        password = payload.get("password", "") if hasattr(payload, "get") else ""
        address = request.remote_addr or "local"
        now = time.monotonic()
        with login_lock:
            # Ventana limitada y limpieza para no acumular direcciones indefinidamente.
            for ip in list(failures):
                if now - failures[ip][0] >= 60:
                    del failures[ip]
            count = failures.get(address, (now, 0))[1]
            if count >= 5 or len(failures) >= 256:
                message, status = "Demasiados intentos. Espera un minuto.", 429
            elif verify(credentials, password):
                failures.pop(address, None)
                session.clear()
                session["authenticated"] = True
                session.permanent = True
                events.write("login_success")
                token = csrf()
                return jsonify(csrf=token) if request.is_json else redirect("/")
            else:
                first = failures.get(address, (now, 0))[0]
                failures[address] = (first, count + 1)
                events.write("login_failed")
                message, status = "Contraseña incorrecta.", 401
        if request.is_json:
            return jsonify(error=message), status
        return render_template("login.html", csrf=csrf(), error=message), status

    @app.post("/api/logout")
    def logout():
        session.clear()
        return jsonify(ok=True)

    @app.get("/")
    def dashboard():
        if not session.get("authenticated"):
            return redirect("/login")
        return render_template("dashboard.html", csrf=csrf())

    @app.get("/api/status")
    def status():
        return jsonify(service.status())

    @app.get("/api/trips")
    def history():
        return jsonify(trips=service.history(request.args.get("date")))

    @app.post("/api/trips")
    def start():
        return jsonify(trip=service.start()), 201

    @app.patch("/api/trips/current")
    def change():
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict) or payload.get("state") not in ("stopped", "moving"):
            raise ValueError("El estado debe ser stopped o moving.")
        return jsonify(trip=service.change(payload["state"]))

    @app.post("/api/trips/current/finish")
    def finish():
        return jsonify(trip=service.finish())

    @app.errorhandler(Conflict)
    def conflict(error):
        events.write("command_rejected", message=str(error))
        return jsonify(error=str(error)), 409

    @app.errorhandler(ValueError)
    def invalid(error):
        events.write("validation_error", message=str(error))
        return jsonify(error=str(error)), 400

    @app.errorhandler(Exception)
    def unexpected(error):
        if isinstance(error, HTTPException):
            return jsonify(error=error.description), error.code
        events.write("error", error_type=type(error).__name__)
        app.logger.exception("Error de aplicación")
        return jsonify(error="No se pudo completar la operación. Revisa el registro y vuelve a intentarlo."), 503

    return app
