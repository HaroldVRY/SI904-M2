"""
src/alertas.py - Gestor de alertas por WhatsApp (Twilio)
=========================================================
Envía un mensaje de WhatsApp cuando se detectan amenazas,
respetando un cooldown configurable para no saturar el canal.
Guarda además la captura anotada en capturas/.

Envío de foto (enviar_foto, default True):
    Intenta enviar la imagen anotada por WhatsApp usando Twilio MediaUrl.
    Requiere una URL pública que sirva capturas/, resuelta por prioridad:
        1. URL_PUBLICA_CAPTURAS en .env (uso local con ngrok).
        2. RENDER_EXTERNAL_URL + "/capturas" (automático en Render,
           servido por la ruta /capturas de dashboard.py).
    Sin ninguna URL pública disponible, se envía solo el texto.
"""


from __future__ import annotations

import os
import time
from typing import Any

import cv2
import numpy as np

try:
    from twilio.rest import Client  # type: ignore
except ImportError:
    Client = None  # type: ignore

import config
from src.utils import asegurar_carpeta, dibujar_detecciones, generar_timestamp, obtener_logger

logger = obtener_logger("Alertas")


class GestorAlertas:
    """
    Gestiona el envío de alertas por WhatsApp vía Twilio.

    - Respeta un cooldown (segundos) entre alertas consecutivas.
    - Guarda la captura anotada en capturas/.
    - Si Twilio no está configurado, solo registra en log (no falla).
    """

    def __init__(self, enviar_foto: bool = True) -> None:
        """
        Parameters
        ----------
        enviar_foto : bool
            Si True (default), intenta enviar la captura anotada por WhatsApp
            usando Twilio MediaUrl. Solo se envía si se logra resolver una
            URL pública (ver _resolver_url_publica).
        """
        self.cooldown    = config.COOLDOWN_SEGUNDOS
        self.enviar_foto = enviar_foto
        self._ultimo_ts  = 0.0          # timestamp de la última alerta enviada
        self._carpeta    = asegurar_carpeta("capturas")
        self._url_publica: str = self._resolver_url_publica()

        # Intentar importar Twilio solo si las credenciales están disponibles
        self._twilio_ok = bool(
            config.TWILIO_ACCOUNT_SID
            and config.TWILIO_AUTH_TOKEN
            and config.TWILIO_WHATSAPP_TO
        )
        if self._twilio_ok:
            try:
                self._twilio_client = Client(
                    config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN
                )
                logger.info(
                    "Twilio configurado → WhatsApp habilitado (to=%s)",
                    config.TWILIO_WHATSAPP_TO,
                )
            except Exception as exc:
                logger.error("No se pudo inicializar Twilio: %s", exc)
                self._twilio_ok = False
        else:
            logger.warning(
                "Credenciales de Twilio incompletas. "
                "Las alertas se registrarán solo en log."
            )

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    @staticmethod
    def _resolver_url_publica() -> str:
        """
        Determina la URL base pública que sirve la carpeta capturas/.

        Prioridad:
            1. URL_PUBLICA_CAPTURAS en .env (uso local con ngrok).
            2. RENDER_EXTERNAL_URL (Render la define automáticamente en
               despliegue) + "/capturas" — servido por dashboard.py.

        Devuelve "" si ninguna está disponible (no se enviarán fotos).
        """
        url_manual = os.getenv("URL_PUBLICA_CAPTURAS", "").rstrip("/")
        if url_manual:
            return url_manual

        url_render = os.getenv("RENDER_EXTERNAL_URL", "").rstrip("/")
        if url_render:
            return f"{url_render}/capturas"

        return ""

    def disparar(
        self,
        frame: np.ndarray,
        detecciones: list[dict[str, Any]],
        enviar_whatsapp: bool = True,
    ) -> bool:
        """
        Verifica cooldown y, si pasa, registra la alerta.

        - Siempre respeta el cooldown (controla la frecuencia del panel).
        - Solo guarda captura y envía WhatsApp si enviar_whatsapp=True
          (se activa cuando hay arma detectada y la alarma está ON).

        Devuelve True si el cooldown lo permitió (alerta registrada).
        """
        if not detecciones:
            return False

        ahora = time.time()
        if ahora - self._ultimo_ts < self.cooldown:
            restante = int(self.cooldown - (ahora - self._ultimo_ts))
            logger.debug("Cooldown activo — faltan %d s.", restante)
            return False

        self._ultimo_ts = ahora
        logger.info("Alerta de panel generada (cooldown superado).")

        # Captura y WhatsApp: solo si hay arma y alarma activa
        if enviar_whatsapp and self._twilio_ok:
            ruta_captura = self._guardar_captura(frame, detecciones)
            mensaje = self._armar_mensaje(detecciones, ruta_captura)
            logger.info("Enviando WhatsApp:\n%s", mensaje)
            if self.enviar_foto and self._url_publica:
                self._enviar_whatsapp_con_foto(mensaje, ruta_captura)
            else:
                self._enviar_whatsapp(mensaje)

        return True

    # ------------------------------------------------------------------
    # Métodos internos
    # ------------------------------------------------------------------

    def _guardar_captura(
        self,
        frame: np.ndarray,
        detecciones: list[dict[str, Any]],
    ) -> str:
        """Dibuja las cajas en el frame y guarda la imagen en capturas/."""
        frame_anotado = dibujar_detecciones(frame, detecciones)
        ts = generar_timestamp()
        nombre = f"alerta_{ts}.jpg"
        ruta = os.path.join(self._carpeta, nombre)
        cv2.imwrite(ruta, frame_anotado)
        logger.info("Captura guardada: %s", ruta)
        return ruta

    def _armar_mensaje(
        self,
        detecciones: list[dict[str, Any]],
        ruta_captura: str,
    ) -> str:
        """Construye el texto del mensaje de WhatsApp."""
        from datetime import datetime

        ts_legible = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        # Agrupar por tipo
        resumen: dict[str, list[str]] = {}
        for det in detecciones:
            tipo = det["tipo"]
            clase = det["clase"]
            conf = det["confianza"]
            resumen.setdefault(tipo, []).append(f"{clase} ({conf:.0%})")

        lineas = [
            "🚨 *ALERTA DE SEGURIDAD* 🚨",
            f"📅 {ts_legible}",
            "",
        ]
        for tipo, items in resumen.items():
            icono = {"armas": "🔫", "rostros": "👤", "placas": "🚗"}.get(tipo, "⚠️")
            lineas.append(f"{icono} *{tipo.upper()}* detectado(s):")
            for item in items:
                lineas.append(f"   • {item}")

        lineas += ["", f"📸 Captura guardada: {os.path.basename(ruta_captura)}"]
        return "\n".join(lineas)

    def _enviar_whatsapp(self, mensaje: str) -> None:
        """Envía el mensaje de texto por WhatsApp usando Twilio. Captura excepciones."""
        try:
            msg = self._twilio_client.messages.create(
                body=mensaje,
                from_=config.TWILIO_WHATSAPP_FROM,
                to=config.TWILIO_WHATSAPP_TO,
            )
            logger.info("WhatsApp enviado — SID: %s", msg.sid)
        except Exception as exc:
            logger.error("Error al enviar WhatsApp: %s", exc)

    def _enviar_whatsapp_con_foto(self, mensaje: str, ruta_captura: str) -> None:
        """
        Envía la captura anotada junto con el texto por WhatsApp.

        En Render, self._url_publica ya apunta a RENDER_EXTERNAL_URL + "/capturas"
        (servida por dashboard.py) sin configuración adicional.

        Para uso local con ngrok:
            ngrok http 8000
            # En otra terminal:
            python -m http.server 8000   # desde la carpeta raiz del proyecto
            URL_PUBLICA_CAPTURAS=https://xxxx.ngrok.io/capturas
        """
        nombre_archivo = os.path.basename(ruta_captura)
        media_url = f"{self._url_publica}/{nombre_archivo}"
        try:
            msg = self._twilio_client.messages.create(
                body=mensaje,
                from_=config.TWILIO_WHATSAPP_FROM,
                to=config.TWILIO_WHATSAPP_TO,
                media_url=[media_url],
            )
            logger.info("WhatsApp con foto enviado — SID: %s | url=%s", msg.sid, media_url)
        except Exception as exc:
            logger.error("Error al enviar WhatsApp con foto: %s", exc)
            logger.info("Intentando enviar solo el texto...")
            self._enviar_whatsapp(mensaje)
