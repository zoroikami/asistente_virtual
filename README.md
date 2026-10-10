# 💜 Yize — Asistente Virtual 3D & Copiloto Autónoma de Escritorio
*Compañera de Escritorio 3D • Control Total de Windows • Control Remoto desde Celular (PWA) • Mente Activa con IA*

**Yize** es una compañera virtual interactiva y copiloto autónoma para Windows. Habita en tu computadora a través de un avatar 3D transparente (formato VRM), te escucha por micrófono con síntesis de voz neuronal, monitorea en tiempo real lo que juegas o programas, y te permite darle órdenes tanto desde la PC como desde tu **teléfono móvil** (vía red Wi-Fi o datos móviles 4G/5G).

---

## ✨ Características Principales

* 🎭 **Avatar 3D Interactivo de Escritorio**:
  - Modelo 3D en tiempo real (VRM) renderizado con Three.js y Electron sobre tu pantalla sin marcos ni fondos.
  - Sigue el cursor de tu ratón con la mirada (*LookAt*).
  - Gestos procedurales vivos, pestañeo natural y sincronización labial (*lip-sync*).
  - Reacciones emocionales faciales según el contexto: `[happy]`, `[smug]`, `[angry]`, `[excited]`, `[thinking]`, etc.
* 📱 **Control Remoto desde Celular (PWA)**:
  - Aplicación web instalable en Android e iPhone con diseño moderno Cyberpunk Dark.
  - Micrófono en el celular para dictarle órdenes por voz en español.
  - Deck de control remoto: volumen, multimedia, juegos, capturas, bloqueo de PC.
  - Visor de pantalla en vivo de tu PC desde el teléfono.
  - Conexión dual: en red Wi-Fi de tu casa o desde cualquier lugar con datos móviles vía túnel seguro Cloudflare.
* 🧠 **Mente Autónoma e Inteligencia Artificial**:
  - Potenciada con **Google Gemini 2.5 Flash** con razonamiento en tiempo real y *function calling*.
  - **Modo en Vivo (Live Companion)**: Detecta juegos activos (League of Legends Live Client API, Steam, Fortnite) y ventanas de Windows, emitiendo opiniones espontáneas.
  - **Memoria a largo plazo**: Recuerda tus preferencias, gustos y hábitos entre sesiones.
* 🎙️ **Voz Neuronal de Alta Fidelidad**:
  - Compatible con voces ultranaturales en español (Microsoft Edge Neural TTS y Fish Audio).

---

## 🚀 Cómo Iniciar a Yize (Lanzadores Rápidos)

| Script | Descripción |
| :--- | :--- |
| **`iniciar_yize.bat`** | **Lanzador Maestro Interactivo:** Te permite elegir entre modo Consola/Texto, modo Voz continua por micrófono, o iniciar Yize 3D junto con el Servidor Móvil. |
| **`iniciar_servidor_movil.bat`** | **Servidor para Celular:** Inicia la app móvil y muestra el código QR para escanear con la cámara de tu teléfono (en Wi-Fi o con túnel 4G/5G). |
| **`detener_asistente.bat`** | Detiene de forma segura todos los procesos activos (asistente, overlay 3D y servidor móvil). |

---

## 🎙️ Cómo Interactuar por Voz

Puedes hablarle de forma natural diciendo su nombre (**"Yize"**, **"Oye Yize"**, **"Hey Yize"**):

* **En una sola frase:**
  * *"Yize, abre Spotify"*
  * *"Yize, qué hora es"*
  * *"Yize, sube el volumen"*
  * *"Yize, toma una captura de pantalla"*
  * *"Yize, vamos a jugar LoL"*
* **Por conversación libre:**
  * Charlar sobre programación, anime, videojuegos, tus tareas o debatir cualquier tema.

---

## 🛠️ Acciones y Comandos Disponibles

