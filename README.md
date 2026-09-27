# TaxiTech · Taxímetro digital

Proyecto educativo en Python de Fabiana Leonardo.

Enunciado: https://github.com/Factoria-F5-madrid/project-py-taximetro

## Fase 1 — Terminal

Requiere Python 3.11 o posterior en macOS/Linux (o Docker). La versión actual
incluye las fases posteriores; prepara el acceso antes de ejecutar el terminal:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m taximetro setup
.venv/bin/python taximeter.py
.venv/bin/python -m unittest discover -s tests -v
```

Usa `i` para iniciar; `p` para parado; `m` para movimiento; `e` para consultar;
`f` para finalizar y `q` para salir. Pulsa Enter después de cada comando.
Se pueden encadenar carreras. Salir finaliza la carrera activa.

Tarifas del ejercicio: 0,02 €/s parado y 0,05 €/s en movimiento.
La carrera empieza parada. El reloj monotónico mide el tiempo real entre
comandos; consultar el precio no cambia el cálculo. Se redondea a céntimos
al presentar el total, sin redondear cada tramo.

Ejemplo: 60 s parado + 120 s en movimiento = 1,20 € + 6,00 € = 7,20 €.

## Plan de entrega

- Fase 1: terminal y cálculo por tramos.
- Fase 2: historial persistente, logs, tarifas externas y pruebas.
- Fase 3: separación de responsabilidades, contraseña e interfaz táctil.
- Fase 4: SQLite, API REST, panel web y despliegue con un comando.

## Fase 2 — Persistencia y configuración

`h` muestra el historial. Las carreras se guardan en `data/history.jsonl` y
los eventos en `data/operations.jsonl`, con rotación. `TAXIMETRO_DATA` permite
elegir otra carpeta. `data/` no se sube al repositorio.

Modifica `config.json` para cambiar tarifas sin tocar código. Se aplican a
la siguiente carrera; una carrera activa conserva las tarifas iniciales.
Si el archivo es inválido, se informa del error y no comienza la carrera.

## Fase 3 — Acceso e interfaz táctil

```sh
.venv/bin/python -m taximetro web
```

Abre http://127.0.0.1:8080 y entra con la contraseña creada en `setup`.
El terminal también exige esa contraseña. Se guarda un hash scrypt con sal,
nunca la contraseña, en `data/credentials.json`, con permisos de lectura
restringidos. El archivo incluye la clave aleatoria que firma las sesiones.

La pantalla permite iniciar, cambiar estado y finalizar; actualiza el contador
sin bloquear los botones y presenta el historial por fecha de Madrid.
Se protegen las operaciones con sesión y CSRF; cinco intentos de acceso
fallidos bloquean nuevos intentos de esa dirección durante un minuto.

Responsabilidades: `domain.py` calcula; `service.py` coordina; `storage.py`
persiste; `security.py` autentica; `web.py` y `cli.py` presentan la aplicación.
Sólo se permite un proceso por carpeta de datos para evitar dos contadores.

Las tarifas son datos del ejercicio; este prototipo no es un taxímetro homologado.
