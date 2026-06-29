import os

# Render asigna el puerto vía variable PORT
bind    = f"0.0.0.0:{os.getenv('PORT', '10000')}"
workers = 1      # CRÍTICO: estado en memoria, nunca más de 1 worker
threads = 8      # 1 por SSE + frames concurrentes
timeout = 0      # sin timeout: SSE mantiene conexiones abiertas indefinidamente
