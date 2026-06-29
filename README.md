# SI904-M2 — Sistema de Seguridad Ciudadana por Visión por Computadora

Sistema de detección de amenazas en tiempo real que utiliza **3 modelos de IA
hospedados en Roboflow** y envía **alertas por WhatsApp** vía Twilio.

Desarrollado como entregable del curso **SI904** (Monografía 02).

---

## Modelos utilizados

| Nombre   | Model ID en Roboflow         | Detecta                          |
|----------|------------------------------|----------------------------------|
| Armas    | `weapon-qpfo8/1`             | knife, rifle, revolver, etc.     |
| Rostros  | `face-detection-yyxs8/2`    | face                             |
| Placas   | `license-plate-w8chc/1`     | placas vehiculares               |

---

## Requisitos

- **Python 3.10, 3.11 o 3.12** — ⚠️ NO compatible con Python 3.13 (limitación de `inference-sdk`)
- Conexión a Internet (la inferencia se realiza en los servidores de Roboflow)
- Cuenta en [Roboflow](https://roboflow.com) con API key válida
- Cuenta en [Twilio](https://console.twilio.com) para las alertas por WhatsApp (opcional)
- Webcam o archivo de video para la FASE 2

---

## Instalación en Windows

### 1. Clonar/descargar el proyecto

```powershell
cd C:\ruta\del\proyecto\SI904-M2
```

### 2. Crear entorno virtual con Python 3.11 (recomendado)

```powershell
# Verificar que tienes Python 3.11 o 3.12
python --version          # Si apunta a 3.13, usa la ruta completa:
# C:\Users\<tu_usuario>\AppData\Local\Programs\Python\Python311\python.exe --version

# Crear el venv con Python 3.11
C:\Users\<tu_usuario>\AppData\Local\Programs\Python\Python311\python.exe -m venv venv

# Activar el entorno virtual
.\venv\Scripts\Activate.ps1
```

> ⚠️ Si ves el error "la ejecución de scripts está deshabilitada", ejecuta primero:
> `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

### 3. Instalar dependencias

```powershell
pip install -r requirements.txt
```

### 4. Configurar credenciales

```powershell
copy .env.example .env
```

Edita `.env` con tus valores reales:

```env
ROBOFLOW_API_KEY=tu_api_key_de_roboflow
ROBOFLOW_API_URL=https://serverless.roboflow.com

TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=tu_auth_token
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
TWILIO_WHATSAPP_TO=whatsapp:+51XXXXXXXXX
```

---

## Activar el Sandbox de WhatsApp de Twilio

1. Ve a [console.twilio.com](https://console.twilio.com)
2. Navega a **Messaging → Try it out → Send a WhatsApp message**
3. Sigue las instrucciones: envía el código `join xxxx-yyyy` por WhatsApp al número del sandbox
4. Copia el **Account SID** y el **Auth Token** desde el dashboard principal
5. El número del sandbox (`whatsapp:+14155238886`) va en `TWILIO_WHATSAPP_FROM`
6. Tu número con prefijo whatsapp: va en `TWILIO_WHATSAPP_TO` (ej: `whatsapp:+51987654321`)

---

## Flujo del sistema

```
┌──────────┐     frame      ┌───────────────────┐   detecciones   ┌─────────────────┐
│  Cámara  │ ────────────→ │ DetectorRoboflow   │ ──────────────→ │  GestorAlertas  │
│ (webcam  │               │ (inference-sdk API) │                 │  (WhatsApp via  │
│ o video) │               └───────────────────┘                  │   Twilio)       │
└──────────┘                        │                              └─────────────────┘
                                    ↓                                      │
                             dibujar_detecciones                    capturas/ (jpg)
                             (utils.py)                                    │
                                    ↓                                      ↓
                             cv2.imshow(frame)                    WhatsApp message
```

---

## Uso

### FASE 1 — Probar los modelos (sin cámara)

```powershell
# Coloca 2-3 imágenes de prueba en data/
# (una con arma, una con rostro, una con placa)

python test_modelos.py
```

Salida esperada:
```
[INFO] Probando 3 modelos sobre 3 imagen(es)...

Imagen: arma.jpg
    [armas   ] 1 detección(es)
        - knife            conf=0.92
    [rostros ] 0 detección(es)
    [placas  ] 0 detección(es)
...
[OK] Prueba finalizada.
```

### FASE 2 — Sistema completo con alertas

```powershell
# Con la webcam predeterminada (índice 0)
python main.py

# Con una cámara específica
python main.py --source 1

# Con un archivo de video
python main.py --source video.mp4

# Solo detección de armas con alta confianza
python main.py --modelos armas --conf 0.60

# Los 3 modelos activos
python main.py --modelos armas rostros placas
```

Presiona **`q`** para salir.

### Pruebas unitarias

```powershell
pytest tests/ -v
```

---

## Argumentos de la CLI (`main.py`)

| Argumento     | Tipo   | Default       | Descripción                                          |
|---------------|--------|---------------|------------------------------------------------------|
| `--source`    | int/str| `0`           | Índice de webcam o ruta de archivo de video          |
| `--modelos`   | list   | `armas rostros`| Modelos a activar: `armas`, `rostros`, `placas`      |
| `--conf`      | float  | `0.40`        | Umbral mínimo de confianza para mostrar detecciones  |
| `--cooldown`  | int    | `30`          | Segundos mínimos entre alertas de WhatsApp           |
| `--intervalo` | float  | `1.0`         | Segundos entre llamadas a la API de Roboflow         |

---

## Checklist de fallos comunes

| Síntoma                              | Causa probable                                    | Solución                                          |
|--------------------------------------|---------------------------------------------------|---------------------------------------------------|
| `[ERROR CRÍTICO] Falta ROBOFLOW_API_KEY` | `.env` no creado o API key vacía              | Copiar `.env.example` → `.env` y completar key    |
| `No matching distribution for inference-sdk` | Python 3.13 instalado                    | Usar Python 3.11 o 3.12 para crear el venv        |
| No llega mensaje de WhatsApp          | Número no unido al sandbox de Twilio             | Enviar el código `join xxxx-yyyy` por WhatsApp    |
| `No se pudo abrir la fuente de video` | Cámara ocupada o índice incorrecto               | Probar `--source 1` o cerrar otras apps de cámara |
| Latencia alta / detecciones lentas    | Conexión a Internet lenta                        | Aumentar `--intervalo` (ej. `--intervalo 3.0`)   |
| `HTTP 403 Unauthorized`               | API key de Roboflow expirada/incorrecta          | Regenerar la API key en el panel de Roboflow      |
| Firewall bloquea conexión             | Red corporativa restringida                      | Probar con red móvil o VPN                        |

---

## Estructura del proyecto

```
SI904-M2/
├── config.py            # Carga .env + constantes + IDs de modelos
├── main.py              # Orquestador FASE 2 (webcam → detección → alertas)
├── test_modelos.py      # Script FASE 1 (prueba los 3 modelos con imágenes)
├── requirements.txt     # Dependencias (Python 3.10-3.12)
├── .env.example         # Plantilla de credenciales
├── src/
│   ├── detector.py      # DetectorRoboflow: llama a la API e interpreta predicciones
│   ├── alertas.py       # GestorAlertas: cooldown + captura + WhatsApp
│   ├── camara.py        # Camara: wrapper sobre cv2.VideoCapture
│   └── utils.py         # Logger, timestamps, carpetas, dibujo de cajas
├── data/                # Imágenes de prueba para FASE 1
├── capturas/            # Snapshots guardados al disparar alertas
├── tests/               # Pruebas unitarias con pytest
└── docs/                # Paper IEEE y diagramas
```

---

## Propuestas de mejora (FASE 3)

- **Modelos configurables desde `.env`**: añadir nuevos modelos sin tocar el código
- **Imagen por WhatsApp**: usar Twilio MediaUrl con una URL pública temporal (ngrok)
- **OCR en placas**: integrar EasyOCR o PaddleOCR como postproceso del modelo de placas
- **Interfaz web**: panel de control con Flask/FastAPI para ver capturas en tiempo real
