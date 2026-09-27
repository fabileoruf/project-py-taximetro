# API: ejemplo desde Python

Con la aplicación ejecutándose, este ejemplo utiliza únicamente la biblioteca
estándar. Pide la contraseña sin escribirla en el código ni en el historial del shell.

```python
from getpass import getpass
from http.cookiejar import CookieJar
import json
import time
from urllib.request import build_opener, HTTPCookieProcessor, Request

base = "http://127.0.0.1:8080"
client = build_opener(HTTPCookieProcessor(CookieJar()))
token = None

def api(path, method="GET", data=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["X-CSRF-Token"] = token
    body = json.dumps(data or {}).encode() if method != "GET" else None
    request = Request(base + path, data=body, headers=headers, method=method)
    with client.open(request, timeout=10) as response:
        return json.load(response)

token = api("/api/csrf")["csrf"]
token = api("/api/login", "POST", {"password": getpass("Contraseña: ")})["csrf"]
print(api("/api/trips", "POST"))
time.sleep(2)
print(api("/api/trips/current", "PATCH", {"state": "moving"}))
time.sleep(2)
print(api("/api/trips/current/finish", "POST"))
print(api("/api/trips"))
api("/api/logout", "POST")
```

La API usa la misma sesión que la interfaz. El cliente debe conservar las cookies
y actualizar el token CSRF después de entrar. No debe iniciar automáticamente
otra carrera al reintentar una petición: primero consulta `/api/status`.

Una segunda petición de finalizar cuando ya no hay carrera devuelve `409`.
El importe de una carrera finalizada se guarda una sola vez por ID.
