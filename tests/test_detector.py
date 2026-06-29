"""
tests/test_detector.py
======================
Pruebas unitarias para DetectorRoboflow.

Se mockea InferenceHTTPClient.infer para no hacer llamadas reales a la API.
Verifica:
    - Conversión correcta de centro (x,y,w,h) → esquinas (x1,y1,x2,y2)
    - Filtrado por umbral de confianza (CONF_THRESHOLD)
    - Manejo de errores de red sin abortar
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# Configurar API key ficticia antes de importar módulos que dependan de config
os.environ["ROBOFLOW_API_KEY"] = "test_key"


import config
config.CONF_THRESHOLD = 0.40

from src.detector import DetectorRoboflow


# Respuesta simulada de Roboflow para el modelo de armas
_RESPUESTA_ARMAS = {
    "predictions": [
        # Debería pasar el filtro (conf=0.90 >= 0.40)
        {"x": 100, "y": 150, "width": 80, "height": 60,
         "confidence": 0.90, "class": "knife", "class_id": 0},
        # Debería ser filtrado (conf=0.30 < 0.40)
        {"x": 200, "y": 250, "width": 40, "height": 30,
         "confidence": 0.30, "class": "rifle", "class_id": 1},
    ]
}

_RESPUESTA_ROSTROS = {
    "predictions": [
        {"x": 300, "y": 200, "width": 100, "height": 100,
         "confidence": 0.85, "class": "face", "class_id": 0},
    ]
}


class TestDetectorRoboflow:
    """Pruebas para la clase DetectorRoboflow."""

    @patch("src.detector.InferenceHTTPClient")
    def test_conversion_centro_a_esquinas(self, mock_client_cls):
        """Verifica la conversión (cx,cy,w,h) → (x1,y1,x2,y2)."""
        mock_client = MagicMock()
        mock_client.infer.return_value = _RESPUESTA_ARMAS
        mock_client_cls.return_value = mock_client

        detector = DetectorRoboflow()
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        dets = detector.inferir(frame, ["armas"])

        # Solo la detección con conf=0.90 debe pasar
        assert len(dets) == 1

        det = dets[0]
        # cx=100, cy=150, w=80, h=60
        # x1 = 100 - 40 = 60, y1 = 150 - 30 = 120
        # x2 = 100 + 40 = 140, y2 = 150 + 30 = 180
        assert det["x1"] == 60
        assert det["y1"] == 120
        assert det["x2"] == 140
        assert det["y2"] == 180
        assert det["clase"] == "knife"
        assert det["tipo"] == "armas"

    @patch("src.detector.InferenceHTTPClient")
    def test_filtrado_por_confianza(self, mock_client_cls):
        """Verifica que detecciones con conf < CONF_THRESHOLD se descartan."""
        mock_client = MagicMock()
        mock_client.infer.return_value = _RESPUESTA_ARMAS
        mock_client_cls.return_value = mock_client

        config.CONF_THRESHOLD = 0.40
        detector = DetectorRoboflow()
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        dets = detector.inferir(frame, ["armas"])

        # El rifle (conf=0.30) NO debe aparecer
        assert all(d["clase"] != "rifle" for d in dets)
        assert len(dets) == 1

    @patch("src.detector.InferenceHTTPClient")
    def test_error_de_red_no_aborta(self, mock_client_cls):
        """Un error en un modelo no impide procesar los demás."""
        mock_client = MagicMock()

        def infer_con_error(imagen, model_id):
            if "weapon" in model_id:
                raise ConnectionError("Timeout simulado")
            return _RESPUESTA_ROSTROS

        mock_client.infer.side_effect = infer_con_error
        mock_client_cls.return_value = mock_client

        detector = DetectorRoboflow()
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        dets = detector.inferir(frame, ["armas", "rostros"])

        # Armas falló, pero rostros sí devolvió resultados
        assert all(d["tipo"] == "rostros" for d in dets)
        assert len(dets) >= 1

    @patch("src.detector.InferenceHTTPClient")
    def test_modelo_desconocido_se_omite(self, mock_client_cls):
        """Un nombre de modelo no registrado en config.MODELOS se omite."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        detector = DetectorRoboflow()
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        dets = detector.inferir(frame, ["modelo_inventado"])

        assert dets == []
        mock_client.infer.assert_not_called()

    @patch("src.detector.InferenceHTTPClient")
    def test_multiples_modelos(self, mock_client_cls):
        """Verifica que se procesan múltiples modelos y se unen los resultados."""
        mock_client = MagicMock()

        def infer_multi(imagen, model_id):
            if "weapon" in model_id:
                return _RESPUESTA_ARMAS
            if "face" in model_id:
                return _RESPUESTA_ROSTROS
            return {"predictions": []}

        mock_client.infer.side_effect = infer_multi
        mock_client_cls.return_value = mock_client

        config.CONF_THRESHOLD = 0.40
        detector = DetectorRoboflow()
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        dets = detector.inferir(frame, ["armas", "rostros"])

        tipos = {d["tipo"] for d in dets}
        assert "armas" in tipos
        assert "rostros" in tipos
