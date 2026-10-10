# 🏗️ Arquitectura del Sistema — Yize Virtual Assistant & Copilot

Este documento describe la arquitectura modular del proyecto, sus capas de responsabilidad y el flujo de comunicación entre la PC, el modelo 3D y el celular.

---

## 📐 Diagrama de Arquitectura

```mermaid
graph TD
    subgraph Clientes_e_Interfaces [1. Clientes e Interfaces de Usuario]
        PC_Mic[Micrófono / Consola PC<br>main.py]
        Overlay3D[Overlay 3D Escritorio<br>Electron + Three.js + VRM]
        MobileApp[Celular / App PWA<br>mobile_web/]
    end

    subgraph Puentes_y_Servidores [2. Puentes de Conexión & Servidores]
        OverlayBridge[overlay_bridge.py<br>WebSocket :8765]
        VTSBridge[vts_bridge.py<br>WebSocket VTube Studio]
        MobileServer[mobile_server.py<br>aiohttp REST & WS :8080]
        CFTunnel[Cloudflare Tunnel<br>Acceso 4G/5G]
    end

    subgraph Core_Cerebro [3. Núcleo Inteligente (Core Engine)]
        Brain[brain.py<br>Cerebro & Routing]
        Gemini[Google Gemini 2.5 Flash<br>AI & Function Calling]
        LiveComp[live_companion.py<br>Observador en Tiempo Real]
        Memory[memory.py<br>memoria_yize.json]
    end

    subgraph Hardware_y_OS [4. Control de Windows & Hardware]
        Actions[actions.py<br>Juegos, Apps, Volumen, Teclado]
        Vision[vision.py<br>Captura de Pantalla]
        Voice[voice.py<br>edge-tts & STT]
        WinAPI[Windows Win32 API / OS]
    end

    %% Conexiones
    PC_Mic --> Brain
    Overlay3D <--> OverlayBridge
    OverlayBridge <--> Brain
    MobileApp <--> MobileServer
    CFTunnel <--> MobileServer
    MobileServer <--> Brain
    MobileServer <--> Actions
    MobileServer <--> Vision

    Brain <--> Gemini
    Brain <--> LiveComp
    Brain <--> Memory
    Brain --> Actions
    Brain --> Vision
    Brain --> Voice

    Actions --> WinAPI
    Vision --> WinAPI
    Voice --> WinAPI
```

---

## 📂 Organización de Carpetas y Módulos

```text
asistente_virtual/
│
├── 🚀 Lanzadores y Puntos de Entrada
│   ├── iniciar_yize.bat             # Lanzador maestro interactivo (PC + Móvil + 3D)
│   ├── iniciar_servidor_movil.bat   # Lanzador directo para el celular (Wi-Fi o 4G/5G)
│   ├── detener_asistente.bat        # Detiene procesos en segundo plano
│   ├── main.py                      # Punto de entrada principal en la PC (Voz / Consola)
│   └── mobile_server.py             # Servidor HTTP y WebSocket para el celular
│
├── 🧠 core/                         # Núcleo de Inteligencia y Lógica del Sistema
│   ├── __init__.py                  # Auto-resolución de paquetes y sys.path
│   ├── brain.py                     # Enrutamiento de consultas, prompts y fallback
│   ├── actions.py                   # Acciones en Windows (Juegos, Apps, volumen, teclado)
│   ├── agent_tools.py               # Herramientas estructuradas para Gemini
│   ├── live_companion.py            # Observador en vivo (Riot Games LoL API, ventanas)
│   ├── memory.py                    # Memoria persistente a largo plazo
│   ├── vision.py                    # Análisis y captura de pantalla
│   ├── voice.py                     # Motor de voz (Edge TTS y SpeechRecognition)
│   └── config.py                    # Configuración, rutas y variables de entorno
│
├── 🌐 bridges/                      # Puentes y Protocolos de Comunicación
│   ├── __init__.py                  # Auto-resolución de paquetes
│   ├── overlay_bridge.py            # WebSocket de enlace con el avatar 3D (:8765)
│   ├── vts_bridge.py                # Enlace con VTube Studio (Live2D)
│   └── vts_token.txt                # Token de autenticación de VTube Studio
│
├── 📱 mobile_web/                   # Aplicación Web Progresiva Móvil (PWA)
│   ├── index.html                   # Interfaz móvil responsive
│   ├── styles.css                   # Sistema de diseño Cyberpunk / Dark Mode
│   ├── app.js                       # Lógica de voz, WebSocket, deck y pantalla
│   ├── manifest.json                # Soporte de instalación en pantalla de inicio
│   ├── sw.js                        # Service Worker para carga instantánea
│   └── icon.png                     # Icono de la app
│
├── 🎭 yize_overlay/                 # Avatar 3D de Escritorio (Electron + Three.js)
│   ├── electron-main.cjs            # Ventana flotante transparente sin marcos
│   ├── public/assets/Yize.vrm       # Modelo VRM 3D cargado
│   └── src/                         # Animador de gestos, expresiones y socket
│
├── 💾 Carpetas de Recursos y Datos
│   ├── assets/                      # Iconos, imágenes y recortes
│   ├── models/                      # Modelos 3D (Yize.vrm) y modelos RVC
│   ├── capturas/                    # Screenshots generados
│   ├── sonidos/                     # Archivos de audio auxiliares
│   ├── memoria_yize.json            # Base de recuerdos del usuario
│   └── notas.txt                    # Notas rápidas de texto
│
└── 📖 Documentación y Configuración
    ├── .env                         # API Keys privadas
    ├── ARQUITECTURA.md              # Este documento
    ├── MANUAL_APP_MOVIL.md          # Manual de la aplicación móvil
    └── README.md                    # Descripción general del asistente
```

---

## 🔄 Flujo de Datos

1. **Entrada de Usuario:** El usuario habla por el micrófono de la PC o desde el celular (app móvil).
2. **Procesamiento:** `brain.py` recibe el texto:
   - Si es un comando nativo (ej: *"sube el volumen"*, *"abre Fortnite"*), `actions.py` lo ejecuta en Windows al instante.
   - Si es una pregunta o conversación, se inyecta la telemetría en vivo (`live_companion.py`) y memoria (`memory.py`) a **Google Gemini 2.5 Flash**.
3. **Respuesta Multicanal:**
   - **Voz:** `voice.py` genera el audio con la voz neural de Yize.
   - **Avatar 3D:** `overlay_bridge.py` envía la etiqueta de emoción (`[happy]`, `[smug]`, `[angry]`, etc.) para mover el rostro y cuerpo de Yize en la pantalla.
   - **Celular:** `mobile_server.py` envía la respuesta por WebSocket en tiempo real para mostrar el mensaje y reproducir el audio si el usuario lo desea.
