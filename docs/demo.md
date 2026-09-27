# Guion de demostración en directo

Duración orientativa: 4–5 minutos. Usa datos de prueba.

1. **Presentación (30 s).** Explica que es un taxímetro en Python, desarrollado en
   cuatro fases. Muestra las etiquetas `fase-1` a `fase-4` y el tablero.
2. **Arranque (30 s).** Ejecuta `python3 iniciar.py`. Explica que crea el entorno
   y pide una contraseña al primer uso. Abre http://127.0.0.1:8080 e inicia sesión.
3. **Carrera (1 min).** Pulsa Iniciar, espera unos segundos en Parado y cambia a
   En movimiento. Explica las tarifas por segundo. Finaliza y señala el recibo.
   Inicia otra carrera para mostrar que no hay que cerrar el programa.
4. **Historial (30 s).** Finaliza la segunda carrera, muestra ambas y el total del
   día. Filtra una fecha sin resultados y vuelve a Ver todas.
5. **Configuración y persistencia (1 min).** Enseña `config.json`, explica que
   los cambios se aplican a nuevas carreras y reinicia el servidor con las
   carreras finalizadas. Comprueba que el historial sigue presente.
6. **Pruebas y decisiones (30 s).** Ejecuta los tests. Explica Decimal, reloj
   monotónico, separación entre interfaz y servicio, SQLite y contraseña con hash.
7. **Cierre.** Abre la memoria PDF y señala las instrucciones de ejecución y los
   límites: un vehículo, acceso compartido y uso educativo.

## Preguntas que conviene saber responder

- **¿Por qué 60 s parado y 120 s en movimiento cuestan 7,20 €?**
  Porque `60 × 0,02 + 120 × 0,05 = 1,20 + 6,00`.
- **¿Por qué no se suma un importe cada vez que la pantalla refresca?**
  Se mide el tiempo real de cada tramo. Refrescar no modifica ni redondea el cálculo.
- **¿Por qué usar Decimal?** Para tratar las tarifas y el redondeo decimal con precisión.
- **¿Qué pasa si se cierra el navegador?** El servidor sigue contando; la carrera
  se finaliza con el botón, no al cerrar la ventana.
- **¿Qué pasa si se apaga el servidor?** Se recupera el último registro como carrera
  interrumpida y se avisa al conductor; no se cobra el tiempo apagado.
- **¿Hace falta Docker?** No. `python3 iniciar.py` es el camino principal.
- **¿Qué parte es Python?** Toda la lógica, la API, la base de datos, el acceso y el
  arranque. HTML, CSS y JavaScript presentan la pantalla en el navegador.
