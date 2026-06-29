# Especificación de Requerimientos — SecureVision AI
## SI904 Seguridad de Sistemas · Trabajo Monográfico 02
### Universidad Nacional de Ingeniería

---

## 1. Introducción

### 1.1 Propósito
Este documento especifica los requerimientos funcionales, no funcionales y técnicos del sistema **SecureVision AI**, desarrollado como Trabajo Monográfico 02 del curso SI904 — Seguridad de Sistemas. El objetivo es establecer un contrato claro entre los requerimientos del enunciado y la implementación entregada.

### 1.2 Alcance
El sistema cubre el monitoreo en tiempo real de una o más fuentes de video, la detección automática de amenazas (armas, rostros, placas), la notificación inmediata por WhatsApp ante la detección de armas, y la persistencia de todos los eventos en una base de datos relacional en la nube.

### 1.3 Definiciones y Acrónimos

| Término | Definición |
|---|---|
| API | Application Programming Interface — interfaz de comunicación entre servicios |
| Cooldown | Período mínimo entre alertas del mismo tipo para evitar saturación |
| MJPEG | Motion JPEG — protocolo de streaming de video frame a frame |
| OCR | Optical Character Recognition — reconocimiento de texto en imágenes |
| RLS | Row Level Security — control de acceso por fila en PostgreSQL |
| SSE | Server-Sent Events — protocolo de notificaciones push unidireccionales |
| Umbral | Porcentaje mínimo de confianza para aceptar una detección como válida |
| Roboflow | Plataforma de modelos de visión artificial en la nube |
| Twilio | Plataforma de comunicaciones API (SMS, WhatsApp, llamadas) |
| Supabase | Base de datos PostgreSQL en la nube con API REST integrada |
| Flask | Framework web minimalista para Python |
| OpenCV | Librería de visión por computadora (captura y procesamiento de video) |

---

## 2. Descripción General

### 2.1 Perspectiva del producto
SecureVision AI es un sistema standalone que se ejecuta localmente en un servidor o PC con webcam, exponiendo un panel web accesible desde la red local. Se integra con tres servicios externos: Roboflow (inferencia de IA), Twilio (WhatsApp) y Supabase (base de datos).

```
[Webcam] → [SecureVision AI] → [Roboflow API]
                ↓                      ↓
         [Panel Web]            [Detecciones]
                ↓                      ↓
         [Twilio API]          [Supabase DB]
                ↓
         [WhatsApp Guardia]
```

### 2.2 Usuarios del sistema

| Tipo de usuario | Rol | Acceso |
|---|---|---|
| **Operador de Seguridad** | Monitorea el feed en vivo, recibe alertas WhatsApp, puede iniciar/detener el sistema | Panel web — Tab Monitor |
| **Administrador del Sistema** | Configura credenciales en `.env`, gestiona modelos activos, realiza pruebas de validación | Panel web — Todos los tabs + acceso directo a `.env` |

### 2.3 Restricciones y supuestos

- El sistema asume conexión a Internet permanente para las APIs externas.
- La detección funciona con cualquier webcam USB o integrada.
- El número receptor de WhatsApp debe haberse unido al sandbox de Twilio previamente.
- Python debe ser versión 3.9–3.12 (incompatibilidad de `inference-sdk` con 3.13+).
- Las credenciales sensibles nunca deben commitearse a repositorios públicos.

---

## 3. Requerimientos Funcionales

