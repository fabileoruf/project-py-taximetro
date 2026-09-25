# TaxiTech · Taxímetro digital

Proyecto educativo en Python de Fabiana Leonardo.

Enunciado: https://github.com/Factoria-F5-madrid/project-py-taximetro

## Fase 1 — Terminal

Requiere Python 3.11 o posterior. Ejecutar desde esta carpeta:

```sh
python3 taximeter.py
python3 -m unittest discover -s tests -v
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

Las tarifas son datos del ejercicio; este prototipo no es un taxímetro homologado.
