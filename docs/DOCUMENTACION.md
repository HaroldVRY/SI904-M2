# SecureVision AI — Documentación Técnica
## SI904 Seguridad de Sistemas · Universidad Nacional de Ingeniería

---

## 1. Descripción General

**SecureVision AI** es un sistema de vigilancia inteligente para seguridad ciudadana que detecta en tiempo real la presencia de armas, rostros y placas vehiculares mediante modelos de visión artificial alojados en Roboflow. Ante la detección de un arma, el sistema envía una alerta automática por WhatsApp al número de guardia configurado, activa una alarma sonora en el panel web y persiste el evento en una base de datos Supabase (PostgreSQL).

**Propósito:** Proveer a organismos de seguridad pública y privada una herramienta de monitoreo continuo, escalable y con notificación en tiempo real, sin requerir hardware especializado más allá de una webcam convencional.

**Valor diferencial:**
- Inferencia en la nube (Roboflow API) — sin GPU local requerida
- Alertas WhatsApp con validación de entrega (Twilio)
- Panel web accesible desde cualquier navegador en la misma red
- Persistencia histórica en Supabase con esquema relacional

---

## 2. Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────────┐
│                        CAPA DE CAPTURA                          │
│   Webcam / Fuente de video  →  src/camara.py (cv2.VideoCapture) │
└────────────────────────────────┬────────────────────────────────┘
                                 │ frame BGR
┌────────────────────────────────▼────────────────────────────────┐
│                      CAPA DE INFERENCIA                         │
│            src/detector.py  →  Roboflow API (HTTPS)             │
│   ┌──────────────┐  ┌───────────────────┐  ┌────────────────┐  │
│   │ weapon-qpfo8 │  │face-detection-yyxs│  │license-plate-w8│  │
│   └──────────────┘  └───────────────────┘  └────────────────┘  │
└────────────────────────────────┬────────────────────────────────┘
                                 │ lista de detecciones
┌────────────────────────────────▼────────────────────────────────┐
│                     CAPA DE DECISIÓN                            │
│   dashboard.py: _loop_camara()                                  │
│   ¿tipo == "armas" AND confianza >= umbral AND cooldown OK?     │
└──────┬─────────────────────────────────────────┬────────────────┘
       │ SÍ: alerta                              │ siempre