| ID | Nombre | Descripción | Prioridad | Estado |
|---|---|---|---|---|
| **RF-01** | Autenticación de usuario | El sistema requiere login con usuario y contraseña para acceder al panel web. Las credenciales se gestionan en `.env`. La sesión se destruye al hacer logout. | Alta | ✅ Implementado |
| **RF-02** | Detección de armas en tiempo real | El sistema detecta cuchillos, pistolas, rifles y objetos cortantes en el feed de video usando el modelo Roboflow `weapon-qpfo8/1`. La detección se realiza cada N segundos configurables. | Alta | ✅ Implementado |
| **RF-03** | Detección de rostros en tiempo real | El sistema identifica y localiza rostros humanos en el encuadre usando el modelo `face-detection-yyxs8/2`. Se muestra con caja verde y se contabilizan como "personas en pantalla". | Alta | ✅ Implementado |
| **RF-04** | Detección de placas vehiculares | El sistema localiza placas de vehículos usando el modelo `license-plate-w8chc/1`. Se muestra con caja naranja. | Media | ✅ Implementado |
| **RF-05** | Alertas por WhatsApp | Al detectar un arma con confianza >= umbral, el sistema envía un mensaje de alerta estructurado al número configurado vía Twilio WhatsApp API. | Alta | ✅ Implementado |
| **RF-06** | Panel de control web en tiempo real | Interfaz web accesible en http://localhost:5001 con stream de video, estadísticas, historial de alertas y controles del sistema. Sin necesidad de instalar software adicional en el cliente. | Alta | ✅ Implementado |
| **RF-07** | Stream de video con anotaciones | El feed de cámara se transmite como MJPEG con cajas delimitadoras dibujadas sobre cada objeto detectado, codificadas por color según tipo. | Alta | ✅ Implementado |
| **RF-08** | Alarma sonora ante alertas | Al recibir una detección de arma que dispara alerta, el navegador emite una alarma sonora de 3 pitidos usando Web Audio API. Se puede silenciar desde el header del dashboard. | Media | ✅ Implementado |
| **RF-09** | Conteo de personas en pantalla | El dashboard muestra en tiempo real cuántos rostros hay en el frame actual (no acumulado). Se actualiza con cada ciclo de inferencia. | Media | ✅ Implementado |
| **RF-10** | Testing con imágenes estáticas | El tab "Testing de Modelos" permite cargar imágenes locales (JPG/PNG/BMP/WEBP), seleccionar modelos y umbral, y recibir la imagen anotada con resultados de detección. | Media | ✅ Implementado |
| **RF-11** | Persistencia en base de datos | Todas las sesiones, detecciones individuales y alertas WhatsApp se guardan en Supabase (PostgreSQL). La BD se activa/desactiva según presencia de credenciales en `.env`. | Media | ✅ Implementado |
| **RF-12** | Historial de alertas en sesión | El panel web mantiene un registro de las últimas 50 detecciones y alertas de la sesión actual, con scroll interno sin afectar el layout del video. | Baja | ✅ Implementado |
| **RF-13** | Control de cooldown | El sistema evita saturar WhatsApp con alertas repetidas: el parámetro `COOLDOWN_SEGUNDOS` (default 30s) controla el tiempo mínimo entre alertas consecutivas. | Alta | ✅ Implementado |
| **RF-14** | Configuración dinámica | El operador puede ajustar desde el dashboard los modelos activos, umbral de confianza, cooldown, intervalo de inferencia y fuente de video sin reiniciar el servidor. | Media | ✅ Implementado |
| **RF-15** | Descarga de imagen anotada | En el tab Testing, el resultado del análisis puede descargarse como archivo JPEG con las anotaciones dibujadas. | Baja | ✅ Implementado |
| **RF-16** | OCR en placas vehiculares | Lectura del texto alfanumérico de la placa detectada usando EasyOCR sobre el recorte del bounding box. No requiere reentrenar el modelo de Roboflow. | Media | ⏳ Pendiente |
| **RF-17** | Integración con Telegram | Envío de alertas adicionales por Telegram Bot API como canal redundante. | Baja | ℹ️ Opcional — WhatsApp cumple el requisito "y/o" del enunciado |
| **RF-18** | Simulación de múltiples cámaras | Reproducción de archivos `.mp4` en bucle como cámaras virtuales independientes, con grid de N streams en el dashboard. | Baja | ⏳ Pendiente |
| **RF-19** | Reporte exportable PDF | Generación de informe PDF con estadísticas de sesión, listado de detecciones y alertas, gráficos de actividad. | Baja | ⏳ Pendiente |

---

## 4. Requerimientos No Funcionales

| ID | Nombre | Descripción | Métrica |
|---|---|---|---|
| **RNF-01** | Rendimiento | La latencia desde la detección de un arma hasta el envío del WhatsApp no debe superar 2 segundos. El stream de video debe mantener mínimo 15 fps. | Latencia < 2s · FPS ≥ 15 |
| **RNF-02** | Disponibilidad | El sistema debe poder operar en modo continuo 24/7 con reinicio automático del hilo de cámara ante fallos de frame. El cooldown configurable evita saturación de alertas. | Uptime = 24/7 mientras el proceso esté activo |
| **RNF-03** | Seguridad | Todas las credenciales (API keys, contraseñas, tokens) se almacenan en `.env` y nunca se incluyen en el código fuente. El panel web requiere autenticación. Las rutas de la API solo responden a sesiones válidas. | 0 credenciales hardcodeadas · Todas las rutas protegidas |
| **RNF-04** | Escalabilidad | Los modelos de detección son configurables via `.env` sin modificar código. Se pueden añadir nuevos modelos de Roboflow extendiendo el parámetro `ROBOFLOW_MODEL_*`. | Nuevo modelo en < 5 min sin recodificar |
| **RNF-05** | Portabilidad | El sistema funciona en Windows 10+, Ubuntu 20.04+ y macOS 12+ con Python 3.9–3.12. No requiere GPU ni hardware especializado. | Compatible con 3 SO principales |
| **RNF-06** | Mantenibilidad | El código está organizado en capas (camara, detector, alertas, database, utils). Los 10 tests unitarios deben pasar al 100% antes de cualquier despliegue. | 10/10 tests · Arquitectura por capas |
| **RNF-07** | Tolerancia a fallos | Si Supabase no está disponible o las credenciales son incorrectas, el sistema sigue operando con todas sus funciones excepto la persistencia. La BD desactivada no detiene el monitoreo. | Sistema operativo sin BD configurada |

