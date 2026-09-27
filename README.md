# TaxiTech · Taxímetro digital en Python

Proyecto educativo de **Fabiana Leonardo**, desarrollado en cuatro fases para Factoría F5.

- [Repositorio](https://github.com/fabileoruf/project-py-taximetro)
- [Kanban por fases](https://github.com/users/fabileoruf/projects/3)
- [Memoria en PDF](docs/memoria-taximetro.pdf)
- [Guion de demostración](docs/demo.md)
- [Enunciado de referencia](https://github.com/Factoria-F5-madrid/project-py-taximetro)

![Taxímetro en funcionamiento, con datos de prueba](docs/images/carrera.png)

## Empezar con un comando

Necesitas **Python 3.11 o posterior**, en macOS o Linux, y acceso a Internet
para instalar las dependencias la primera vez. Desde esta carpeta:

```sh
python3 iniciar.py
```

El lanzador prepara `.venv`, instala las dependencias, te pide crear una
contraseña la primera vez y arranca el servidor. Abre **http://127.0.0.1:8080**.
La contraseña se escribe en el terminal sin mostrarse; elige al menos 10
caracteres. No hay una contraseña predefinida. Para parar, pulsa `Ctrl+C`.

Para la interfaz de terminal:

```sh
python3 iniciar.py cli
```

Docker es una alternativa opcional; **no hace falta para ejecutar ni presentar el proyecto**.

## Uso del taxímetro

1. Inicia una carrera: comienza en **parado**, a 0,02 €/s.
2. Cambia a **en movimiento**, a 0,05 €/s; puedes alternar cuantas veces necesites.
3. Finaliza para ver el total, guardar la carrera y comenzar la siguiente.
4. Consulta el historial por fecha de Madrid o pulsa **Ver todas**.

El tiempo sigue contando aunque no pulses botones. Cerrar el navegador o cerrar
sesión no termina una carrera; hay que usar **Finalizar carrera**.

En terminal: `i` iniciar, `p` parado, `m` movimiento, `e` consultar, `f` finalizar,
`h` historial, `a` ayuda, `q` salir. Pulsa Enter después del comando.
Salir del terminal con `q`, EOF o Ctrl+C finaliza y guarda la carrera activa.

**Ejemplo:** 60 segundos parado + 120 segundos en movimiento = **7,20 €**.
Las tarifas son las del ejercicio, no una referencia de tarifas reales.

## Las cuatro fases

Cada etiqueta conserva una versión funcional de esa etapa. La rama `main`
contiene la versión completa.

| Fase | Etiqueta Git | Entrega |
|---|---|---|
| 1 | `fase-1` | Terminal, inicio, cambio de estado, precio y carreras consecutivas. |
| 2 | `fase-2` | Historial JSONL, logs, tarifas externas y pruebas. |
| 3 | `fase-3` | Servicio compartido con clases, contraseña e interfaz web adaptable. |
| 4 | `fase-4` | SQLite, recuperación tras reinicio, API y arranque con un comando Python. |

Las fases 1 y 2 se ejecutan con `python3 taximeter.py`, sin dependencias externas.
En la fase 3, instala `requirements.txt`, ejecuta `python -m taximetro setup`
y después `python -m taximetro web` dentro del entorno virtual.
Las etiquetas permiten revisar la evolución sin mezclar requisitos de distintas etapas.

## Arquitectura y decisiones

```text
Terminal (cli.py) ─┐
                  ├─ MeterService ─ Taximeter + Rates
Web/API (web.py) ──┘       │
                          ├─ SQLiteHistory: historial y recuperación
                          ├─ EventLog: registro estructurado
                          └─ config.json: tarifas externas
```

- **Python:** lógica del negocio, API, persistencia, autenticación y arranque.
- **Flask + Waitress:** interfaz y API con un servidor WSGI, sin modo debug.
- **HTML/CSS/JavaScript:** presentación en navegador; el precio siempre lo calcula Python.
- **SQLite:** base relacional integrada en Python, con transacciones y restricciones.
- **Decimal y reloj monotónico:** acumulación precisa por tramos, sin depender de ajustes del reloj del sistema.
- **scrypt:** hash con sal para la contraseña; sesiones firmadas, CSRF y límite de intentos.

Un único proceso gestiona un taxímetro. Un bloqueo por carpeta impide arrancar
simultáneamente dos instancias contra los mismos datos. Un bloqueo interno
serializa las operaciones cuando llegan peticiones concurrentes.

## Configuración y datos

Edita `config.json` para cambiar tarifas sin tocar código:

```json
{"stopped": "0.02", "moving": "0.05"}
```

Las nuevas tarifas se aplican a la siguiente carrera. Una carrera activa conserva
las iniciales. Los valores deben ser positivos y finitos.

| Archivo en `data/` | Contenido |
|---|---|
| `taximetro.sqlite3` | Historial relacional y último registro de la carrera activa. |
| `operations.jsonl` | Arranques, cambios de estado, cierres, accesos y errores; tiene rotación. |
| `credentials.json` | Hash de contraseña y clave de sesión; permisos `0600`. |
| `.app.lock` | Evita dos procesos sobre la misma carpeta. |

`data/` y `.venv/` están excluidos de Git. Puedes cambiar la carpeta con
`TAXIMETRO_DATA` y el archivo de tarifas con `TAXIMETRO_CONFIG`.
Si existe el historial JSONL de la fase 2, se importa a SQLite sin duplicarlo.

Después de un cierre inesperado, la carrera activa se registra como
**interrumpida** hasta su último punto guardado. No se cobra el tiempo en que
el servidor estuvo apagado. Se guarda al iniciar, cambiar de estado y consultar
el contador; con la pantalla abierta, se consulta aproximadamente cada 0,7 s.
Si no hay consultas, el punto guardado puede ser anterior al cierre. La interfaz
avisa para que el conductor revise el importe antes de cobrar.

## API REST

Las operaciones de negocio requieren sesión. Las modificaciones también requieren
el token `X-CSRF-Token`. Ejemplo reproducible en [docs/api.md](docs/api.md).

| Método | Ruta | Función |
|---|---|---|
| GET | `/health` | Estado del servidor, sin datos privados. |
| GET | `/api/csrf` | Obtener token CSRF y cookie de sesión. |
| POST | `/api/login` | Entrar con contraseña; devuelve un token CSRF renovado. |
| POST | `/api/logout` | Cerrar sesión. |
| GET | `/api/status` | Carrera activa, tarifas y resumen del día. |
| POST | `/api/trips` | Iniciar carrera. |
| PATCH | `/api/trips/current` | Cambiar estado: `stopped` o `moving`. |
| POST | `/api/trips/current/finish` | Finalizar y guardar. |
| GET | `/api/trips?date=2026-09-27` | Historial; la fecha es opcional. |

Los importes se devuelven como cadenas decimales. Respuestas de error:
`400` datos inválidos, `401` sesión necesaria, `403` CSRF inválido,
`409` operación incompatible, `429` demasiados intentos y `503` fallo operativo.

## Pruebas

```sh
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python tests/native_check.py
```

Para probar también el navegador y regenerar las capturas:

```sh
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m playwright install chromium
.venv/bin/python tests/browser_check.py
```

Se comprueban cálculos, redondeo, persistencia, migración, concurrencia,
recuperación, autenticación, CSRF y flujo de usuario. El navegador se verifica a
1440, 768 y 390 píxeles, incluyendo desconexión y reconexión. Los datos de las
capturas son de prueba y nunca se añaden al historial personal.

GitHub Actions ejecuta las pruebas de Python y navegador en cada push.

## Tablet y alternativa Docker

Para abrir la aplicación desde una tablet en tu red local:

```sh
python3 iniciar.py web --host 0.0.0.0
```

En la tablet, abre `http://IP-DEL-ORDENADOR:8080`. El ordenador debe permanecer
encendido. Para una instalación expuesta a Internet, hace falta configurar HTTPS
con un proxy y activar `TAXIMETRO_HTTPS=1`; esa infraestructura no forma parte de
esta entrega local.

Si prefieres Docker y ya lo tienes instalado:

```sh
./start-docker.sh
```

Crea la contraseña al primer arranque. Los datos se conservan en el volumen
`taxi-data`, separado de `data/` de la ejecución nativa. `docker compose down`
para el servicio sin borrar el volumen. La imagen se ejecuta con usuario no root.
Docker no es un requisito del enunciado; el arranque principal es `iniciar.py`.

## Entrega y límites

Consulta [docs/entrega.md](docs/entrega.md) para el texto del campus y
[docs/demo.md](docs/demo.md) para preparar la demostración en directo.

Este es un prototipo educativo para **un vehículo y un acceso compartido**.
No incluye GPS, facturación fiscal, múltiples vehículos ni homologación.
El repositorio y el tablero se crearon privados: para entregar sus enlaces,
hay que hacerlos accesibles al profesor (invitación o cambio de visibilidad).
