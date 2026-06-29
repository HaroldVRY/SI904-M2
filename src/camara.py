"""
src/camara.py - Clase Camara
=============================
Envuelve cv2.VideoCapture para manejar tanto webcam (índice entero)
como archivos de video o URLs de cámara IP (cadena de texto).
"""

from __future__ import annotations

from typing import Optional, Union

import cv2
import numpy as np

from src.utils import obtener_logger

logger = obtener_logger("Camara")


class Camara:
    """
    Abstracción sobre cv2.VideoCapture.

    Parámetros
    ----------
    fuente : int | str
        Índice de la webcam (0, 1, …) o ruta/URL del video/IP.
    """

    def __init__(self, fuente: Union[int, str] = 0) -> None:
        self._fuente = fuente
        self._cap = cv2.VideoCapture(fuente)

        if not self._cap.isOpened():
            logger.error(
                "No se pudo abrir la fuente de video: '%s'", fuente
            )
        else:
            ancho  = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            alto   = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps    = self._cap.get(cv2.CAP_PROP_FPS)
            logger.info(
                "Cámara abierta: fuente='%s' | resolución=%dx%d | fps=%.1f",
                fuente,
                ancho,
                alto,
                fps,
            )

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def esta_abierta(self) -> bool:
        """Devuelve True si la fuente de video está disponible."""
        return self._cap.isOpened()

    def leer_frame(self) -> Optional[np.ndarray]:
        """
        Lee un frame de la fuente.

        Devuelve el frame (np.ndarray BGR) si tuvo éxito,
        o None si la lectura falló o la fuente se agotó.
        """
        if not self._cap.isOpened():
            return None

        ok, frame = self._cap.read()
        if not ok:
            logger.warning("No se pudo leer el frame (fuente agotada o error).")
            return None

        return frame

    def liberar(self) -> None:
        """Libera los recursos de la cámara."""
        if self._cap.isOpened():
            self._cap.release()
            logger.info("Cámara liberada: fuente='%s'", self._fuente)

    # ------------------------------------------------------------------
    # Context manager para uso con 'with'
    # ------------------------------------------------------------------

    def __enter__(self) -> "Camara":
        return self

    def __exit__(self, *args) -> None:
        self.liberar()