---

## 5. Requerimientos Técnicos

| Componente | Tecnología | Versión | Justificación |
|---|---|---|---|
| Lenguaje base | Python | 3.11.6 | Amplia compatibilidad, ecosistema ML maduro |
| Servidor web | Flask | 3.1.3 | Minimalista, threading nativo, ideal para MJPEG/SSE |
| Captura de video | OpenCV (cv2) | 4.10.0.84 | Estándar industrial para procesamiento de frames |
| Inferencia de IA | inference-sdk (Roboflow) | 1.3.2 | API unificada para todos los modelos Roboflow |
| Alertas WhatsApp | twilio | 9.10.9 | API WhatsApp empresarial con validación de entrega |
| Base de datos | supabase-py | 2.31.0 | PostgreSQL gestionado en la nube, API REST incluida |
| Autenticación | Flask sessions | Nativo | Cookies server-side sin dependencias adicionales |
| Streaming video | MJPEG | Nativo HTTP | Compatible con todos los navegadores modernos |
| Eventos tiempo real | Server-Sent Events (SSE) | Nativo HTTP | Push unidireccional eficiente para el feed de alertas |
| Alarma sonora | Web Audio API | Nativo navegador | Sin archivos de audio externos, latencia mínima |
| Tests unitarios | pytest | 8.3.4 | Framework de testing estándar Python |
| Variables entorno | python-dotenv | 1.0.1 | Separación de configuración y código |

---

## 6. Casos de Uso Principales

### CU-01: Iniciar sesión de monitoreo

| Campo | Detalle |
|---|---|
| **Actor** | Operador de Seguridad |
| **Precondiciones** | El dashboard está corriendo en http://127.0.0.1:5001. El operador tiene credenciales válidas. |
| **Flujo principal** | 1. Operador abre el navegador y navega a http://127.0.0.1:5001 · 2. El sistema redirige a /login · 3. Operador ingresa usuario y contraseña · 4. El sistema valida credenciales contra `.env` · 5. El sistema crea sesión Flask y redirige al dashboard · 6. Operador selecciona modelos activos, ajusta umbrales · 7. Operador presiona "Iniciar" · 8. El sistema crea sesión en Supabase y arranca el hilo de cámara · 9. El feed de video se activa en el panel |
| **Flujo alternativo** | 3a. Credenciales incorrectas → se muestra mensaje de error, se mantiene en /login |
| **Postcondiciones** | Sistema activo, sesión creada en Supabase, stream MJPEG disponible |

---

### CU-02: Detección y alerta de arma

| Campo | Detalle |
|---|---|
| **Actor** | Sistema (automático) |
| **Precondiciones** | El monitoreo está activo (CU-01 completado). Un arma aparece en el campo visual de la cámara. |
| **Flujo principal** | 1. El hilo de cámara captura un frame · 2. El frame se envía al modelo `weapon-qpfo8` en Roboflow · 3. Roboflow retorna detección con confianza >= 40% · 4. El sistema verifica que han pasado >= 30s desde la última alerta · 5. El sistema guarda captura `.jpg` en `capturas/` · 6. Twilio envía mensaje WhatsApp al número de guardia · 7. El sistema registra la alerta en Supabase (`alertas_whatsapp`) · 8. El evento SSE "alerta" se emite al dashboard · 9. El dashboard muestra la alerta en rojo y suena la alarma sonora |
| **Flujo alternativo** | 4a. Cooldown activo → se omite WhatsApp, la caja roja sigue visible en pantalla |
| **Postcondiciones** | Alerta en WhatsApp entregada, evento registrado en BD, alarma sonora emitida |

---

### CU-03: Testing de imagen estática

