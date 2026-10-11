# 💜 Yize — Asistente Virtual 3D & Copiloto Autónoma de Escritorio
*Compañera de Escritorio 3D • Control Total de Windows • Control Remoto desde Celular (PWA) • Mente Activa con IA*

**Yize** es una compañera virtual interactiva y copiloto autónoma para Windows. Habita en tu computadora a través de un avatar 3D transparente (formato VRM), te escucha por micrófono con síntesis de voz neuronal, monitorea en tiempo real lo que juegas o programas, y te permite darle órdenes tanto desde la PC como desde tu **teléfono móvil** (vía red Wi-Fi o datos móviles 4G/5G).

---

## ✨ Características Principales

* 🎭 **Avatar 3D Interactivo de Escritorio**:
  - Modelo 3D en tiempo real (VRM) renderizado con Three.js y Electron sobre tu pantalla sin marcos ni fondos.
  - **Animaciones `.vrma` reales mezcladas con procedurales**: Motor `@pixiv/three-vrm-animation` con `AnimationMixer` que reproduce clips reales de Mixamo/VRoid arrastrándolos directamente sobre el avatar.
  - **Repertorio de Idle largo (10 micro-comportamientos)**: Yize se estira, revisa su celular imaginario, bebe de una taza, se asoma con curiosidad, apoya la barbilla o cruza los brazos para evitar bucles repetitivos.
  - **Selector de modelo y atuendo en caliente (`F3`)**: Menú flotante para alternar entre Yize 3D, el modo Live2D (VTube Studio) o cargar cualquier archivo `.vrm` externo.
  - **Indicador de Privacidad & Botón de Mute Total**: Puntito LED inteligente en el overlay (verde en micrófono, púrpura en webcam local, cian en visión, gris en reposo) y botón de Modo Sigilo.
  - **Modo "No Molestar" automático**: Detecta cuando abres un videojuego o ventana a pantalla completa y se minimiza/silencia sola.
  - **Seguimiento global del cursor** (*LookAt*) en cualquier monitor y reacción si agitas el ratón (*Mouse Shake*).
  - **Inercia física de pelo y ropa** al arrastrar la ventana por la pantalla (*Three-VRM Spring Bones*).
  - **Visemas fonéticos realistas**: Síntesis acústica de formantes que modula cada vocal VRM (`aa`, `ih`, `ee`, `oh`, `ou`) con labios redondeados o estirados sin saturar en la apertura.
  - **Baile rítmico sincronizado con la música** capturando el audio loopback del PC (Spotify, YouTube, juegos).
  - **Panel de calibración en vivo (F2)** con sliders de huesos y poses con copia de JSON al portapapeles.
  - **Escucha activa**: Asiente y ladea la cabeza con curiosidad mientras le hablas por el micrófono.
  - **Arrastrar y soltar archivos (Drag & Drop)**: Suelta animaciones `.vrma`, modelos `.vrm`, imágenes o código sobre Yize.
  - **Guía visual holográfica en pantalla (HUD)**: Localiza cualquier opción o botón con IA y dibuja una retícula neón con flecha animada directamente sobre él.
  - **Gestos con la mano por webcam (MediaPipe local en RAM)**: Reconoce saludos (ella saluda), pulgar arriba (se alegra), puño (se burla) y juego de Piedra, Papel o Tijera con trampas.
* 📱 **Control Remoto desde Celular (PWA)**:
  - Aplicación web instalable en Android e iPhone con diseño moderno Cyberpunk Dark.
  - Micrófono en el celular para dictarle órdenes por voz en español y deck de control para Windows.
  - Chips rápidos para música de estudio Lo-Fi, gestos de cámara, piedra papel tijera, agua y postura.
  - Conexión dual: en red Wi-Fi de tu casa o desde cualquier lugar con datos móviles vía túnel Cloudflare.
