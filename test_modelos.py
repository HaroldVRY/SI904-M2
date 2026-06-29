"""
test_modelos.py - FASE 1
====================================================================
Prueba los 3 modelos de Roboflow sobre las imágenes de la carpeta data/.
Objetivo: confirmar que la API responde y ver el formato de las predicciones,
ANTES de integrar cámara y alertas.

Uso:
    1) Pon 2-3 imágenes en data/ (un arma, un rostro, una placa).
    2) Configura ROBOFLOW_API_KEY en tu archivo .env
    3) python test_modelos.py
====================================================================
"""

import os
import glob
from dotenv import load_dotenv
from inference_sdk import InferenceHTTPClient

load_dotenv()

API_KEY = os.getenv("ROBOFLOW_API_KEY", "")
API_URL = os.getenv("ROBOFLOW_API_URL", "https://serverless.roboflow.com")

# Los 3 modelos a probar
MODELOS = {
    "armas":   "weapon-qpfo8/1",
    "rostros": "face-detection-yyxs8/2",
    "placas":  "license-plate-w8chc/1",
}

CARPETA_DATA = "data"
EXTENSIONES = ("*.jpg", "*.jpeg", "*.png")


def listar_imagenes(carpeta):
    rutas = []
    for ext in EXTENSIONES:
        rutas.extend(glob.glob(os.path.join(carpeta, ext)))
    return sorted(rutas)


def probar_modelo(client, nombre, model_id, imagen):
    """Ejecuta un modelo sobre una imagen e imprime un resumen legible."""
    try:
        resultado = client.infer(imagen, model_id=model_id)
    except Exception as e:
        print(f"    [{nombre:<8}] ERROR de red/API: {e}")
        return

    predicciones = resultado.get("predictions", [])
    print(f"    [{nombre:<8}] {len(predicciones)} detección(es)")
    for p in predicciones:
        clase = p.get("class", "?")
        conf = p.get("confidence", 0.0)
        print(f"        - {clase:<16} conf={conf:.2f}")


def main():
    if not API_KEY:
        print("[ERROR] Falta ROBOFLOW_API_KEY en el archivo .env")
        return

    imagenes = listar_imagenes(CARPETA_DATA)
    if not imagenes:
        print(f"[AVISO] No hay imágenes en '{CARPETA_DATA}/'. "
              f"Coloca .jpg/.png para probar.")
        return

    client = InferenceHTTPClient(api_url=API_URL, api_key=API_KEY)
    print(f"[INFO] Probando {len(MODELOS)} modelos sobre "
          f"{len(imagenes)} imagen(es)...\n")

    for ruta in imagenes:
        print(f"Imagen: {os.path.basename(ruta)}")
        for nombre, model_id in MODELOS.items():
            probar_modelo(client, nombre, model_id, ruta)
        print()

    print("[OK] Prueba finalizada.")


if __name__ == "__main__":
    main()