| Campo | Detalle |
|---|---|
| **Actor** | Administrador del Sistema |
| **Precondiciones** | Usuario autenticado en el dashboard. Tiene una imagen local (JPG/PNG/WEBP). |
| **Flujo principal** | 1. Administrador navega al tab "Testing de Modelos" · 2. Arrastra o selecciona la imagen desde el sistema de archivos · 3. Selecciona modelos a evaluar y ajusta umbral de confianza · 4. Presiona "Analizar Imagen" · 5. El sistema envía la imagen a Roboflow vía `POST /api/test-image` · 6. El servidor retorna la imagen anotada en base64 y la lista de detecciones · 7. El dashboard muestra la imagen con cajas y la tabla de resultados · 8. Administrador puede descargar la imagen anotada |
| **Flujo alternativo** | 5a. Error de Roboflow → mensaje de error mostrado en pantalla |
| **Postcondiciones** | Imagen analizada y resultado presentado. Sin impacto en la BD ni alertas. |

---

### CU-04: Consultar historial de alertas

| Campo | Detalle |
|---|---|
| **Actor** | Operador de Seguridad |
| **Precondiciones** | Operador autenticado. El monitoreo ha estado activo en sesiones anteriores. |
| **Flujo principal** | 1. Operador está en el tab Monitor · 2. Observa el panel "Registro de Detecciones" con el feed SSE · 3. Para ver historial completo, accede a Supabase Table Editor → `alertas_whatsapp` o ejecuta `GET /api/alerts` |
| **Postcondiciones** | Operador informado del historial de la sesión actual |

---

## 7. Restricciones

| # | Restricción |
|---|---|
| R-01 | Python debe ser versión 3.9 a 3.12 inclusive. `inference-sdk` tiene incompatibilidad declarada con Python 3.13+. |
| R-02 | El sistema requiere conexión a Internet activa para: Roboflow API (inferencia), Twilio (WhatsApp), Supabase (BD). |
| R-03 | El número receptor de WhatsApp debe haber enviado el código de opt-in al sandbox de Twilio (`join <palabra>`) antes de recibir mensajes. |
| R-04 | La primera llamada a la API de Roboflow puede tardar 2–5 segundos adicionales por inicialización del modelo en frío. Las llamadas subsiguientes son más rápidas. |
| R-05 | La clave Supabase `anon` tiene Row Level Security activo por defecto. Se debe usar `service_role` o deshabilitar RLS manualmente para operaciones backend. |
| R-06 | El panel web no está diseñado para exposición pública directa a Internet. Usar en red local o detrás de un proxy inverso (nginx) con HTTPS para ambientes reales. |

---

## 8. Matriz de Trazabilidad

| ID Requerimiento | Módulo Implementador | Función/Clase Principal | Estado |
|---|---|---|---|
| RF-01 | `dashboard.py` | `login()`, `logout()`, `requires_auth()` | ✅ |
| RF-02 | `src/detector.py` | `DetectorRoboflow.inferir()` + modelo `weapon-qpfo8` | ✅ |
| RF-03 | `src/detector.py` | `DetectorRoboflow.inferir()` + modelo `face-detection-yyxs8` | ✅ |
| RF-04 | `src/detector.py` | `DetectorRoboflow.inferir()` + modelo `license-plate-w8chc` | ✅ |
| RF-05 | `src/alertas.py` | `GestorAlertas.disparar()` + Twilio API | ✅ |
| RF-06 | `dashboard.py` + `templates/index.html` | `index()`, routes Flask, SPA | ✅ |
| RF-07 | `dashboard.py` | `video_feed()` MJPEG + `dibujar_detecciones()` | ✅ |
| RF-08 | `templates/index.html` | `playAlarm()` Web Audio API | ✅ |
| RF-09 | `dashboard.py` | `_loop_camara()` → `personas_en_pantalla` en `_estado` | ✅ |
| RF-10 | `dashboard.py` + `templates/index.html` | `api_test_image()` POST | ✅ |
| RF-11 | `src/database.py` | `iniciar_sesion()`, `registrar_detecciones_lote()`, `registrar_alerta_whatsapp()` | ✅ |
| RF-12 | `dashboard.py` + `templates/index.html` | `_alertas_historial`, SSE feed | ✅ |
| RF-13 | `src/alertas.py` | `GestorAlertas.disparar()` — lógica de cooldown | ✅ |
| RF-14 | `dashboard.py` + `templates/index.html` | `api_control()` POST, sliders/toggles del dashboard | ✅ |
| RF-15 | `templates/index.html` | `descargar()` JS, base64 JPEG | ✅ |
| RF-16 | — | EasyOCR sobre crop del bounding box de placa | ⏳ Pendiente |
| RF-17 | — | Telegram Bot API como canal adicional | ℹ️ Opcional |
| RF-18 | — | `cv2.VideoCapture` con archivos `.mp4` + loop | ⏳ Pendiente |
| RF-19 | — | Librería reportlab o weasyprint para PDF | ⏳ Pendiente |
