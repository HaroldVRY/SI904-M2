"""
tests/conftest.py - Configuración global de pytest para SI904-M2
=================================================================
Asegura que ROBOFLOW_API_KEY esté presente antes de que
cualquier módulo que importe config.py falle en la validación.
"""

import os
import pytest

# Inyectar API key ficticia para tests (antes de cualquier import de config)
os.environ.setdefault("ROBOFLOW_API_KEY", "test_key_pytest")
