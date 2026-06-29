"""
main.py - Orquestador principal — FASE 2
==========================================
Bucle: leer frame → inferir → dibujar → alertar → mostrar.
Ejecutar: python main.py [--source 0] [--modelos armas rostros] [...]
"""

from __future__ import annotations

import argparse
import sys
import time

import cv2

# config.py valida la API key al importar; abortará si falta.
import config  # noqa: F401 (importar para validación temprana)
from src.alertas import GestorAlertas
from src.camara import Camara
from src.detector import DetectorRoboflow
from src.utils import dibujar_detecciones, obtener_logger

logger = obtener_logger("Main")

# Tipos de detección considerados de alto riesgo (disparan alerta)
_TIPOS_RIESGO = {"armas"}


def parsear_argumentos() -> argparse.Namespace:
    """Define y parsea los argumentos de la línea de comandos."""
    parser = argparse.ArgumentParser(
        description="Sistema de seguridad ciudadana — SI904-M2",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--source",
        default=0,
        help="Índice de webcam (int) o ruta/URL del video (str).",
    )
    parser.add_argument(
        "--modelos",
        nargs="+",
        default=["armas", "rostros"],
        choices=list(config.MODELOS.keys()),
        help="Modelos a ejecutar (uno o más de: armas, rostros, placas).",
    )
    parser.add_argument(
        "--conf",
        type=float,
        default=config.CONF_THRESHOLD,
        help="Umbral mínimo de confianza para mostrar una detección.",
    )
    parser.add_argument(
        "--cooldown",
        type=int,
        default=config.COOLDOWN_SEGUNDOS,
        help="Segundos de espera mínima entre alertas de WhatsApp.",
    )
    parser.add_argument(
        "--intervalo",
        type=float,
        default=config.INTERVALO_INFERENCIA,
        help="Segundos entre llamadas a la API de Roboflow.",
    )
    parser.add_argument(
        "--enviar-foto",
        action="store_true",
        default=False,
        help="Enviar la captura anotada por WhatsApp via Twilio MediaUrl "
             "(requiere URL_PUBLICA_CAPTURAS en .env).",
    )
    return parser.parse_args()


def convertir_source(source: str | int) -> int | str:
    """Convierte el argumento --source al tipo correcto (int para webcam)."""
    try:
        return int(source)
    except (ValueError, TypeError):
        return str(source)


def main() -> None:
    args = parsear_argumentos()

    # Aplicar overrides de argumentos sobre config
    config.CONF_THRESHOLD       = args.conf
    config.COOLDOWN_SEGUNDOS    = args.cooldown
    config.INTERVALO_INFERENCIA = args.intervalo

    fuente  = convertir_source(args.source)
    modelos = args.modelos

    logger.info("Iniciando sistema | fuente=%s | modelos=%s", fuente, modelos)

    detector = DetectorRoboflow()
    alertas  = GestorAlertas(enviar_foto=args.enviar_foto)

    ultimo_inferencia = 0.0
    total_frames      = 0
    total_alertas     = 0

    with Camara(fuente) as cam:
        if not cam.esta_abierta():
            logger.error("No se pudo abrir la cámara. Saliendo.")
            sys.exit(1)

        logger.info("Presiona 'q' para salir.")

        while True:
            frame = cam.leer_frame()
            if frame is None:
                logger.info("Fin del video o error de lectura. Saliendo.")
                break

            total_frames += 1
            ahora = time.time()

            # ── Inferencia periódica ──────────────────────────────────
            detecciones = []
            if ahora - ultimo_inferencia >= args.intervalo:
                ultimo_inferencia = ahora
                detecciones = detector.inferir(frame, modelos)

                # Disparar alerta si hay detecciones de riesgo
                det_riesgo = [d for d in detecciones if d["tipo"] in _TIPOS_RIESGO]
                if det_riesgo:
                    if alertas.disparar(frame, detecciones):
                        total_alertas += 1

            # ── Dibujar y mostrar ─────────────────────────────────────
            frame_vis = dibujar_detecciones(frame, detecciones)

            # HUD: contador de frames y alertas
            cv2.putText(
                frame_vis,
                f"Frames: {total_frames}  |  Alertas: {total_alertas}  |  Q: salir",
                (10, 28),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 255),
                1,
                cv2.LINE_AA,
            )

            cv2.imshow("SI904-M2 — Seguridad Ciudadana", frame_vis)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                logger.info("Usuario presionó 'q'. Cerrando.")
                break

    cv2.destroyAllWindows()
    logger.info(
        "Sistema detenido | frames=%d | alertas enviadas=%d",
        total_frames,
        total_alertas,
    )


if __name__ == "__main__":
    main()
