"""
src/utils.py - Utilidades reutilizables del sistema SI904-M2
=============================================================
Funciones puras: logging, timestamps, carpetas y dibujo de
detecciones sobre frames de OpenCV.
"""

import logging
import os
from datetime import datetime
from typing import Any

import cv2
import numpy as np

# ------------------------------------------------------------------
# Colores por tipo de detección (BGR para OpenCV)
# ------------------------------------------------------------------
_COLORES: dict[str, tuple[int, int, int]] = {
    "armas":   (0,   0,   220),   # rojo intenso
    "rostros": (0,   200, 0),     # verde
    "placas":  (220, 130, 0),     # azul
}
_COLOR_DEFAULT = (200, 200, 0)    # cian para tipos desconocidos


def obtener_logger(nombre: str = "SI904") -> logging.Logger:
    """
    Devuelve un logger configurado con formato legible en español.
    Si el logger ya existe, lo reutiliza (idempotente).
    """
    logger = logging.getLogger(nombre)
    if not logger.handlers:
        handler = logging.StreamHandler()
        fmt = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(fmt)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
    return logger


def asegurar_carpeta(ruta: str) -> str:
    """
    Crea la carpeta (y sus padres) si no existe.
    Devuelve la ruta para facilitar encadenamiento.
    """
    os.makedirs(ruta, exist_ok=True)
    return ruta


def generar_timestamp(fmt: str = "%Y%m%d_%H%M%S") -> str:
    """
    Devuelve la fecha/hora actual como cadena con el formato dado.
    Por defecto: '20240623_153045'
    """
    return datetime.now().strftime(fmt)


def dibujar_detecciones(
    frame: np.ndarray,
    detecciones: list[dict[str, Any]],
) -> np.ndarray:
    """
    Dibuja las cajas delimitadoras y etiquetas sobre el frame.

    Cada detección es un dict con las claves:
        tipo       (str):  'armas', 'rostros' o 'placas'
        clase      (str):  nombre de la clase predicha
        confianza  (float): valor entre 0 y 1
        x1, y1    (int):  esquina superior izquierda
        x2, y2    (int):  esquina inferior derecha

    Devuelve el mismo frame modificado in-place (y como retorno).
    """
    copia = frame.copy()

    for det in detecciones:
        tipo = det.get("tipo", "")
        clase = det.get("clase", "objeto")
        conf = det.get("confianza", 0.0)
        x1 = int(det.get("x1", 0))
        y1 = int(det.get("y1", 0))
        x2 = int(det.get("x2", 0))
        y2 = int(det.get("y2", 0))

        color = _COLORES.get(tipo, _COLOR_DEFAULT)
        grosor = 2

        # Caja delimitadora
        cv2.rectangle(copia, (x1, y1), (x2, y2), color, grosor)

        # Etiqueta con fondo opaco para legibilidad
        etiqueta = f"{clase} {conf:.0%}"
        (ancho_txt, alto_txt), baseline = cv2.getTextSize(
            etiqueta, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1
        )
        y_fondo = max(y1 - alto_txt - baseline - 4, 0)
        cv2.rectangle(
            copia,
            (x1, y_fondo),
            (x1 + ancho_txt + 4, y1),
            color,
            -1,  # relleno sólido
        )
        cv2.putText(
            copia,
            etiqueta,
            (x1 + 2, y1 - baseline - 2),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )

    return copia
