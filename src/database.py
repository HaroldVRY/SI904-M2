"""
src/database.py - Integración con Supabase (PostgreSQL en la nube)
====================================================================
Proporciona funciones para registrar sesiones, detecciones y alertas
en la base de datos Supabase del proyecto SI904-M2.

Todas las funciones son tolerantes a fallos: si SUPABASE_URL o
SUPABASE_KEY no están configurados, o si la conexión falla, simplemente
retornan None/False sin interrumpir el flujo del sistema.
"""

from __future__ import annotations

import os
from typing import Any

from src.utils import obtener_logger

logger = obtener_logger("Database")

# ── Cliente Supabase (lazy-init) ───────────────────────────────────
_client = None


def _get_client():
    """Retorna el cliente Supabase, inicializándolo si es necesario."""
    global _client
    if _client is not None:
        return _client

    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_KEY", "").strip()

    if not url or not key:
        logger.warning("SUPABASE_URL o SUPABASE_KEY no configurados. BD desactivada.")
        return None

    try:
        from supabase import create_client
        _client = create_client(url, key)
        logger.info(f"Supabase conectado: {url[:40]}...")
        return _client
    except Exception as e:
        logger.error(f"Error al conectar con Supabase: {e}")
        return None


# ══════════════════════════════════════════════════════════════════
# SESIONES
# ══════════════════════════════════════════════════════════════════

def iniciar_sesion(modelos: list[str], fuente: int, conf: float) -> int | None:
    """
    Crea un registro de sesión en la tabla `sesiones`.
    Retorna el ID generado, o None si la BD está desactivada.
    """
    client = _get_client()
    if not client:
        return None
    try:
        result = client.table("sesiones").insert({
            "modelos_activos": modelos,
            "fuente_video":    str(fuente),
            "conf_threshold":  float(conf),
        }).execute()
        sesion_id = result.data[0]["id"] if result.data else None
        logger.info(f"Sesión iniciada en BD: id={sesion_id}")
        return sesion_id
    except Exception as e:
        logger.error(f"Error al crear sesión en BD: {e}")
        return None


def cerrar_sesion(sesion_id: int | None, total_frames: int, total_alertas: int) -> None:
    """Marca el fin de una sesión y guarda las métricas finales."""
    client = _get_client()
    if not client or not sesion_id:
        return
    try:
        client.table("sesiones").update({
            "total_frames":  total_frames,
            "total_alertas": total_alertas,
        }).eq("id", sesion_id).execute()
        logger.info(f"Sesión {sesion_id} cerrada en BD.")
    except Exception as e:
        logger.error(f"Error al cerrar sesión en BD: {e}")


# ══════════════════════════════════════════════════════════════════
# DETECCIONES
# ══════════════════════════════════════════════════════════════════

def registrar_deteccion(
    sesion_id:     int | None,
    tipo:          str,
    clase:         str,
    confianza:     float,
    x1: int, y1: int,
    x2: int, y2: int,
    disparo_alerta: bool = False,
) -> None:
    """
    Inserta una fila en `detecciones` para cada objeto detectado.
    Llamar desde el hilo de cámara (es thread-safe por el cliente Supabase).
    """
    client = _get_client()
    if not client or not sesion_id:
        return
    try:
        client.table("detecciones").insert({
            "sesion_id":      sesion_id,
            "tipo":           tipo,
            "clase":          clase,
            "confianza":      round(float(confianza), 4),
            "x1": int(x1), "y1": int(y1),
            "x2": int(x2), "y2": int(y2),
            "disparo_alerta": disparo_alerta,
        }).execute()
    except Exception as e:
        logger.error(f"Error al registrar detección: {e}")


def registrar_detecciones_lote(
    sesion_id:     int | None,
    detecciones:   list[dict[str, Any]],
    disparo_alerta: bool = False,
) -> None:
    """
    Inserta múltiples detecciones de un mismo frame en una sola petición.
    Más eficiente que llamar a registrar_deteccion() N veces.
    """
    client = _get_client()
    if not client or not sesion_id or not detecciones:
        return
    try:
        rows = [
            {
                "sesion_id":      sesion_id,
                "tipo":           d["tipo"],
                "clase":          d["clase"],
                "confianza":      round(float(d["confianza"]), 4),
                "x1": int(d["x1"]), "y1": int(d["y1"]),
                "x2": int(d["x2"]), "y2": int(d["y2"]),
                "disparo_alerta": disparo_alerta,
            }
            for d in detecciones
        ]
        client.table("detecciones").insert(rows).execute()
    except Exception as e:
        logger.error(f"Error al registrar lote de detecciones: {e}")


# ══════════════════════════════════════════════════════════════════
# ALERTAS WHATSAPP
# ══════════════════════════════════════════════════════════════════

def registrar_alerta_whatsapp(
    sesion_id:        int | None,
    numero_destino:   str,
    estado:           str,
    twilio_sid:       str | None,
    mensaje_texto:    str,
    detecciones_json: list[dict],
) -> None:
    """Registra una alerta WhatsApp enviada en la tabla `alertas_whatsapp`."""
    client = _get_client()
    if not client or not sesion_id:
        return
    try:
        client.table("alertas_whatsapp").insert({
            "sesion_id":       sesion_id,
            "numero_destino":  numero_destino,
            "estado":          estado,
            "twilio_sid":      twilio_sid,
            "mensaje_texto":   mensaje_texto,
            "detecciones_json": detecciones_json,
        }).execute()
        logger.info(f"Alerta WhatsApp registrada en BD (sesión {sesion_id}).")
    except Exception as e:
        logger.error(f"Error al registrar alerta WhatsApp en BD: {e}")


# ══════════════════════════════════════════════════════════════════
# CONSULTAS (para reportes futuros)
# ══════════════════════════════════════════════════════════════════

def obtener_sesiones(limite: int = 20) -> list[dict]:
    """Retorna las últimas N sesiones con su resumen."""
    client = _get_client()
    if not client:
        return []
    try:
        result = client.table("sesiones").select("*").order(
            "inicio", desc=True).limit(limite).execute()
        return result.data or []
    except Exception as e:
        logger.error(f"Error al consultar sesiones: {e}")
        return []


def obtener_detecciones_sesion(sesion_id: int) -> list[dict]:
    """Retorna todas las detecciones de una sesión específica."""
    client = _get_client()
    if not client:
        return []
    try:
        result = client.table("detecciones").select("*").eq(
            "sesion_id", sesion_id).order("detectado_en", desc=False).execute()
        return result.data or []
    except Exception as e:
        logger.error(f"Error al consultar detecciones: {e}")
        return []
