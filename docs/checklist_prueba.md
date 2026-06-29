# Checklist de Prueba de Extremo a Extremo — SI904-M2

## FASE 1 — Probar los modelos (sin cámara)

### Preparación
- [ ] API key de Roboflow configurada en `.env` (variable `ROBOFLOW_API_KEY`)
- [ ] Coloca 3 imágenes en `data/`:
  - `arma.jpg` — un cuchillo, pistola o rifle (imagen de internet)
  - `rostro.jpg` — cara de persona bien iluminada
  - `placa.jpg` — placa vehicular visible
- [ ] Entorno virtual activado: `.\venv\Scripts\Activate.ps1`

### Ejecución
```powershell
python test_modelos.py
```

### Verificación
- [ ] Sale el mensaje `[INFO] Probando 3 modelos sobre N imagen(es)...`
- [ ] Para la imagen con arma → modelo `armas` detecta algo con conf > 0.40
- [ ] Para la imagen con rostro → modelo `rostros` detecta algo
- [ ] Para la imagen con placa → modelo `placas` detecta algo
- [ ] Sale `[OK] Prueba finalizada.` al final

---

## FASE 2 — Sistema completo con cámara y alertas

### Preparación adicional
- [ ] Credenciales de Twilio en `.env`:
  - `TWILIO_ACCOUNT_SID`
  - `TWILIO_AUTH_TOKEN`
  - `TWILIO_WHATSAPP_FROM=whatsapp:+14155238886`
  - `TWILIO_WHATSAPP_TO=whatsapp:+51XXXXXXXXX` (tu número)
- [ ] Número de WhatsApp unido al sandbox de Twilio (enviaste `join xxxx-yyyy`)
- [ ] Webcam disponible (o archivo de video de prueba)

### Ejecución
```powershell
# Con webcam
python main.py

# Con video de prueba
python main.py --source video_prueba.mp4 --modelos armas rostros --conf 0.40
```

### Verificación
- [ ] Se abre ventana de OpenCV mostrando la cámara en tiempo real
- [ ] HUD muestra `Frames: N | Alertas: 0 | Q: salir`
- [ ] Al mostrar un cuchillo/objeto de juguete frente a la cámara:
  - [ ] Se dibuja una caja roja con la etiqueta del objeto y confianza
  - [ ] En la consola aparece `[INFO] Alerta generada: ...`
  - [ ] Se guarda un `.jpg` en la carpeta `capturas/`
  - [ ] Llega un mensaje de WhatsApp con el resumen de la detección
  - [ ] El contador de Alertas en el HUD aumenta a 1
- [ ] Al presionar `q`, el programa cierra limpiamente

---

## Checklist de fallos comunes

| # | Síntoma | Causa probable | Solución |
|---|---------|---------------|----------|
| 1 | `[ERROR CRÍTICO] Falta ROBOFLOW_API_KEY` | `.env` no existe o key vacía | Copiar `.env.example` → `.env` y poner la API key |
| 2 | `ERROR: No matching distribution found for inference-sdk` | Python 3.13 en el venv | Recrear venv con Python 3.11: `Python311\python.exe -m venv venv` |
| 3 | `ERROR: No matching distribution found for aiohttp~=3.14` | Problema de red temporal | Volver a intentar `pip install -r requirements.txt` |
| 4 | No llega mensaje de WhatsApp | Número no unido al sandbox | Enviar `join xxxx-yyyy` al sandbox desde el celular |
| 5 | No llega mensaje de WhatsApp | TWILIO_WHATSAPP_TO incorrecto | Verificar formato: `whatsapp:+51XXXXXXXXX` |
| 6 | `No se pudo abrir la fuente de video: '0'` | Webcam ocupada/no encontrada | Cerrar Teams/Zoom; probar `--source 1` |
| 7 | Detecciones lentas / timeout | Conexión lenta o firewall | Aumentar `--intervalo 3.0`; probar con red móvil |
| 8 | `HTTP 401 / 403 Unauthorized` | API key expirada o incorrecta | Regenerar en Roboflow > Settings > API Keys |
| 9 | Caja desfasada / coordenadas erróneas | Resolución de cámara inusual | Normal en algunos modelos; el dibujo es indicativo |
| 10 | `ModuleNotFoundError: No module named 'inference_sdk'` | venv no activado | Ejecutar `.\venv\Scripts\Activate.ps1` primero |
| 11 | `ERROR: execution of scripts is disabled` | PowerShell policy | `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser` |
| 12 | Foto no llega por WhatsApp (`--enviar-foto`) | URL pública no configurada | Poner `URL_PUBLICA_CAPTURAS` en .env y levantar ngrok |

---

## Pruebas unitarias

```powershell
pytest tests/ -v
```

Resultado esperado:
```
tests/test_detector.py::TestDetectorRoboflow::test_conversion_centro_a_esquinas PASSED
tests/test_detector.py::TestDetectorRoboflow::test_filtrado_por_confianza PASSED
tests/test_detector.py::TestDetectorRoboflow::test_error_de_red_no_aborta PASSED
tests/test_detector.py::TestDetectorRoboflow::test_modelo_desconocido_se_omite PASSED
tests/test_detector.py::TestDetectorRoboflow::test_multiples_modelos PASSED
tests/test_alertas.py::TestGestorAlertas::test_primera_alerta_se_envia PASSED
tests/test_alertas.py::TestGestorAlertas::test_cooldown_impide_segunda_alerta PASSED
tests/test_alertas.py::TestGestorAlertas::test_captura_guardada PASSED
tests/test_alertas.py::TestGestorAlertas::test_sin_credenciales_no_llama_whatsapp PASSED
tests/test_alertas.py::TestGestorAlertas::test_sin_detecciones_no_dispara PASSED

10 passed in X.XXs
```
