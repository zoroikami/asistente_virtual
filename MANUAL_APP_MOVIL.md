# 📱 Guía de Uso — App Móvil de Control Remoto para Yize

Con esta aplicación puedes hablar con **Yize**, darle órdenes por voz o texto desde tu celular y controlar tu computadora en tiempo real, tanto dentro de tu casa por Wi-Fi como desde la calle con datos móviles 4G/5G.

---

## 🚀 Cómo Iniciar la App Móvil

Tienes dos formas sencillas de encenderla:

### Método 1: Lanzador dedicado (Recomendado)
Haz doble clic en:
👉 `iniciar_servidor_movil.bat`

El script te preguntará cómo deseas conectarte:
- **Opción [1] En casa (Misma red Wi-Fi):**
  - Muestra un **Código QR en la pantalla de tu PC** y la URL local (ej. `http://192.168.1.6:8080`).
  - Solo tienes que abrir la cámara de tu celular, apuntar a la pantalla y tocar el enlace.
- **Opción [2] Fuera de casa (4G/5G con túnel seguro Cloudflare):**
  - Descarga y activa automáticamente un enlace público seguro `https://xxxx.trycloudflare.com` con código QR.
  - Te permite darle órdenes a tu PC desde cualquier lugar del mundo.

### Método 2: Desde el menú principal de Yize
Haz doble clic en:
👉 `iniciar_yize.bat`
- Selecciona la **Opción [3] Servidor Móvil** o la **Opción [4] Iniciar Todo** (Yize en PC + Servidor Móvil).

---

## 📲 Cómo Instalarla en tu Celular (Como App Nativa)

La aplicación es una **PWA (Progressive Web App)**: no necesitas descargar nada de la Play Store ni compilar APKs.

1. Abre el enlace en tu navegador móvil (**Google Chrome** en Android o **Safari** en iPhone).
2. Toca el menú de opciones (los tres puntos en Chrome o el botón Compartir en Safari).
3. Selecciona **"Añadir a la pantalla de inicio"** o **"Instalar aplicación"**.
4. ¡Listo! Se creará un icono con la imagen de Yize en tu pantalla de inicio y se abrirá en pantalla completa como una app nativa.

---

## 🎙️ Funciones Disponibles desde el Celular

### 1. Pestaña "Chat & Voz"
- **Micrófono Central Interactivo:** Toca el botón violeta del micrófono y háblale en español. Reconoce automáticamente lo que dices y se lo manda a Yize.
- **Selector de Voz:**
  - 🔊 **Altavoces PC:** Yize te responde hablando fuerte por los parlantes de tu computadora.
  - 📱 **Este Celular:** Yize te responde directamente por los altavoces de tu celular con su voz de anime en alta definición.
- **Burbuja de Pensamientos en Directo:** Muestra en tiempo real lo que Yize está pensando y sus reacciones autónomas.
- **Chips de Acceso Rápido:** Botones de un toque para *"Abre Spotify"*, *"Captura de pantalla"*, *"Qué hora es"*, *"Abre LoL"*, *"Bloquear PC"*, etc.
- **Teclado de Texto:** Para escribirle órdenes si estás en un lugar silencioso.

### 2. Pestaña "Control PC" (Deck Remoto)
- **Control Multimedia:** Subir volumen (+10%), Bajar volumen (-10%), Silenciar / Mutear, Play/Pausa, Siguiente canción, Canción anterior.
- **Lanzador de Juegos y Programas en 1 Toque:**
  - League of Legends, Fortnite, Steam, Spotify, Discord, YouTube, Chrome, WhatsApp Web, Bloc de Notas.
- **Acciones del Sistema:**
  - Sacar captura de pantalla en la PC.
  - Minimizar todo y mostrar el escritorio.
  - Bloquear la computadora al instante.
  - Escribir texto a distancia en la PC o presionar teclas (Enter, Escape, Barra espaciadora).

### 3. Pestaña "Pantalla" (Screen Mirror)
- Mira lo que está ocurriendo en la pantalla de tu computadora en tiempo real desde la cama o desde otra habitación.
- Botón de **Actualizar** y modo **Auto-refresco cada 3 segundos**.
- Botón de **Pantalla Completa**.

### 4. Pestaña "Ajustes & Estado"
- **Telemetría en Vivo:** Medidores de CPU %, memoria RAM % y estado de batería de tu PC.
- **Detector de Ventana Activa:** Te dice exactamente qué juego, programa o página web está abierta en la PC en ese instante.
- **PIN de Seguridad (Opcional):** Si quieres proteger el acceso remoto, puedes definir un PIN de 4 dígitos.
- **Código QR:** Para conectar cualquier otro dispositivo en tu hogar.
