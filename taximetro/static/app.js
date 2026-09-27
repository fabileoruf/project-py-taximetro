"use strict";
const $ = (id) => document.getElementById(id);
const csrf = document.querySelector('meta[name="csrf-token"]').content;
let current = null;
let online = false;
let busy = false;
let dateSelected = false;
let lastTripId = undefined;
const euros = (value) => Number(value).toLocaleString("es-ES", {minimumFractionDigits: 2, maximumFractionDigits: 2});
const duration = (value) => {
  const seconds = Math.floor(value);
  const minutes = Math.floor(seconds / 60);
  return `${String(minutes).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
};

async function api(path, method = "GET", data) {
  const response = await fetch(path, {
    method, headers: {"Content-Type": "application/json", "X-CSRF-Token": csrf},
    body: data === undefined ? undefined : JSON.stringify(data),
    signal: AbortSignal.timeout(7000),
  });
  if (response.status === 401) { window.location.assign("/login"); throw new Error("Sesión caducada."); }
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || "No se pudo completar la operación.");
  return result;
}

function showError(message) { $("error").textContent = message; $("error").hidden = !message; }
function controls() {
  const active = Boolean(current?.active);
  $("start").hidden = active;
  $("finish").hidden = !active;
  $("start").disabled = busy || !online;
  $("finish").disabled = busy || !online;
  for (const state of ["stopped", "moving"]) {
    $(state).disabled = busy || !online || !active;
    $(state).setAttribute("aria-pressed", String(active && current.active.state === state));
  }
}

function render(data) {
  current = data;
  const trip = data.active;
  $("fare").textContent = euros(trip?.total || 0);
  $("duration").textContent = duration(trip?.duration_seconds || 0);
  $("current-rate").textContent = trip ? `${euros(trip.rates[trip.state])} €/s` : "— €/s";
  $("state-badge").textContent = trip ? (trip.state === "stopped" ? "PARADO" : "EN MOVIMIENTO") : "DISPONIBLE";
  $("state-badge").classList.toggle("active", Boolean(trip));
  $("meter-hint").textContent = trip ? "El contador sigue activo hasta que finalices la carrera." : "La carrera comienza en parado. Cambia el estado mientras conduces.";
  $("total-today").textContent = euros(data.total_today);
  $("trips-today").textContent = data.trips_today;
  $("stopped-rate").textContent = euros(data.rates.stopped);
  $("moving-rate").textContent = euros(data.rates.moving);
  $("today").textContent = new Date(`${data.today}T12:00:00`).toLocaleDateString("es-ES", {weekday: "long", day: "numeric", month: "long"});
  if (!dateSelected) { $("history-date").value = data.today; dateSelected = true; }
  controls();
}

async function refreshHistory() {
  const day = $("history-date").value;
  const data = await api(`/api/trips${day ? `?date=${encodeURIComponent(day)}` : ""}`);
  const body = $("history-body");
  body.replaceChildren();
  for (const trip of data.trips) {
    const row = document.createElement("tr");
    const values = [
      `#${trip.id.slice(0, 8).toUpperCase()}`,
      new Date(trip.started_at).toLocaleString("es-ES", {timeZone: "Europe/Madrid", day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit"}),
      duration(trip.duration_seconds),
      trip.status === "interrupted" ? "Interrumpida" : "Finalizada",
      `${euros(trip.total)} €`,
    ];
    values.forEach((value, index) => {
      const cell = document.createElement("td");
      if (index === 3) {
        const badge = document.createElement("span");
        badge.className = `trip-badge${trip.status === "interrupted" ? " interrupted" : ""}`;
        badge.textContent = value;
        cell.append(badge);
      } else { cell.textContent = value; }
      if (index === 4) cell.className = "align-right";
      row.append(cell);
    });
    body.append(row);
  }
  $("empty-history").hidden = data.trips.length > 0;
}

async function refresh() {
  const wasOnline = online;
  const data = await api("/api/status");
  online = true;
  $("connection").textContent = "Sistema conectado";
  $("connection").parentElement.classList.remove("offline");
  render(data);
  const nextId = data.active?.id || null;
  if (!wasOnline || lastTripId !== nextId) await refreshHistory();
  lastTripId = nextId;
  if (!wasOnline) showError("");
}

async function action(path, method, payload) {
  if (busy || !online) return;
  busy = true;
  controls();
  showError("");
  try {
    const result = await api(path, method, payload);
    if (path.endsWith("/finish")) {
      $("receipt").textContent = `Carrera finalizada · ${duration(result.trip.duration_seconds)} · Total a cobrar: ${euros(result.trip.total)} €. Guardada en el historial.`;
      $("receipt").hidden = false;
    } else if (method === "POST") { $("receipt").hidden = true; }
    await refresh();
    await refreshHistory();
  } catch (error) { showError(error.message); }
  finally { busy = false; controls(); }
}

$("start").addEventListener("click", () => action("/api/trips", "POST"));
$("finish").addEventListener("click", () => action("/api/trips/current/finish", "POST"));
$("stopped").addEventListener("click", () => action("/api/trips/current", "PATCH", {state: "stopped"}));
$("moving").addEventListener("click", () => action("/api/trips/current", "PATCH", {state: "moving"}));
$("history-date").addEventListener("change", () => refreshHistory().catch((error) => showError(error.message)));
$("all-trips").addEventListener("click", () => { $("history-date").value = ""; refreshHistory().catch((error) => showError(error.message)); });
$("logout").addEventListener("click", async () => {
  try { await api("/api/logout", "POST"); window.location.assign("/login"); }
  catch (error) { showError(error.message); }
});

async function poll() {
  if (!busy) {
    try { await refresh(); }
    catch (error) {
      online = false;
      $("connection").textContent = "Sin conexión";
      $("connection").parentElement.classList.add("offline");
      showError(`No se puede actualizar el contador. ${error.message} Si hay una carrera activa, el servidor sigue contando; reconecta para finalizarla.`);
      controls();
    }
  }
  window.setTimeout(poll, 700);
}
poll();
