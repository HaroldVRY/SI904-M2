# PROMPTS para Claude Code — Roboflow + WhatsApp (de inicio a fin)

Ejecuta en orden, **un prompt por turno**, revisando cada resultado. El
`CLAUDE.md` ya tiene el contexto, así que no hace falta repetirlo. Haz commit
después de cada prompt que deje el proyecto ejecutable.

El desarrollo va en **dos fases**: primero validamos los 3 modelos (FASE 1) y
recién después construimos el sistema completo con alertas (FASE 2).

---

## FASE 1 — Probar los modelos

### Prompt 0 — Verificación inicial
```
Lee CLAUDE.md y resume la arquitectura y el plan en dos fases. Lista los archivos
que crearás y en qué orden. No escribas código todavía.
```

### Prompt 1 — Configuración central
```
Crea config.py usando python-dotenv. Que exponga ROBOFLOW_API_KEY, ROBOFLOW_API_URL,
las credenciales de Twilio (ACCOUNT_SID, AUTH_TOKEN, WHATSAPP_FROM, WHATSAPP_TO),
CONF_THRESHOLD (0.40), COOLDOWN_SEGUNDOS (30), INTERVALO_INFERENCIA (1.0) y un dict
MODELOS = {"armas":"weapon-qpfo8/1","rostros":"face-detection-yyxs8/2","placas":"license-plate-w8chc/1"}.
Que avise con un error claro si falta la API key de Roboflow.
```

### Prompt 2 — Script de prueba (FASE 1)
```
Crea test_modelos.py. Debe crear un InferenceHTTPClient con la config, recorrer una
o varias imágenes de la carpeta data/, ejecutar los 3 modelos sobre cada una e
imprimir de forma legible: nombre del modelo, número de predicciones, y para cada
predicción su clase y confianza. Que maneje errores de red sin caerse. El objetivo
es confirmar que la API responde y entender el formato de salida.
```
> Antes de correrlo, coloca 2-3 imágenes de prueba en `data/` (una con un arma,
> una con un rostro y una con una placa). Luego: `python test_modelos.py`.

### Prompt 3 — Utilidades de dibujo
```
Crea src/utils.py con: un logger reutilizable, una función para asegurar carpetas,
una para generar timestamps, y una función dibujar_detecciones(frame, detecciones)
que reciba las cajas (con clase, confianza y esquinas x1,y1,x2,y2) y las dibuje con
color según el tipo (armas en rojo, rostros en verde, placas en azul) y su etiqueta.
```

---

## FASE 2 — Sistema completo con alertas

### Prompt 4 — Detector Roboflow
```
Crea src/detector.py con la clase DetectorRoboflow. En el constructor crea el
InferenceHTTPClient con la config. Método inferir(frame, modelos) que para cada
modelo pedido llama a client.infer(frame, model_id=...), filtra por CONF_THRESHOLD,
y devuelve una lista de detecciones normalizadas con: tipo (armas/rostros/placas),
clase, confianza y esquinas (x1,y1,x2,y2) convertidas desde el centro (x,y,w,h) que
entrega Roboflow. Maneja errores de red por modelo sin abortar los demás.
```

### Prompt 5 — Gestor de alertas por WhatsApp
```
Crea src/alertas.py con la clase GestorAlertas. Método disparar(frame, detecciones):
respeta un cooldown configurable; guarda la captura ANOTADA en capturas/ con timestamp;
arma un mensaje con qué se detectó (tipos y confianza) y la hora; y lo envía por
WhatsApp usando el cliente de Twilio (twilio.rest.Client, messages.create con from_ y
to en formato whatsapp:). Si Twilio no está configurado, solo registra en log sin caer.
Maneja excepciones de Twilio.
```

### Prompt 6 — Cámara
```
Crea src/camara.py con la clase Camara que envuelve cv2.VideoCapture, acepta índice
de webcam (int) o ruta de archivo (str), y tiene métodos para leer frame, saber si
está abierta y liberar recursos. Maneja la fuente no disponible.
```

### Prompt 7 — Orquestador principal
```
Crea main.py con argparse: --source (0 por defecto), --modelos (lista, por defecto
armas y rostros), --conf, --cooldown, --intervalo. Instancia DetectorRoboflow,
GestorAlertas y Camara con la config. Bucle: leer frame -> cada INTERVALO_INFERENCIA
segundos inferir con los modelos elegidos -> dibujar detecciones -> si hay detecciones
de riesgo (p.ej. armas) disparar alerta -> mostrar el frame con un contador -> salir
con 'q'. Libera la cámara al final.
```

### Prompt 8 — Pruebas
```
Crea tests/ con pytest. Mockea InferenceHTTPClient.infer para no llamar a la API real
y verifica que DetectorRoboflow convierte bien el centro (x,y,w,h) a esquinas y filtra
por confianza. Para GestorAlertas, mockea Twilio y verifica el cooldown, el guardado de
captura y que NO se llama a WhatsApp cuando faltan credenciales.
```

### Prompt 9 — README y documentación
```
Crea README.md con: descripción, los 3 modelos usados, requisitos, instalación del
entorno en Windows, cómo activar el Sandbox de WhatsApp de Twilio y obtener SID/Token,
cómo correr FASE 1 y FASE 2, y una tabla de argumentos de la CLI. Incluye un diagrama
ASCII del flujo camara -> detector(Roboflow) -> alertas(WhatsApp).
```

### Prompt 10 — Prueba de extremo a extremo
```
Guíame para la prueba final: poner imágenes en data/ y correr FASE 1; luego FASE 2 con
la webcam mostrando un arma de juguete/cuchillo y verificar que llega el WhatsApp.
Dame un checklist de fallos comunes (API key, número del sandbox no unido, cámara,
firewall, latencia de red).
```

---

## FASE 3 — Propuestas de mejora (después de la prueba)
Para mencionar/proponer en el paper y la exposición:

### Prompt 11 (opcional) — Más modelos o sustitución
```
Quiero poder añadir o cambiar modelos de Roboflow sin tocar el código: que la lista de
modelos activos se lea desde .env o config y el sistema se adapte. Documenta cómo
agregar un modelo nuevo (su model_id) y deja preparado el caso de detección de placas
con OCR como trabajo futuro.
```

### Prompt 12 (opcional) — Imagen por WhatsApp
```
Investiga y propón cómo enviar la captura anotada por WhatsApp (Twilio MediaUrl con una
URL pública temporal, o pywhatkit como alternativa local). Implementa la opción más
simple detrás de un flag --enviar-foto, sin romper el envío de texto actual.
```

---

## Sugerencia de flujo
1. Prompts 0-2: validas que los modelos responden (FASE 1). **Aquí haces tu primera prueba.**
2. Prompts 3-7: sistema funcional con alertas por WhatsApp (FASE 2 / MVP).
3. Prompts 8-10: robustez, documentación y prueba de extremo a extremo.
4. Prompts 11-12: mejoras para proponer en la monografía.
