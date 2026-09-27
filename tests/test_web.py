import json
from pathlib import Path
import tempfile
import unittest

from taximetro.events import EventLog
from taximetro.security import create_credentials
from taximetro.service import MeterService
from taximetro.storage import JsonHistory
from taximetro.web import create_app
from taximetro.domain import Taximeter
from test_domain import Clock


class WebTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Hash de prueba una sola vez; no son credenciales de la aplicación real.
        with tempfile.TemporaryDirectory() as directory:
            cls.credentials = create_credentials(directory, "test-password-123")

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        (self.directory / "credentials.json").write_text(json.dumps(self.credentials))
        self.clock = Clock()
        self.service = MeterService(JsonHistory(self.directory), EventLog(self.directory),
                                    factory=lambda rates: Taximeter(rates, self.clock))
        self.app = create_app(self.directory, self.service)
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        self.csrf = self.client.get("/api/csrf").json["csrf"]

    def send(self, path, method="POST", data=None):
        return self.client.open(path, method=method, json=data,
                                headers={"X-CSRF-Token": self.csrf})

    def login(self):
        result = self.send("/api/login", data={"password": "test-password-123"})
        self.assertEqual(result.status_code, 200)
        self.csrf = result.json["csrf"]

    def test_login_required_and_csrf_enforced(self):
        self.assertEqual(self.client.get("/api/trips").status_code, 401)
        self.assertEqual(self.client.get("/").status_code, 302)
        self.login()
        self.assertEqual(self.client.post("/api/trips").status_code, 403)
        self.assertEqual(self.client.get("/").status_code, 200)

    def test_complete_trip_and_next_trip(self):
        self.login()
        self.assertEqual(self.send("/api/trips").status_code, 201)
        self.assertEqual(self.send("/api/trips").status_code, 409)
        self.clock.advance(60)
        self.assertEqual(self.send("/api/trips/current", "PATCH", {"state": "moving"}).status_code, 200)
        self.clock.advance(120)
        receipt = self.send("/api/trips/current/finish")
        self.assertEqual(receipt.json["trip"]["total"], "7.20")
        self.assertEqual(len(self.client.get("/api/trips").json["trips"]), 1)
        self.assertEqual(self.send("/api/trips/current/finish").status_code, 409)
        self.assertEqual(self.send("/api/trips").status_code, 201)

    def test_invalid_state_date_and_payloads(self):
        self.login()
        for data in ({"state": "invalid"}, [], None, {"state": []}):
            self.assertEqual(self.send("/api/trips/current", "PATCH", data).status_code, 400)
        self.assertEqual(self.client.get("/api/trips?date=bad").status_code, 400)

    def test_failed_logins_are_limited_and_password_not_logged(self):
        for _ in range(5):
            self.assertEqual(self.send("/api/login", data={"password": "wrong-secret"}).status_code, 401)
        self.assertEqual(self.send("/api/login", data={"password": "wrong-secret"}).status_code, 429)
        text = (self.directory / "operations.jsonl").read_text()
        self.assertNotIn("wrong-secret", text)

    def test_logout_invalidates_access(self):
        self.login()
        self.assertEqual(self.send("/api/logout").status_code, 200)
        self.assertEqual(self.client.get("/api/status").status_code, 401)

    def test_headers_and_cookie_flags(self):
        self.login()
        response = self.client.get("/")
        self.assertIn("frame-ancestors 'none'", response.headers["Content-Security-Policy"])
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        cookies = self.client.get("/api/csrf").headers.getlist("Set-Cookie")
        self.assertTrue(any("HttpOnly" in value and "SameSite=Strict" in value for value in cookies))