| Categoría | Ejemplos de Órdenes |
| :--- | :--- |
| **Multimedia y Volumen** | `sube el volumen`, `baja el volumen`, `silencia el audio`, `play`, `pausa la música`, `siguiente canción`, `canción anterior` |
| **Juegos y Launchers** | `abre League of Legends` / `abre LoL`, `abre Fortnite`, `abre Steam`, `abre Riot Client`, `abre Valorant` |
| **Aplicaciones y Navegador** | `abre Spotify`, `abre Chrome`, `abre Discord`, `abre YouTube`, `abre WhatsApp`, `abre Bloc de notas`, `abre Calculadora` |
| **Control de Windows** | `captura de pantalla` / `screenshot`, `bloquea la pantalla`, `minimiza todo` / `muestra el escritorio` |
| **Estado y Rendimiento** | `cómo está el sistema`, `estado de la batería`, `uso de procesador`, `memoria ram`, `qué hora es`, `qué día es hoy` |
| **Apagado Programado** | `apaga la pc` *(programa apagado en 60s con confirmación)*, `cancela el apagado` |
| **Notas del Usuario** | `anota comprar café`, `lee mis notas`, `borra mis notas` *(guardadas en `notas.txt`)* |
| **Visión de Pantalla con IA** | `mira mi pantalla`, `qué estoy haciendo`, `analiza este error de código` |

---

## 🏗️ Estructura del Proyecto

El código está organizado bajo una arquitectura modular limpia por capas:

```text
asistente_virtual/
│
├── 🚀 Lanzadores
│   ├── iniciar_yize.bat             # Lanzador maestro PC + Móvil + 3D
│   ├── iniciar_servidor_movil.bat   # Lanzador directo del servidor móvil (QR)
│   ├── detener_asistente.bat        # Detención de procesos en segundo plano
│   ├── main.py                      # Punto de entrada de Yize en PC
│   └── mobile_server.py             # Servidor HTTP/WebSocket aiohttp
│
├── 🧠 core/                         # Núcleo de Lógica, Hardware e Inteligencia
│   ├── brain.py                     # Enrutador inteligente y personalidad
│   ├── actions.py                   # Acciones en Windows (Juegos, apps, teclado, audio)
│   ├── agent_tools.py               # Herramientas estructuradas de Gemini
│   ├── live_companion.py            # Monitoreo en vivo (League of Legends API, ventanas)
│   ├── memory.py                    # Memoria persistente a largo plazo
│   ├── vision.py                    # Captura y visión multimodal de pantalla
│   ├── voice.py                     # Reconocimiento (STT) y voz neuronal (TTS)
│   └── config.py                    # Configuración, rutas y constantes
│
├── 🌐 bridges/                      # Puentes de Comunicación
│   ├── overlay_bridge.py            # WebSocket con el avatar 3D (:8765)
│   └── vts_bridge.py                # Enlace con VTube Studio (Live2D)
│
├── 📱 mobile_web/                   # Frontend de la App Móvil PWA (HTML, CSS, JS)
├── 🎭 yize_overlay/                 # Avatar 3D de escritorio (Electron + Three.js)
├── 📦 models/                       # Modelos 3D (Yize.vrm) y modelos de voz RVC
├── 🖼️ assets/                       # Recursos visuales y gráficos
├── 📸 capturas/                     # Capturas de pantalla tomadas por Yize
├── 🔊 sonidos/                      # Efectos sonoros y audio generado
└── 💾 Datos y Configuración
    ├── .env                         # Claves de API privadas
    ├── memoria_yize.json            # Base de recuerdos del usuario
    └── notas.txt                    # Bloc de notas rápido
```

---

## 📚 Documentación Adicional

* 🏗️ **[Arquitectura y Flujo Técnico](file:///c:/Users/kj/Desktop/asistente_virtual/ARQUITECTURA.md)**: Diagramas Mermaid, capas del sistema y comunicación WebSocket.
* 📱 **[Manual de la App Móvil](file:///c:/Users/kj/Desktop/asistente_virtual/MANUAL_APP_MOVIL.md)**: Guía paso a paso para instalar la PWA en tu celular e interactuar fuera de casa vía 4G/5G.

---

## 🔑 Configuración de Inteligencia Artificial (Google Gemini)

Yize puede ejecutar comandos nativos del sistema localmente sin internet. Para activar su razonamiento completo, visión de pantalla y personalidad:

1. Consigue una API Key gratuita en [Google AI Studio](https://aistudio.google.com/app/apikey).
2. Abre el archivo **`.env`** en la carpeta raíz del proyecto.
3. Coloca tu clave:
   ```env
   GEMINI_API_KEY=tu_api_key_aqui
   ```
4. Guarda el archivo y ejecuta `iniciar_yize.bat`.

