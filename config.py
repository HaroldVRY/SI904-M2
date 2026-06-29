"""
config.py - Configuración central del proyecto SI904-M2
========================================================
Carga las credenciales desde .env y expone constantes y
los IDs de los modelos de Roboflow.

Para añadir un nuevo modelo SIN tocar este archivo:
    1. Agrega en .env:  MODELO_<NOMBRE>=<workspace>/<version>
       Ejemplo:         MODELO_CASCOS=hard-hat-workers-gkqmq/6
    2. Opcionalmente actívalo por defecto:  MODELOS_ACTIVOS=armas,rostros,cascos
"""

import os
import sys
from dotenv import load_dotenv

# Carga las variables de entorno desde .env (si existe)
load_dotenv()

# ------------------------------------------------------------------
# Roboflow
# ------------------------------------------------------------------
ROBOFLOW_API_KEY: str = os.getenv("ROBOFLOW_API_KEY", "")
ROBOFLOW_API_URL: str = os.getenv(
    "ROBOFLOW_API_URL", "https://serverless.roboflow.com"
)

# Validación obligatoria: sin API key el sistema no puede funcionar
if not ROBOFLOW_API_KEY:
    sys.exit(
        "[ERROR CRÍTICO] Falta ROBOFLOW_API_KEY en el archivo .env.\n"
        "Copia .env.example como .env y completa tu API key de Roboflow."
    )

# ------------------------------------------------------------------
# IDs de los modelos hospedados en Roboflow
# Los 3 predefinidos se pueden ampliar con MODELO_<NOMBRE> en .env
# ------------------------------------------------------------------
MODELOS: dict[str, str] = {
    "armas":   "weapon-qpfo8/1",
    "rostros": "face-detection-yyxs8/2",
    "placas":  "license-plate-w8chc/1",
}

# Cargar modelos adicionales desde .env (MODELO_<NOMBRE>=<model_id>)
_prefijo = "MODELO_"
for _clave, _valor in os.environ.items():
    if _clave.startswith(_prefijo):
        _nombre = _clave[len(_prefijo):].lower()
        if _nombre not in MODELOS:          # no sobreescribir los predefinidos
            MODELOS[_nombre] = _valor

# Lista de modelos activos por defecto (configurable desde .env)
# Ejemplo en .env:  MODELOS_ACTIVOS=armas,rostros,placas
_activos_env = os.getenv("MODELOS_ACTIVOS", "")
MODELOS_ACTIVOS: list[str] = (
    [m.strip() for m in _activos_env.split(",") if m.strip()]
    if _activos_env
    else ["armas", "rostros"]
)

# ------------------------------------------------------------------
# Credenciales de Twilio para alertas por WhatsApp
# ------------------------------------------------------------------
TWILIO_ACCOUNT_SID: str  = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN: str   = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_FROM: str = os.getenv(
    "TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886"
)
TWILIO_WHATSAPP_TO: str  = os.getenv("TWILIO_WHATSAPP_TO", "")

# ------------------------------------------------------------------
# Parámetros del sistema (con valores por defecto razonables)
# ------------------------------------------------------------------
CONF_THRESHOLD: float       = float(os.getenv("CONF_THRESHOLD", "0.40"))
COOLDOWN_SEGUNDOS: int      = int(os.getenv("COOLDOWN_SEGUNDOS", "30"))
INTERVALO_INFERENCIA: float = float(os.getenv("INTERVALO_INFERENCIA", "1.0"))