┌──────▼──────────────────┐          ┌───────────▼────────────────┐
│  CAPA DE NOTIFICACIÓN   │          │    CAPA DE PRESENTACIÓN     │
│  src/alertas.py         │          │    dashboard.py (Flask)     │
│  Twilio WhatsApp API    │          │    Stream MJPEG  /video_feed│
│  Guardar captura .jpg   │          │    Eventos SSE   /events    │
│  Alarma Web Audio API   │          │    API REST      /api/*     │
└──────┬──────────────────┘          └───────────┬────────────────┘
       │                                         │
┌──────▼─────────────────────────────────────────▼────────────────┐
│                     CAPA DE PERSISTENCIA                        │
│   src/database.py  →  Supabase (PostgreSQL en la nube)          │
│   sesiones / detecciones / alertas_whatsapp                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Estructura del Proyecto

```
SI904-M2/
├── dashboard.py              # Servidor Flask principal + bucle de cámara
├── main.py                   # Punto de entrada alternativo (CLI)
├── config.py                 # Variables de configuración globales
├── requirements.txt          # Dependencias Python
├── .env                      # Credenciales y configuración (NO versionar)
│
├── src/
│   ├── __init__.py
│   ├── camara.py             # Wrapper de cv2.VideoCapture
│   ├── detector.py           # Motor de detección Roboflow
│   ├── alertas.py            # Gestor de alertas WhatsApp (Twilio)
│   ├── database.py           # Integración Supabase (PostgreSQL)
│   └── utils.py              # Dibujo de detecciones y logger
│
├── templates/
│   ├── index.html            # Dashboard SPA (Landing + Monitor + Testing)
│   └── login.html            # Página de autenticación
│
├── static/
│   └── img/
│       ├── hero.png          # Imagen hero de la landing page
│       └── detection.png     # Imagen demo de detecciones
│
├── docs/
│   ├── DOCUMENTACION.md      # Este archivo
│   ├── REQUERIMIENTOS.md     # Especificación de requerimientos
│   ├── schema_supabase.sql   # Script SQL para crear las tablas en Supabase
│   └── diagramas/            # Diagramas de arquitectura
│
├── tests/
│   └── test_*.py             # Suite de pruebas unitarias (10/10)
│
└── capturas/                 # Imágenes guardadas al disparar alertas
```

---

## 4. Instalación y Configuración

### 4.1 Requisitos del sistema

| Requisito | Versión mínima | Notas |
|---|---|---|
| Python | 3.9 — 3.12 | inference-sdk NO soporta Python 3.13+ |
| Webcam | Cualquier USB/integrada | Índice configurable (default: 0) |
| Conexión a Internet | Permanente | Roboflow API + Twilio + Supabase |
| Memoria RAM | 4 GB | Recomendado 8 GB |
| SO | Windows 10+ / Ubuntu 20.04+ | Probado en Windows 11 |

### 4.2 Instalación de dependencias

```powershell
# Crear entorno virtual
python -m venv venv
.\venv\Scripts\activate   # Windows
# source venv/bin/activate  # Linux/Mac

# Instalar dependencias
pip install -r requirements.txt
```

### 4.3 Variables de entorno (.env)

Crear el archivo `.env` en la raíz del proyecto con las siguientes variables:

| Variable | Descripción | Ejemplo |
|---|---|---|
| `ROBOFLOW_API_KEY` | API Key de Roboflow | `slpWABkeOQ5xdjdXPW8w` |
| `ROBOFLOW_MODEL_ARMAS` | ID del modelo de armas | `weapon-qpfo8/1` |
| `ROBOFLOW_MODEL_ROSTROS` | ID del modelo de rostros | `face-detection-yyxs8/2` |
| `ROBOFLOW_MODEL_PLACAS` | ID del modelo de placas | `license-plate-w8chc/1` |
| `CONF_THRESHOLD` | Umbral de confianza mínimo | `0.40` |
| `COOLDOWN_SEGUNDOS` | Segundos entre alertas del mismo tipo | `30` |
| `INTERVALO_INFERENCIA` | Segundos entre ciclos de inferencia | `1` |
| `TWILIO_ACCOUNT_SID` | SID de cuenta Twilio | `ACxxxxxxxxxxxx` |
| `TWILIO_AUTH_TOKEN` | Token de autenticación Twilio | `05ea00d92d...` |
| `TWILIO_WHATSAPP_FROM` | Número Twilio sandbox | `whatsapp:+14155238886` |
| `TWILIO_WHATSAPP_TO` | Número de guardia receptor | `whatsapp:+51914027388` |
| `SUPABASE_URL` | URL del proyecto Supabase | `https://xxx.supabase.co` |
| `SUPABASE_KEY` | API Key de Supabase (anon o service_role) | `eyJ...` |
| `DASHBOARD_USER` | Usuario del panel web | `admin` |
| `DASHBOARD_PASS` | Contraseña del panel web | `securevision2026` |
| `DASHBOARD_SECRET_KEY` | Clave secreta para cookies Flask | `sv_k3y_si904_uni_2026` |

---

## 5. Módulos del Sistema

### 5.1 `src/detector.py` — Motor de Detección

Clase `DetectorRoboflow` que encapsula la comunicación con la Roboflow Inference API.

**Responsabilidades:**
- Inicializar el cliente `InferenceHTTPClient` con la API Key configurada
- Ejecutar inferencia paralela sobre los modelos seleccionados para cada frame
- Filtrar detecciones por umbral de confianza (`CONF_THRESHOLD`)
- Normalizar el resultado al formato estándar del proyecto: `{tipo, clase, confianza, x1, y1, x2, y2}`

**Método principal:**
```python
def inferir(self, frame: np.ndarray, modelos: list[str]) -> list[dict]:
    """
    Ejecuta inferencia sobre el frame con los modelos indicados.
    Retorna lista de detecciones filtradas por umbral.
    """
```

### 5.2 `src/alertas.py` — Gestor de Alertas WhatsApp

Clase `GestorAlertas` que controla el envío de mensajes Twilio.

**Responsabilidades:**
- Verificar que el cooldown haya transcurrido antes de enviar una alerta
- Guardar una captura del frame en `capturas/` con timestamp
- Enviar mensaje WhatsApp estructurado via Twilio API
- Actualizar el timestamp de la última alerta enviada

**Lógica de cooldown:**
```
tiempo_actual - ultima_alerta_ts >= COOLDOWN_SEGUNDOS  →  enviar
tiempo_actual - ultima_alerta_ts <  COOLDOWN_SEGUNDOS  →  silenciar
```

### 5.3 `src/camara.py` — Captura de Video

Clase `Camara` como context manager sobre `cv2.VideoCapture`.

**Responsabilidades:**
- Abrir y liberar correctamente el recurso de cámara
- Proveer método `leer_frame()` que retorna el frame en BGR o `None` si falla

### 5.4 `src/database.py` — Persistencia en Supabase

Módulo de integración con Supabase (PostgreSQL en la nube).

**Funciones principales:**

| Función | Descripción |
|---|---|
| `iniciar_sesion(modelos, fuente, conf)` | Crea fila en `sesiones`, retorna el ID |
| `cerrar_sesion(id, frames, alertas)` | Actualiza métricas finales de la sesión |
| `registrar_detecciones_lote(id, dets, flag)` | Insert masivo en `detecciones` |
| `registrar_alerta_whatsapp(...)` | Registra alerta enviada en `alertas_whatsapp` |
| `obtener_sesiones(limite)` | Consulta historial de sesiones |

**Tolerancia a fallos:** Si `SUPABASE_URL` o `SUPABASE_KEY` no están configurados, todas las funciones retornan `None`/`False` silenciosamente sin interrumpir el sistema.

### 5.5 `src/utils.py` — Utilidades

**Funciones:**
- `dibujar_detecciones(frame, detecciones)` — Dibuja cajas delimitadoras codificadas por color sobre el frame
- `obtener_logger(nombre)` — Retorna logger configurado con formato timestamp

**Código de colores:**

| Tipo | Color | RGB |
|---|---|---|
| `armas` | Rojo | (0, 0, 220) |
| `rostros` | Verde | (0, 200, 0) |
| `placas` | Naranja | (0, 140, 255) |

### 5.6 `dashboard.py` — Servidor Web Flask

Módulo principal que integra todos los componentes.

**Componentes internos:**
- `_estado` — Diccionario global con métricas de la sesión actual (protegido por `threading.Lock`)
- `_loop_camara()` — Hilo daemon de captura + inferencia + notificación
- `_eventos_q` — Cola SSE para eventos en tiempo real (máx. 200 elementos)
- `_ultimo_frame_jpg` — Buffer del último frame codificado como JPEG

---

## 6. API REST del Dashboard

| Endpoint | Método | Auth | Descripción | Respuesta |
|---|---|---|---|---|
| `/` | GET | ✅ Requerida | Sirve el dashboard HTML (SPA) | HTML |
| `/login` | GET | ❌ Pública | Formulario de inicio de sesión | HTML |
| `/login` | POST | ❌ Pública | Valida credenciales y crea sesión | Redirect |
| `/logout` | GET | ✅ Requerida | Destruye la sesión Flask | Redirect a /login |
| `/video_feed` | GET | ✅ Requerida | Stream MJPEG con anotaciones en vivo | `multipart/x-mixed-replace` |
| `/events` | GET | ✅ Requerida | Server-Sent Events de detecciones y alertas | `text/event-stream` |
| `/api/stats` | GET | ✅ Requerida | Estadísticas de la sesión actual | JSON |
| `/api/alerts` | GET | ✅ Requerida | Historial de las últimas 50 alertas | JSON array |
| `/api/control` | POST | ✅ Requerida | Iniciar / detener el sistema | JSON `{ok, mensaje}` |
| `/api/test-image` | POST | ✅ Requerida | Inferencia sobre imagen subida | JSON `{imagen_b64, detecciones, total}` |

### Formato `/api/stats`
```json
{
  "activo": true,
  "frames": 1240,
  "det_armas": 3,
  "det_rostros": 87,
  "det_placas": 0,
  "alertas_total": 1,
  "personas_en_pantalla": 2,
  "uptime": "02:04",
  "modelos": ["armas", "rostros"],
  "conf": 0.40,
  "cooldown": 30
}
```

### Formato evento SSE
```json
// Detección
{"tipo": "deteccion", "datos": {"ts": "14:35:22", "detecciones": [{"tipo": "armas", "clase": "knife", "conf": 0.65}]}}

// Alerta
{"tipo": "alerta", "datos": {"ts": "14/06/2026 14:35:22", "items": [{"tipo": "armas", "clase": "knife", "conf": 0.65}]}}
```

---

## 7. Modelos de Inteligencia Artificial

### 7.1 Modelo de Armas — `weapon-qpfo8`

| Atributo | Valor |
|---|---|
| ID Roboflow | `weapon-qpfo8/1` |
| Clases detectadas | `knife`, `pistol`, `rifle`, `gun` |
| Confianza validada en prueba | 65% (knife) |
| Umbral mínimo configurado | 40% |
| Dispara alerta WhatsApp | **SÍ** |
| Dispara alarma sonora | **SÍ** |

### 7.2 Modelo de Rostros — `face-detection-yyxs8`

| Atributo | Valor |
|---|---|
| ID Roboflow | `face-detection-yyxs8/2` |
| Clases detectadas | `Face` |
| Confianza validada en prueba | 87% |
| Umbral mínimo configurado | 40% |
| Dispara alerta WhatsApp | No |
| Uso | Conteo de personas, registro de presencia |

### 7.3 Modelo de Placas — `license-plate-w8chc`

| Atributo | Valor |
|---|---|
| ID Roboflow | `license-plate-w8chc/1` |
| Clases detectadas | `license-plate`, `plate` |
| Confianza validada en prueba | 92% |
| Umbral mínimo configurado | 40% |
| Dispara alerta WhatsApp | No |
| Extensión futura | OCR con EasyOCR para leer texto alfanumérico |

---

## 8. Lógica de Alertas WhatsApp

```
Frame capturado
      │
      ▼
Se ejecuta inferencia  ──► Sin detecciones ──► Solo dibuja frame, continúa
      │
      ▼
¿Hay detecciones con tipo = "armas"?
      │
      ├── NO ──► Dibuja cajas (verde/naranja), registra en BD, continúa
      │
      └── SÍ ──► ¿Tiempo desde última alerta >= COOLDOWN (30s)?
                        │
                        ├── NO ──► Cooldown activo, silencia alerta
                        │          (caja roja visible, sin WhatsApp)
                        │
                        └── SÍ ──► 1. Guarda captura en capturas/*.jpg
                                   2. Envía mensaje WhatsApp via Twilio
                                   3. Registra en BD (alertas_whatsapp)
                                   4. Emite evento SSE "alerta" al dashboard
                                   5. Dispara alarma sonora (Web Audio API)
                                   6. Actualiza timestamp de última alerta
```

**Formato del mensaje WhatsApp enviado:**
```
🚨 ALERTA DE SEGURIDAD 🚨
📅 28/06/2026 14:35:22
🔫 ARMAS detectado(s):
   • knife (65.0%)
👤 ROSTROS detectado(s):
   • Face (87.0%)
📸 Captura guardada: alerta_20260628_143522.jpg
```

---

## 9. Base de Datos Supabase

### 9.1 Esquema de Tablas

**Tabla `sesiones`**
```sql
CREATE TABLE sesiones (
  id                BIGSERIAL PRIMARY KEY,
  inicio            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  fin               TIMESTAMPTZ,
  total_frames      INTEGER      DEFAULT 0,
  total_alertas     INTEGER      DEFAULT 0,
  modelos_activos   TEXT[]       NOT NULL DEFAULT '{armas,rostros}',
  fuente_video      TEXT         DEFAULT '0',
  conf_threshold    NUMERIC(4,2) DEFAULT 0.40
);
```

**Tabla `detecciones`**
```sql
CREATE TABLE detecciones (
  id              BIGSERIAL PRIMARY KEY,
  sesion_id       BIGINT       REFERENCES sesiones(id) ON DELETE CASCADE,
  detectado_en    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
  tipo            TEXT         NOT NULL CHECK (tipo IN ('armas','rostros','placas')),
  clase           TEXT         NOT NULL,
  confianza       NUMERIC(5,4) NOT NULL,
  x1 INTEGER, y1 INTEGER, x2 INTEGER, y2 INTEGER,
  disparo_alerta  BOOLEAN      DEFAULT FALSE
);
```

**Tabla `alertas_whatsapp`**
```sql
CREATE TABLE alertas_whatsapp (
  id               BIGSERIAL PRIMARY KEY,
  sesion_id        BIGINT       REFERENCES sesiones(id) ON DELETE CASCADE,
  enviada_en       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
  numero_destino   TEXT         NOT NULL,
  estado           TEXT         DEFAULT 'enviada',
  twilio_sid       TEXT,
  mensaje_texto    TEXT,
  detecciones_json JSONB
);
```

### 9.2 Flujo de datos — qué se guarda cuándo

| Evento | Operación en BD |
|---|---|
| Presionar **Iniciar** en el dashboard | `INSERT` en `sesiones` → se obtiene `sesion_id` |
| Cada ciclo de inferencia con detecciones | `INSERT` masivo en `detecciones` (lote) |
| Detección de arma que supera cooldown | `INSERT` en `alertas_whatsapp` |
| Presionar **Detener** en el dashboard | `UPDATE` en `sesiones` con `total_frames`, `total_alertas` y `fin` |

---

## 10. Panel de Control Web

### 10.1 Tab: Inicio (Landing Page)
Página de presentación del producto con: hero section, strip de estadísticas clave, grilla de 6 características, diagrama de arquitectura, tarjetas de los 3 modelos con métricas de validación, imagen demo de detecciones, stack tecnológico y footer institucional.

### 10.2 Tab: Monitor en Vivo
- **Stats bar (6 tarjetas):** Frames, Personas en pantalla, Armas detectadas, Rostros, Placas, Alertas WhatsApp
- **Feed MJPEG:** Stream de video en tiempo real con cajas delimitadoras coloreadas
- **Panel de control:** Toggles de modelos, sliders de confianza/cooldown/intervalo, selector de fuente, botones Iniciar/Detener
- **Registro de detecciones:** Feed SSE de eventos en tiempo real con scroll interno fijo

### 10.3 Tab: Testing de Modelos
- **Zona de carga:** Drag & drop o selección de archivos (JPG/PNG/BMP/WEBP)
- **Configuración:** Selección de modelos a evaluar + slider de confianza
- **Resultado:** Imagen anotada con cajas, lista detallada de detecciones con clase/confianza/coordenadas
- **Descarga:** Botón para exportar la imagen anotada como JPEG

### 10.4 Autenticación
- Formulario en `/login` con usuario y contraseña
- Sesión gestionada con cookies Flask (server-side)
- Todas las rutas protegidas con decorador `@requires_auth`
- Credenciales en `.env`: `DASHBOARD_USER` y `DASHBOARD_PASS`
- **Credenciales por defecto:** `admin` / `securevision2026`
- Botón "Salir" en el header para cerrar sesión

---

## 11. Sistema de Alarma Sonora

Implementado mediante la **Web Audio API** nativa del navegador, sin dependencias externas ni archivos de audio.

**Cómo funciona:**
```javascript
// Al recibir evento SSE de tipo "alerta", se ejecuta:
function playAlarm() {
  const ctx = new AudioContext();
  const pitches = [880, 660, 880];  // 3 pitidos en Hz
  pitches.forEach((freq, i) => {
    const osc = ctx.createOscillator();
    osc.type = 'square';            // onda cuadrada (sonido agudo)
    osc.frequency.value = freq;
    // envolvente de amplitud: fade in / fade out rápido
    osc.start(ctx.currentTime + i * 0.28);
    osc.stop(ctx.currentTime + i * 0.28 + 0.25);
  });
}
```

**Control desde el dashboard:** Botón "Alarma: ON / OFF" en el header. El estado de mute se conserva mientras la sesión del navegador esté abierta.

---

## 12. Ejecución del Sistema

```powershell
# 1. Activar entorno virtual
.\venv\Scripts\activate

# 2. Iniciar el dashboard
.\venv\Scripts\python.exe dashboard.py

# 3. Abrir en el navegador
#    http://127.0.0.1:5001
#    Credenciales: admin / securevision2026

# 4. Para correr los tests unitarios
.\venv\Scripts\python.exe -m pytest tests/ -v
```

**El sistema también abre el navegador automáticamente** tras 1.5 segundos de iniciado.

---

## 13. Tests Unitarios

Suite de 10 pruebas que validan los componentes principales:

```
tests/
├── test_detector.py     # Validación de umbral, formato de detecciones, modelos vacíos
├── test_alertas.py      # Cooldown, envío Twilio, guardado de captura
├── test_camara.py       # Apertura/cierre, lectura de frames
└── test_utils.py        # Dibujo de detecciones, logger
```

**Resultado:**
```
======================== 10 passed in X.XXs ========================
```

Comando: `.\venv\Scripts\python.exe -m pytest tests/ -v`

---

## 14. Limitaciones y Trabajo Futuro

| Funcionalidad | Estado | Descripción |
|---|---|---|
| OCR en placas | Pendiente | Integrar EasyOCR para leer texto alfanumérico de las placas detectadas. No requiere reentrenar el modelo de Roboflow. |
| Múltiples cámaras | Pendiente | Simulación con archivos `.mp4` en bucle mediante `cap.set(CAP_PROP_POS_FRAMES, 0)`. Grid de N streams en el dashboard. |
| Integración Telegram | Opcional | El canal WhatsApp cumple el requerimiento "y/o". Telegram agregaría canal redundante. |
| Grabación automática | Pendiente | Guardar clip de video de ±5s al detectar un arma usando `cv2.VideoWriter`. |
| Reporte exportable PDF | Pendiente | Exportar historial de sesión con detecciones y alertas en formato PDF. |
| Panel de historial BD | Pendiente | Tab adicional en el dashboard para consultar sesiones pasadas desde Supabase. |
