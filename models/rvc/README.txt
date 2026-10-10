============================================================
       CARPETA DE MODELOS DE VOZ RVC (CLONACIÓN LOCAL)
============================================================

Para clonar la voz de Millie (o cualquier personaje) gratis usando tu tarjeta NVIDIA RTX 3050:

1. Coloca tu archivo de voz (.pth) en esta carpeta.
   Ejemplo:
   models/rvc/millie.pth
   models/rvc/millie.index  (opcional, mejora la fidelidad)

2. Dónde conseguir el modelo de Millie:
   - En Discord de IA de voz / RVC (comunidades como AI Hub o Servidores de Helluva Boss)
   - O usando la app comunitaria Applio (applio.org) para entrenar o convertir modelos.

3. En tu archivo .env, asegúrate de tener:
   TTS_ENGINE=rvc

El asistente detectará automáticamente el archivo .pth en esta carpeta y transformará
la voz base de Edge-TTS al timbre exacto del modelo usando tu tarjeta gráfica NVIDIA.