* 🧠 **Mente Autónoma, Gamificación y Plugins**:
  - **Buenos Días Personalizado**: Resumen matutino en 20s con el clima en tiempo real de Santiago de Chile, tareas pendientes y resumen de su diario.
  - **Nivel de Afinidad (Bond Level 1 a 5)**: Sube puntos con el tiempo compartido y desbloquea mayor cercanía y confianza en su personalidad.
  - **Juegos Interactivos**: Juega Trivia (programación/gaming) o Tres en Raya (Ta-te-ti) directamente con ella.
  - **Sistema de Plugins Modular (`plugins/`)**: Agrega nuevas habilidades simplemente colocando archivos `.py` en la carpeta `plugins/`.
  - **Personalidades intercambiables**: *"Modo Estudio/Concentración"* (productiva y serena), *"Modo Tutora"* (didáctica y paciente) y *"Modo Caos"* (sarcástica y pícara estilo Millie).
  - **Recordatorios con escalada de sarcasmo & Hábitos**: 3 niveles de acidez creciente si ignoras una tarea pendiente, más avisos periódicos de postura, hidratación y ojos.
  - **Chistes internos & Comedia recurrente**: Guarda momentos cómicos y anécdotas compartidas que Yize rescata espontáneamente cuando la conversación lo amerita.
  - **Cadena de respaldo con IA local (Ollama)**: Si no hay internet o se agota la cuota de Gemini, responde automáticamente con tu modelo local de Ollama.
  - **Centinela del sistema**: Alertas de batería baja, dispositivos USB conectados, fatiga y nuevos puertos de red en escucha.
  - **El Diario de Yize** (`data/diario_yize.md`): Resumen sarcástico generado con IA al cerrar cada sesión.

---

## 🚀 Cómo Iniciar a Yize

| Ejecutable / Comando | Descripción |
| :--- | :--- |
| **`Yize.exe`** | **Lanzador Único Nativo:** Inicia todo el ecosistema (asistente de voz, overlay 3D transparente, centinela y servidor móvil) en segundo plano con un solo clic. |
| **`python main.py`** | **Modo Consola / Desarrollo:** Supervisor interactivo con registro en tiempo real de eventos, estado de memoria y apagado seguro coordinado con `Ctrl+C`. |

---

## 🎙️ Cómo Interactuar por Voz

Puedes hablarle de forma natural diciendo su nombre (**"Yize"**, **"Oye Yize"**, **"Hey Yize"**):

* **En una sola frase:**
  * *"Yize, pon algo para estudiar"*
  * *"Yize, ¿dónde está el botón de guardar?"*
  * *"Yize, juguemos piedra papel o tijera"*
  * *"Yize, recuérdame en 20 minutos sacar la pizza"*
  * *"Yize, activa la cámara"*
  * *"Yize, cuéntame un chiste interno"*
* **Por conversación libre:**
  * Charlar sobre programación, anime, videojuegos, tus tareas o debatir cualquier tema.

---

## 🛠️ Acciones y Comandos Disponibles

| Categoría | Ejemplos de Órdenes |
| :--- | :--- |
| **Música y Spotify** | `pon algo para estudiar`, `pon lofi`, `pon synthwave`, `pon música de [artista]`, `play`, `pausa la música`, `siguiente canción`, `canción anterior` |
| **Guía Visual en Pantalla** | `¿dónde está la opción [X]?`, `encuentra el botón [X]`, `busca la opción [X]`, `señala dónde está [X]` *(dibuja retícula HUD)* |
| **Gestos y Cámara Local** | `activa la cámara`, `apaga la cámara`, `juguemos piedra papel o tijera`, saludar con la mano, pulgar arriba, puño cerrado |
| **Recordatorios y Hábitos** | `recuérdame en 20 minutos [tarea]`, `recuérdame tomar agua`, `revisa mi postura`, `ya lo hice`, `cancela los recordatorios`, `qué recordatorios tengo` |
| **Chistes y Anécdotas** | `guarda este chiste: [texto]`, `cuéntame un chiste interno`, `dime una anécdota` |
| **Juegos y Launchers** | `abre League of Legends` / `abre LoL`, `abre Fortnite`, `abre Steam`, `abre Riot Client`, `abre Valorant` |
| **Aplicaciones y Navegador** | `abre Spotify`, `abre Chrome`, `abre Discord`, `abre YouTube`, `abre WhatsApp`, `abre Bloc de notas`, `abre Calculadora` |
| **Control de Windows** | `captura de pantalla` / `screenshot`, `bloquea la pantalla`, `minimiza todo` / `muestra el escritorio` |
| **Estado y Rendimiento** | `cómo está el sistema`, `estado de la batería`, `uso de procesador`, `memoria ram`, `qué hora es`, `qué día es hoy` |
| **Personalidades e IA** | `activa modo estudio`, `activa modo tutora`, `activa modo caos` |
| **Apagado Programado** | `apaga la pc` *(programa apagado en 60s con confirmación)*, `cancela el apagado` |
| **Notas del Usuario** | `anota comprar café`, `lee mis notas`, `borra mis notas` *(guardadas en `notas.txt`)* |
| **Visión de Pantalla con IA** | `mira mi pantalla`, `qué estoy haciendo`, `analiza este error de código` |

