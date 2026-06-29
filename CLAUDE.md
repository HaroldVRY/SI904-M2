# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Contexto del proyecto
Proyecto académico SI904 (Monografía 02): sistema de seguridad ciudadana por visión por
computadora que detecta amenazas en tiempo real y envía alertas por WhatsApp.

Usa **3 modelos hospedados en Roboflow** (inferencia por API, sin pesos locales):
- **armas**: `weapon-qpfo8/1` (knife, rifle, revolver, etc.)
- **rostros**: `face-detection-yyxs8/2`
- **placas**: `license-plate-w8chc/1`

**Idioma del proyecto: español** (comentarios, logs, docstrings, todo el output).

## Estructura en dos fases
- **FASE 1** (`test_modelos.py`): ejecutar los 3 modelos sobre imágenes estáticas en `data/`
  para confirmar que la API responde y entender el formato de respuesta. Sin cámara ni WhatsApp.
- **FASE 2** (`main.py` + `src/`): pipeline completo — captura de webcam → inferencia periódica
  → dibujar detecciones → disparar alerta por WhatsApp.

## Comandos
```powershell
# Configuración inicial (Windows)
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# FASE 1 — probar conectividad con la API
python test_modelos.py

# FASE 2 — ejecutar con webcam (modelos por defecto: armas + rostros)
python main.py

# Fuente y modelos personalizados
python main.py --source video.mp4 --modelos armas rostros placas

# Enviar captura anotada por WhatsApp (requiere ngrok + URL_PUBLICA_CAPTURAS en .env)
python main.py --enviar-foto

# Tests
pytest tests/
pytest tests/test_detector.py -k "nombre_del_test"
```

**Versión de Python**: usar 3.11 o 3.12. `inference-sdk` **no** soporta 3.13+.

## Arquitectura

Flujo de datos principal (FASE 2):

```
Camara.leer_frame()
  → DetectorRoboflow.inferir(frame, modelos)   # llama API Roboflow
  → dibujar_detecciones(frame, detecciones)    # utils.py, devuelve copia
  → GestorAlertas.disparar(frame, detecciones) # Twilio WhatsApp + cooldown
```

**Comportamientos no obvios:**

- `config.py` llama `sys.exit()` si falta `ROBOFLOW_API_KEY` — valida al importar; el programa
  aborta antes de arrancar la cámara.
- Solo las detecciones con `tipo == "armas"` disparan alertas (`_TIPOS_RIESGO = {"armas"}` en
  `main.py`). Rostros y placas se dibujan pero **no alertan**.
- La inferencia ocurre cada `INTERVALO_INFERENCIA` segundos (default 1.0), no en cada frame,
  para no saturar la API de Roboflow.
- `GestorAlertas` es degradable: si faltan credenciales de Twilio, solo registra en log sin caer.
- `dibujar_detecciones()` retorna una **copia** del frame (no modifica in-place).

**Dict de detección normalizado** (producido por `detector.py`, consumido por `utils.py` y `alertas.py`):
```python
{"tipo": "armas", "clase": "knife", "confianza": 0.93, "x1": 10, "y1": 20, "x2": 100, "y2": 120}
```
Roboflow devuelve centro + tamaño; `detector.py` convierte a esquinas:
`x1 = cx - w/2`, `y1 = cy - h/2`, `x2 = cx + w/2`, `y2 = cy + h/2`.

## Ampliar modelos sin tocar código
Agregar en `.env` — `config.py` los carga automáticamente:
```
MODELO_CASCOS=hard-hat-workers-gkqmq/6
MODELOS_ACTIVOS=armas,rostros,cascos
```
Los modelos predefinidos (`armas`, `rostros`, `placas`) no se sobreescriben.

## Variables de entorno relevantes
| Variable | Default | Uso |
|---|---|---|
| `ROBOFLOW_API_KEY` | **requerida** | API key de Roboflow |
| `CONF_THRESHOLD` | 0.40 | Confianza mínima para incluir una detección |
| `COOLDOWN_SEGUNDOS` | 30 | Segundos mínimos entre alertas de WhatsApp |
| `INTERVALO_INFERENCIA` | 1.0 | Segundos entre llamadas a la API |
| `MODELOS_ACTIVOS` | `armas,rostros` | Modelos activos por defecto |
| `URL_PUBLICA_CAPTURAS` | — | URL ngrok para `--enviar-foto` |

## Formato de respuesta de Roboflow (referencia)
```json
{"image": {"width": 640, "height": 480},
 "predictions": [{"x": 320, "y": 240, "width": 100, "height": 80,
                  "confidence": 0.93, "class": "knife", "class_id": 0}]}
```

## Convenciones
- Componentes con estado → clases; helpers puros → funciones en `src/utils.py`.
- Manejar errores de red (Roboflow/Twilio) y de cámara sin que el programa caiga; loguear y continuar.
- Colores en `utils.py` son BGR (OpenCV): armas=rojo, rostros=verde, placas=azul.
- Clases para componentes con estado; funciones cortas con una sola responsabilidad.
