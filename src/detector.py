"""
src/detector.py - Detector de amenazas vía Roboflow API
=========================================================
Encapsula las llamadas a los 3 modelos hospedados en Roboflow
y normaliza las predicciones a un formato uniforme.
"""

from __future__ import annotations

from typing import Any

from inference_sdk import InferenceHTTPClient

import config
from src.utils import obtener_logger

logger = obtener_logger("Detector")


class DetectorRoboflow:
    """
    Realiza inferencia sobre frames usando los modelos de Roboflow.

    Uso:
        detector = DetectorRoboflow()
        detecciones = detector.inferir(frame, modelos=["armas", "rostros"])
    """

    def __init__(self) -> None:
        """Inicializa el cliente HTTP de Roboflow con las credenciales de config."""
        self.client = InferenceHTTPClient(
            api_url=config.ROBOFLOW_API_URL,
            api_key=config.ROBOFLOW_API_KEY,
        )
        self.conf_threshold = config.CONF_THRESHOLD
        logger.info(
            "DetectorRoboflow inicializado | umbral=%.2f", self.conf_threshold
        )

    def inferir(
        self,
        frame: Any,          # np.ndarray o ruta de imagen (str)
        modelos: list[str],  # e.g. ["armas", "rostros"]
    ) -> list[dict[str, Any]]:
        """
        Ejecuta los modelos indicados sobre el frame y devuelve
        una lista de detecciones normalizadas.

        Cada detección es un dict con las claves:
            tipo       (str):  nombre del modelo ('armas', 'rostros', 'placas')
            clase      (str):  clase predicha por el modelo
            confianza  (float): valor de confianza [0, 1]
            x1, y1    (int):  esquina superior izquierda de la caja
            x2, y2    (int):  esquina inferior derecha de la caja

        Los errores de red por modelo se registran en log sin abortar
        la inferencia con los demás modelos.
        """
        detecciones: list[dict[str, Any]] = []

        for nombre in modelos:
            model_id = config.MODELOS.get(nombre)
            if not model_id:
                logger.warning("Modelo desconocido: '%s'. Omitiendo.", nombre)
                continue

            try:
                resultado = self.client.infer(frame, model_id=model_id)
            except Exception as exc:
                logger.error(
                    "Error de red al inferir con '%s': %s", nombre, exc
                )
                continue

            predicciones = resultado.get("predictions", [])

            # Log crudo: muestra TODO lo que el modelo ve, antes del umbral
            if predicciones:
                resumen = ", ".join(
                    f"{p.get('class','?')}={p.get('confidence',0):.2f}"
                    for p in predicciones
                )
                logger.info("[%s] RAW predictions: %s", nombre, resumen)
            else:
                logger.info("[%s] RAW predictions: (ninguna)", nombre)

            for pred in predicciones:
                conf = pred.get("confidence", 0.0)
                if conf < self.conf_threshold:
                    continue

                # Roboflow entrega centro (x,y) + tamaño (w,h) en píxeles
                cx = pred.get("x", 0)
                cy = pred.get("y", 0)
                w  = pred.get("width", 0)
                h  = pred.get("height", 0)

                x1 = int(cx - w / 2)
                y1 = int(cy - h / 2)
                x2 = int(cx + w / 2)
                y2 = int(cy + h / 2)

                detecciones.append(
                    {
                        "tipo":      nombre,
                        "clase":     pred.get("class", "objeto"),
                        "confianza": conf,
                        "x1": x1,
                        "y1": y1,
                        "x2": x2,
                        "y2": y2,
                    }
                )

            logger.debug(
                "[%s] %d detección(es) con conf>=%.2f",
                nombre,
                len([d for d in detecciones if d["tipo"] == nombre]),
                self.conf_threshold,
            )

        return detecciones
