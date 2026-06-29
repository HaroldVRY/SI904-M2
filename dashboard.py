"""
dashboard.py - Panel de control web para SI904-M2
===================================================
Servidor Flask adaptado para procesamiento en la nube:
  - Recibe frames enviados por el navegador del cliente.
  - Procesa inferencias y gestiona alertas/base de datos.
"""

from __future__ import annotations

import base64
import functools
import json
import os
import queue
import threading
import time
from datetime import datetime
from typing import Any

import cv2
import numpy as np
from dotenv import load_dotenv
from flask import (Flask, Response, jsonify, redirect, render_template,
                   request, session, url_for)

load_dotenv()

# ── Validación temprana ────────────────────────────────────────────
os.environ.setdefault("ROBOFLOW_API_KEY", "")
import config  # noqa: E402

from src.alertas import GestorAlertas
from src.database import (
    cerrar_sesion, iniciar_sesion,
    registrar_alerta_whatsapp, registrar_detecciones_lote,
)
from src.detector import DetectorRoboflow
from src.utils import obtener_logger

logger = obtener_logger("Dashboard")

# ── Credenciales de autenticación ─────────────────────────────────
DASHBOARD_USER = os.getenv("DASHBOARD_USER", "admin")
DASHBOARD_PASS = os.getenv("DASHBOARD_PASS", "securevision2026")

# ── Estado global del sistema ──────────────────────────────────────
_estado = {
    "activo":             False,
    "alarma_on":          True,   # controla el envío de WhatsApp
    "modelos":            ["armas", "rostros"],
    "conf":               config.CONF_THRESHOLD,
    "cooldown":           config.COOLDOWN_SEGUNDOS,
    "intervalo":          config.INTERVALO_INFERENCIA,
    # métricas
    "frames":             0,
    "det_armas":          0,
    "det_rostros":        0,
    "det_placas":         0,
    "alertas_total":      0,
    "personas_en_pantalla": 0,
    "inicio_ts":          None,
    "sesion_bd_id":        None,
}

_alertas_historial: list[dict] = []
_lock = threading.Lock()

# SSE pub-sub: cada conexión /events recibe su propia cola
_sse_clientes:      list[queue.Queue] = []
_sse_lock_clientes  = threading.Lock()

# Limita llamadas simultáneas a Roboflow para no saturar el thread pool de Flask
_roboflow_sem = threading.Semaphore(2)

# Detectores globales para evitar re-inicialización lenta
_detector = None
_alertas = None


def _get_detector():
    global _detector
    if _detector is None:
        _detector = DetectorRoboflow()
    return _detector


def _get_alertas():
    global _alertas
    if _alertas is None:
        _alertas = GestorAlertas()
    return _alertas


def _registrar_alerta(detecciones: list[dict]) -> None:
    """Agrega la alerta al historial y la persiste en Supabase."""
    entrada = {
        "ts":    datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "items": [{"tipo": d["tipo"], "clase": d["clase"],
                   "conf": round(d["confianza"], 2)} for d in detecciones],
    }
    _alertas_historial.insert(0, entrada)
    if len(_alertas_historial) > 50:
        _alertas_historial.pop()
    _emitir_evento("alerta", entrada)

    # Persistir en Supabase
    sesion_id_bd = _estado.get("sesion_bd_id")
    to_dest = os.getenv("TWILIO_WHATSAPP_TO", "")
    registrar_alerta_whatsapp(
        sesion_id=sesion_id_bd,
        numero_destino=to_dest,
        estado="enviada",
        twilio_sid=None,
        mensaje_texto=entrada["ts"],
        detecciones_json=entrada["items"],
    )


def _emitir_evento(tipo: str, datos: dict) -> None:
    evento = {"tipo": tipo, "datos": datos}
    with _sse_lock_clientes:
        for q in _sse_clientes:
            try:
                q.put_nowait(evento)
            except queue.Full:
                pass


# ══════════════════════════════════════════════════════════════════
# Flask app
# ══════════════════════════════════════════════════════════════════