---

## 🏗️ Estructura del Proyecto

El código está organizado bajo una arquitectura modular limpia por capas:

```text
asistente_virtual/
│
├── 🚀 Lanzadores & Ejecutables
│   ├── Yize.exe                     # Lanzador rápido compilado C# (sin ventanas de consola)
│   ├── main.py                      # Supervisor unificado de procesos (PC, 3D, móvil, centinela)
│   └── mobile_server.py             # Servidor HTTP/WebSocket aiohttp para móvil
│
├── 🧠 core/                         # Núcleo de Lógica, Hardware e Inteligencia
│   ├── brain.py                     # Enrutador inteligente, personalidades y fallback Ollama
│   ├── actions.py                   # Acciones en Windows (Juegos, apps, teclado, audio)
│   ├── agent_tools.py               # Herramientas estructuradas de Gemini
│   ├── live_companion.py            # Monitoreo en vivo (League of Legends API, ventanas)
│   ├── memory.py                    # Memoria persistente a largo plazo
│   ├── vision.py                    # Captura y visión multimodal de pantalla
│   ├── voice.py                     # Reconocimiento (STT), muletillas y voz neuronal (TTS)
│   ├── system_sentinel.py           # Centinela de seguridad, puertos, batería y USB
│   ├── diario.py                    # Diario inteligente de Yize generado al apagar
│   └── config.py                    # Configuración, rutas y constantes
│
├── 🌐 bridges/                      # Puentes de Comunicación
│   ├── overlay_bridge.py            # WebSocket con el avatar 3D (:8765)
│   └── vts_bridge.py                # Enlace con VTube Studio (Live2D)
│
├── 🎭 yize_overlay/                 # Avatar 3D de escritorio (Electron + Three-VRM)
│   ├── src/main.js                  # Lógica del renderer, LookAt global y drag & drop
│   ├── src/animator.js              # Animaciones, emociones, escucha activa y baile
│   ├── src/calibrator.js            # Calibrador en vivo de poses con lil-gui (F2)
│   ├── src/beat.js                  # Algoritmo de tempo y phase para baile rítmico
│   └── src/musicListener.js         # Captura de loopback de audio del sistema
│
├── 📱 mobile_web/                   # Frontend de la App Móvil PWA (HTML, CSS, JS)
├── 📦 models/                       # Modelos 3D (Yize.vrm) y modelos de voz RVC
├── 💾 data/                         # Almacenamiento persistente
│   ├── memoria_yize.json            # Base de recuerdos del usuario
│   ├── diario_yize.md               # Diario de reflexiones sarcásticas
│   └── notas.txt                    # Bloc de notas rápido
├── 📚 docs/                         # Documentación técnica y manuales
│   ├── ARQUITECTURA.md              # Diseño de componentes y flujo de datos
│   └── MANUAL_APP_MOVIL.md          # Guía paso a paso para la app de celular
└── 🔧 tools/                        # Herramientas y utilidades de compilación
    └── Launcher.cs                  # Código fuente C# de Yize.exe
```

Para más detalles técnicos, consulta [ARQUITECTURA.md](file:///c:/Users/kj/Desktop/asistente_virtual/docs/ARQUITECTURA.md) y [MANUAL_APP_MOVIL.md](file:///c:/Users/kj/Desktop/asistente_virtual/docs/MANUAL_APP_MOVIL.md).

---

## 🔑 Configuración de Inteligencia Artificial (Google Gemini & Ollama)

Yize puede ejecutar comandos nativos del sistema localmente sin internet. Para activar su razonamiento completo, visión de pantalla y personalidad:

1. Consigue una API Key gratuita en [Google AI Studio](https://aistudio.google.com/app/apikey).
2. Abre el archivo **`.env`** en la carpeta raíz del proyecto.
3. Coloca tu clave:
   ```env
   GEMINI_API_KEY=tu_api_key_aqui
   ```
4. *(Opcional)* Si tienes **Ollama** instalado localmente, Yize conmutará automáticamente a tu modelo local si te quedas sin conexión o sin cuota de Gemini.
5. Ejecuta `Yize.exe` o `python main.py`.

