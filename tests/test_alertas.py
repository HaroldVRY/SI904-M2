"""
tests/test_alertas.py
======================
Pruebas unitarias para GestorAlertas.

Se mockea Twilio para no hacer llamadas reales a la API.
Verifica:
    - Cooldown: no se llama a WhatsApp si no ha pasado el tiempo
    - Captura: se guarda la imagen anotada en capturas/
    - Sin credenciales: no se llama a WhatsApp (sin fallar)
"""

from __future__ import annotations

import os
import time
from unittest.mock import MagicMock, patch

import cv2
import numpy as np
import pytest

# Configurar variables de entorno antes de importar config
os.environ["ROBOFLOW_API_KEY"] = "test_key"
os.environ["TWILIO_ACCOUNT_SID"]  = "ACtest"
os.environ["TWILIO_AUTH_TOKEN"]   = "token_test"
os.environ["TWILIO_WHATSAPP_FROM"] = "whatsapp:+14155238886"
os.environ["TWILIO_WHATSAPP_TO"]   = "whatsapp:+51999999999"

import config
config.COOLDOWN_SEGUNDOS = 30

# Frame de prueba: imagen negra de 100x100
_FRAME = np.zeros((100, 100, 3), dtype=np.uint8)

# Detección de prueba
_DETS = [
    {
        "tipo": "armas",
        "clase": "knife",
        "confianza": 0.92,
        "x1": 10, "y1": 10, "x2": 50, "y2": 50,
    }
]


class TestGestorAlertas:
    """Pruebas para la clase GestorAlertas."""

    @patch("src.alertas.Client")
    def test_primera_alerta_se_envia(self, mock_twilio_cls, tmp_path, monkeypatch):
        """La primera alerta siempre se envía (cooldown=0 al inicio)."""
        mock_twilio = MagicMock()
        mock_twilio_cls.return_value = mock_twilio

        # Redirigir capturas/ a directorio temporal
        monkeypatch.setattr("src.alertas.asegurar_carpeta", lambda _: str(tmp_path))

        from src.alertas import GestorAlertas
        g = GestorAlertas()
        g._carpeta = str(tmp_path)

        enviado = g.disparar(_FRAME, _DETS)
        assert enviado is True
        mock_twilio.messages.create.assert_called_once()

    @patch("src.alertas.Client")
    def test_cooldown_impide_segunda_alerta(self, mock_twilio_cls, tmp_path, monkeypatch):
        """La segunda alerta dentro del cooldown NO se envía."""
        mock_twilio = MagicMock()
        mock_twilio_cls.return_value = mock_twilio

        monkeypatch.setattr("src.alertas.asegurar_carpeta", lambda _: str(tmp_path))

        config.COOLDOWN_SEGUNDOS = 30

        from src.alertas import GestorAlertas
        g = GestorAlertas()
        g._carpeta = str(tmp_path)

        g.disparar(_FRAME, _DETS)              # Primera alerta (OK)
        enviado = g.disparar(_FRAME, _DETS)   # Segunda (bloqueada por cooldown)

        assert enviado is False
        # Solo se llamó a Twilio una vez
        assert mock_twilio.messages.create.call_count == 1

    @patch("src.alertas.Client")
    def test_captura_guardada(self, mock_twilio_cls, tmp_path, monkeypatch):
        """Se guarda una imagen .jpg en la carpeta de capturas."""
        mock_twilio = MagicMock()
        mock_twilio_cls.return_value = mock_twilio

        monkeypatch.setattr("src.alertas.asegurar_carpeta", lambda _: str(tmp_path))

        from src.alertas import GestorAlertas
        g = GestorAlertas()
        g._carpeta = str(tmp_path)

        g.disparar(_FRAME, _DETS)

        archivos = list(tmp_path.glob("alerta_*.jpg"))
        assert len(archivos) == 1

    def test_sin_credenciales_no_llama_whatsapp(self, tmp_path, monkeypatch):
        """Sin credenciales de Twilio, el sistema NO falla y NO llama a Twilio."""
        # Simular ausencia de credenciales
        monkeypatch.setenv("TWILIO_ACCOUNT_SID", "")
        monkeypatch.setenv("TWILIO_AUTH_TOKEN", "")
        monkeypatch.setenv("TWILIO_WHATSAPP_TO", "")

        # Recargar config para reflejar los nuevos valores
        import importlib
        import src.alertas as mod_alertas

        # Parchear la carpeta
        monkeypatch.setattr("src.alertas.asegurar_carpeta", lambda _: str(tmp_path))

        from src.alertas import GestorAlertas

        # Crear instancia con config temporal sin credenciales
        with patch.object(config, "TWILIO_ACCOUNT_SID", ""), \
             patch.object(config, "TWILIO_AUTH_TOKEN", ""), \
             patch.object(config, "TWILIO_WHATSAPP_TO", ""):
            g = GestorAlertas()
            g._carpeta = str(tmp_path)
            assert g._twilio_ok is False

            # Debe ejecutarse sin excepción y devolver True (captura sí se guarda)
            enviado = g.disparar(_FRAME, _DETS)
            assert enviado is True

    @patch("src.alertas.Client")
    def test_sin_detecciones_no_dispara(self, mock_twilio_cls, tmp_path, monkeypatch):
        """Sin detecciones, disparar() devuelve False sin llamar a Twilio."""
        mock_twilio = MagicMock()
        mock_twilio_cls.return_value = mock_twilio

        monkeypatch.setattr("src.alertas.asegurar_carpeta", lambda _: str(tmp_path))

        from src.alertas import GestorAlertas
        g = GestorAlertas()
        g._carpeta = str(tmp_path)

        enviado = g.disparar(_FRAME, [])
        assert enviado is False
        mock_twilio.messages.create.assert_not_called()