app = Flask(__name__)
app.secret_key = os.getenv("DASHBOARD_SECRET_KEY", "sv_secret_key_cambia_en_prod")
app.config['TEMPLATES_AUTO_RELOAD'] = True


def requires_auth(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("authenticated"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip()
        clave   = request.form.get("clave", "").strip()
        if usuario == DASHBOARD_USER and clave == DASHBOARD_PASS:
            session["authenticated"] = True
            session["usuario"] = usuario
            return redirect(url_for("index"))
        error = "Credenciales incorrectas. Intente nuevamente."
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@requires_auth
def index():
    return render_template("index.html", usuario=session.get("usuario", ""))


@app.route("/events")
@requires_auth
def events():
    mi_cola: queue.Queue = queue.Queue(maxsize=100)
    with _sse_lock_clientes:
        _sse_clientes.append(mi_cola)

    def stream():
        try:
            yield "data: {\"tipo\":\"conectado\"}\n\n"
            while True:
                try:
                    evento = mi_cola.get(timeout=15)
                    payload = json.dumps(evento.get("datos", evento), ensure_ascii=False)
                    yield f"event: {evento['tipo']}\ndata: {payload}\n\n"
                except queue.Empty:
                    yield ": ping\n\n"
        finally:
            with _sse_lock_clientes:
                try:
                    _sse_clientes.remove(mi_cola)
                except ValueError:
                    pass

    return Response(stream(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache",
                              "X-Accel-Buffering": "no"})


@app.route("/api/stats")
@requires_auth
def api_stats():
    with _lock:
        stats = dict(_estado)
    if stats["inicio_ts"]:
        elapsed = int(time.time() - stats["inicio_ts"])
        stats["uptime"] = f"{elapsed // 60:02d}:{elapsed % 60:02d}"
    else:
        stats["uptime"] = "00:00"
    return jsonify(stats)


@app.route("/api/alerts")
@requires_auth
def api_alerts():
    return jsonify(_alertas_historial)


# ══════════════════════════════════════════════════════════════════
# PROCESAMIENTO DE FRAMES DESDE EL CLIENTE (Nube)
# ══════════════════════════════════════════════════════════════════

@app.route("/api/process-frame", methods=["POST"])
@requires_auth
def api_process_frame():
    """
    Recibe un frame enviado por el navegador del cliente, realiza la inferencia,
    actualiza las estadísticas de la sesión, envía alertas si es necesario,
    y guarda los datos en Supabase.
    """
    if not _estado["activo"]:
        return jsonify({"error": "El sistema no está activo"}), 400

    data = request.json or {}
    img_data = data.get("imagen")
    if not img_data:
        return jsonify({"error": "No se recibió imagen"}), 400

    try:
        # Decodificar imagen base64 del cliente
        header, encoded = img_data.split(",", 1) if "," in img_data else ("", img_data)
        decoded = base64.b64decode(encoded)
        nparr = np.frombuffer(decoded, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if frame is None:
            return jsonify({"error": "Error al decodificar imagen"}), 400

        with _lock:
            _estado["frames"] += 1

        # Inferencia: si ya hay 2 llamadas Roboflow en vuelo, descarta este frame
        # para no saturar el thread pool y mantener /api/control responsivo
        detector = _get_detector()
        if not _roboflow_sem.acquire(blocking=False):
            return jsonify({"ok": True, "detecciones": []})
        try:
            detecciones = detector.inferir(frame, _estado["modelos"])
        finally:
            _roboflow_sem.release()

        # Contadores por tipo y actualización de estado
        hay_arma = False
        personas_frame = 0

        for d in detecciones:
            t = d["tipo"]
            with _lock:
                _estado[f"det_{t}"] = _estado.get(f"det_{t}", 0) + 1
            if t == "armas":
                hay_arma = True
            elif t == "rostros":
                personas_frame += 1

        with _lock:
            _estado["personas_en_pantalla"] = personas_frame

        # Registrar en Supabase (Lote)
        sesion_id_bd = _estado.get("sesion_bd_id")
        if detecciones:
            registrar_detecciones_lote(
                sesion_id_bd, detecciones, disparo_alerta=hay_arma
            )

        # Alerta de panel: cualquier detección dispara el registro (respetando cooldown)
        # WhatsApp: solo cuando hay arma Y la alarma está activada
        if detecciones:
            alertas_obj = _get_alertas()
            enviar_wp   = hay_arma and _estado.get("alarma_on", True)
            if alertas_obj.disparar(frame, detecciones, enviar_whatsapp=enviar_wp):
                with _lock:
                    _estado["alertas_total"] += 1
                _registrar_alerta(detecciones)

        return jsonify({
            "ok": True,
            "detecciones": [
                {
                    "tipo":      d["tipo"],
                    "clase":     d["clase"],
                    "confianza": round(d["confianza"], 3),
                    "x1":        d["x1"],
                    "y1":        d["y1"],
                    "x2":        d["x2"],
                    "y2":        d["y2"]
                }
                for d in detecciones
            ]
        })

    except Exception as e:
        logger.error(f"Error procesando frame del cliente: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/test-image", methods=["POST"])
@requires_auth
def api_test_image():
    """Recibe una imagen subida por el usuario para testing."""
    if "imagen" not in request.files:
        return jsonify({"error": "No se recibió ninguna imagen"}), 400

    modelos_req = request.form.get("modelos", "armas,rostros,placas").split(",")
    modelos_req = [m.strip() for m in modelos_req if m.strip()]
    conf_req    = float(request.form.get("conf", config.CONF_THRESHOLD))

    archivo = request.files["imagen"]
    datos   = np.frombuffer(archivo.read(), dtype=np.uint8)
    frame   = cv2.imdecode(datos, cv2.IMREAD_COLOR)
    if frame is None:
        return jsonify({"error": "No se pudo decodificar la imagen"}), 400

    h, w = frame.shape[:2]
    if max(h, w) > 1280:
        scale = 1280 / max(h, w)
        frame = cv2.resize(frame, (int(w * scale), int(h * scale)))

    detector = _get_detector()
    umbral_orig = config.CONF_THRESHOLD
    config.CONF_THRESHOLD = conf_req
    try:
        detecciones = detector.inferir(frame, modelos_req)
    finally:
        config.CONF_THRESHOLD = umbral_orig

    from src.utils import dibujar_detecciones
    anotada = dibujar_detecciones(frame, detecciones)

    _, buf = cv2.imencode(".jpg", anotada, [cv2.IMWRITE_JPEG_QUALITY, 88])
    b64 = base64.b64encode(buf.tobytes()).decode()

    return jsonify({
        "imagen_b64":  b64,
        "detecciones": [
            {
                "tipo":      d["tipo"],
                "clase":     d["clase"],
                "confianza": round(d["confianza"], 3),
                "x1": d["x1"], "y1": d["y1"],
                "x2": d["x2"], "y2": d["y2"]
            }
            for d in detecciones
        ],
        "total": len(detecciones),
    })


@app.route("/api/control", methods=["POST"])
@requires_auth
def api_control():
    data   = request.json or {}
    accion = data.get("accion")

    if accion == "iniciar":
        modelos_sel = data.get("modelos", ["armas", "rostros"])
        conf_sel    = float(data.get("conf", 0.40))

        _estado["activo"]             = True
        _estado["frames"]             = 0
        _estado["alertas_total"]      = 0
        _estado["det_armas"]          = 0
        _estado["det_rostros"]        = 0
        _estado["det_placas"]         = 0
        _estado["personas_en_pantalla"] = 0
        _estado["inicio_ts"]          = time.time()
        _estado["modelos"]            = modelos_sel
        _estado["conf"]               = conf_sel
        _estado["cooldown"]           = int(data.get("cooldown", 30))
        _estado["intervalo"]          = float(data.get("intervalo", 1.0))
        config.CONF_THRESHOLD    = conf_sel
        config.COOLDOWN_SEGUNDOS = _estado["cooldown"]

        # Propagar al detector si ya existe
        if _detector is not None:
            _detector.conf_threshold = conf_sel

        # Crear/reutilizar alertas AHORA (eager) para que el cooldown sea correcto
        # desde el primer arma detectada, sin depender de la inicialización lazy
        alertas_obj = _get_alertas()
        alertas_obj.cooldown    = _estado["cooldown"]
        alertas_obj._ultimo_ts  = 0.0  # primera alerta sale inmediato

        # Crear sesión en Supabase en background (no bloquear la respuesta al cliente)
        _modelos_snap = list(modelos_sel)
        _conf_snap    = conf_sel
        def _crear_sesion_bd():
            sesion_id = iniciar_sesion(_modelos_snap, 0, _conf_snap)
            with _lock:
                _estado["sesion_bd_id"] = sesion_id
        threading.Thread(target=_crear_sesion_bd, daemon=True).start()

        logger.info(
            "Sistema activado | conf=%.2f | cooldown=%ds | intervalo=%.1fs | modelos=%s",
            conf_sel, _estado["cooldown"], _estado["intervalo"], modelos_sel,
        )
        return jsonify({"ok": True, "mensaje": "Sistema listo para recibir frames"})

    elif accion == "detener" and _estado["activo"]:
        cerrar_sesion(
            _estado.get("sesion_bd_id"),
            _estado["frames"],
            _estado["alertas_total"],
        )
        _estado["activo"]        = False
        _estado["inicio_ts"]     = None
        _estado["sesion_bd_id"]  = None
        logger.info("Sistema de procesamiento desactivado.")
        return jsonify({"ok": True, "mensaje": "Sistema detenido"})

    elif accion == "actualizar":
        if not _estado["activo"]:
            return jsonify({"ok": False, "mensaje": "El sistema no está activo"})

        conf_nuevo      = float(data.get("conf",      _estado["conf"]))
        cooldown_nuevo  = int(data.get("cooldown",    _estado["cooldown"]))
        intervalo_nuevo = float(data.get("intervalo", _estado["intervalo"]))
        modelos_nuevos  = data.get("modelos",         _estado["modelos"])

        with _lock:
            _estado["conf"]      = conf_nuevo
            _estado["cooldown"]  = cooldown_nuevo
            _estado["intervalo"] = intervalo_nuevo
            _estado["modelos"]   = modelos_nuevos

        # Propagar al detector y gestor de alertas sin reiniciarlos
        config.CONF_THRESHOLD    = conf_nuevo
        config.COOLDOWN_SEGUNDOS = cooldown_nuevo  # garantiza que _get_alertas() lazy también lo recoja
        if _detector is not None:
            _detector.conf_threshold = conf_nuevo
        if _alertas is not None:
            _alertas.cooldown = cooldown_nuevo

        logger.info(
            "Parámetros actualizados | conf=%.2f | cooldown=%ds | intervalo=%.1fs | modelos=%s",
            conf_nuevo, cooldown_nuevo, intervalo_nuevo, modelos_nuevos,
        )
        return jsonify({"ok": True, "mensaje": "Parámetros actualizados"})

    elif accion == "alarma":
        _estado["alarma_on"] = bool(data.get("on", True))
        logger.info("Alarma WhatsApp %s", "ACTIVADA" if _estado["alarma_on"] else "DESACTIVADA")
        return jsonify({"ok": True, "alarma_on": _estado["alarma_on"]})

    elif accion == "estado":
        return jsonify({"activo": _estado["activo"], "alarma_on": _estado["alarma_on"]})

    return jsonify({"ok": False, "mensaje": "Acción no válida o estado incorrecto"})


if __name__ == "__main__":
    import webbrowser
    port = 5002
    print(f"\n{'='*55}")
    print(f"  SI904-M2 Dashboard -> http://127.0.0.1:{port}")
    print(f"{'='*55}\n")
    threading.Timer(1.5, lambda: webbrowser.open(f"http://127.0.0.1:{port}")).start()
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
