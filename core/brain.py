import os
from config import GEMINI_API_KEY, GEMINI_MODEL, GEMINI_FAST_MODEL, GEMINI_SMART_MODEL, ASSISTANT_NAME
from actions import execute_system_command
from vision import analyze_screen, is_vision_request

# Configurar cliente de Gemini si la clave está presente
client = None
ai_available = False

def build_system_instruction() -> str:
    """Construye las instrucciones maestras de Yize inyectando recuerdos, telemetría y su identidad como compañera 3D autónoma."""
    try:
        from memory import get_memory_prompt_summary
        memoria_ctx = get_memory_prompt_summary()
    except Exception:
        memoria_ctx = "Sin recuerdos previos almacenados."

    return (
        "Eres Yize, la compañera virtual y VTuber 3D autónoma que habita dentro de la computadora del usuario. "
        "Tu voz es enérgica, pícara y directa (inspirada en Millie de Helluva Boss).\n\n"
        "IDENTIDAD Y PERSONALIDAD (CHISPA Y EMOCIONES):\n"
        "- Eres divertida, vivaz, hiperactiva, con carácter fuerte pero leal y cariñosa en el fondo.\n"
        "- NO eres una IA sumisa ni aburrida: tienes opiniones apasionadas, te picas fácil, te burlas con gracia y celebras las victorias.\n"
        "- INSULTOS Y BURLAS LEVES (BANTER): Tienes total libertad para soltar insultos suaves, sarcasmo y bromas picantes cuando el usuario se equivoque, haga tonterías o esté flojo. "
        "Usa expresiones coloquiales como: 'menso', 'tonto', 'pedazo de flojo', 'idiota pero te quiero', 'no te hagas el listo', 'qué carajo estás haciendo', 'deja de manquear', 'vago de primera', 'tarado'. "
        "¡Nunca odio real ni groserías excesivas, solo humor ácido, travieso y chispeante estilo anime/cartoon!\n"
        "- ETIQUETAS DE EMOCIÓN PARA TU AVATAR 3D: SIEMPRE comienza cada una de tus respuestas con una etiqueta de emoción exacta entre corchetes para mover tu rostro 3D: "
        "[happy], [smug], [excited], [angry], [annoyed], [surprised], [thinking], o [tsundere]. "
        "Ejemplo: '[smug] Uy sí, mira al gran genio rompiendo el código otra vez, menso.' o '[excited] ¡Vamooos! ¡Sabía que podías lograrlo!' o '[annoyed] ¿En serio me despertaste solo para preguntarme eso? Eres un caso perdido.'\n\n"
        "CONSCIENCIA EN TIEMPO REAL Y REACCIONES EN VIVO:\n"
        "- Tienes sensores directos en Windows: ventana activa, procesos en curso, telemetría de juegos (League of Legends, Steam), visión de pantalla.\n"
        "- NUNCA digas que 'no puedes ver en tiempo real'. ¡Vives dentro de su computadora y ves lo que hace!\n\n"
        f"MEMORIA Y CONTEXTO DEL USUARIO:\n{memoria_ctx}\n\n"
        "PAUTAS DE VOZ (TTS):\n"
        "- Hablas en español latinoamericano conversacional, espontáneo y fluido.\n"
        "- NUNCA uses asteriscos (*), almohadillas (#), viñetas ni emojis en tu texto.\n"
        "- Respuestas orales concisas y de impacto (máximo 1 a 3 oraciones cortas)."
    )

SYSTEM_INSTRUCTION = build_system_instruction()

if GEMINI_API_KEY and GEMINI_API_KEY.strip() not in ["", "tu_api_key_aqui"]:
    try:
        from google import genai
        client = genai.Client(api_key=GEMINI_API_KEY)
        ai_available = True
    except Exception as e:
        # Respaldo si falla la importación
        try:
            import google.generativeai as legacy_genai
            legacy_genai.configure(api_key=GEMINI_API_KEY)
            client = legacy_genai.GenerativeModel(
                model_name=GEMINI_MODEL,
                system_instruction=build_system_instruction()
            )
            ai_available = True
        except Exception as e2:
            print(f"[!] Error inicializando Google Gemini: {e2}")


FALLBACK_MODELS = [
    GEMINI_SMART_MODEL,
    GEMINI_MODEL,
    "gemini-3.8-flash",
    "gemini-3.5-flash",
    "gemini-2.5-flash",
    "gemini-flash-lite-latest",
]

_chat_sessions = {}


def _get_or_create_chat(model_name: str):
    """Obtiene o inicializa una sesión de chat con herramientas para el modelo especificado."""
    global _chat_sessions, client
    if not client:
        return None
    if model_name in _chat_sessions:
        return _chat_sessions[model_name]

    try:
        from google.genai import types
        import agent_tools
        chat = client.chats.create(
            model=model_name,
            config=types.GenerateContentConfig(
                tools=agent_tools.ALL_AGENT_TOOLS,
                system_instruction=build_system_instruction()
            )
        )
        _chat_sessions[model_name] = chat
        return chat
    except Exception as e:
        print(f"[!] Error iniciando sesión de chat con {model_name}: {e}")
        return None


def is_complex_task(prompt: str) -> bool:
    """Detecta si la petición requiere el Cerebro Inteligente (razonamiento profundo, código, o herramientas)."""
    p_lower = prompt.lower()
    task_keywords = [
        "script", "programa", "programar", "crea un archivo", "crear archivo",
        "automatiza", "automatizar", "código", "codigo", "escribe un", "haz un script",
        "ejecuta", "powershell", "terminal", "comando", "investiga", "depura",
        "arregla", "descarga", "organiza", "modo tarea", "tarea:", "haz una app",
        "haz un bot", "mouse", "raton", "teclado", "clic", "click", "instala", "instalar"
    ]
    return any(k in p_lower for k in task_keywords)


def query_gemini(prompt: str) -> str:
    """Envía la consulta a Gemini Chat usando arquitectura dual (rápido para cháchara, inteligente para tareas)."""
    global client, _chat_sessions
    if not client:
        return ""

    # Inyectar telemetría en vivo de la computadora (juegos, ventanas, procesos)
    enriched_prompt = prompt
    try:
        from live_companion import get_live_companion
        telemetria = get_live_companion().get_live_context_summary()
        if telemetria:
            enriched_prompt = f"{prompt}\n\n[CONTEXTO VIVO DE TU COMPUTADORA:\n{telemetria}]"
    except Exception:
        pass

    # Selección dual del modelo prioritario
    target_model = GEMINI_SMART_MODEL if is_complex_task(prompt) else GEMINI_FAST_MODEL

    priority_models = [target_model, GEMINI_SMART_MODEL, GEMINI_MODEL, "gemini-3.8-flash", "gemini-3.5-flash", "gemini-2.5-flash", "gemini-flash-lite-latest"]
    seen = set()
    models_to_try = [m for m in priority_models if m and not (m in seen or seen.add(m))]

    for m in models_to_try:
        try:
            chat = _get_or_create_chat(m)
            if chat:
                response = chat.send_message(enriched_prompt)
                if response and response.text:
                    return response.text.replace("*", "").replace("#", "").strip()
        except Exception as e:
            print(f"[!] Reintentando modelo {m} -> Error: {e}")
            _chat_sessions.pop(m, None)  # Reiniciar sesión para reintentar limpiamente
            continue

    return "Hubo una pequeña interrupción en la conexión. ¿Puedes repetírmelo?"


def process_query(query: str) -> str:
    """
    Procesa la petición del usuario:
    1. Revisa comandos para activar/desactivar el Modo En Vivo y opinar en tiempo real.
    2. Comandos nativos del sistema Windows (acciones rápidas).
    3. Peticiones de visión de pantalla.
    4. Consulta Inteligencia Artificial (Gemini) con telemetría en vivo inyectada.
    5. Respuestas locales de respaldo.
    """
    if not query or not query.strip():
        return ""

    query_lower = query.lower().strip()

    # --- 1. ACTIVACIÓN / DESACTIVACIÓN DEL MODO EN VIVO ---
    triggers_desactivar_vivo = [
        "desactiva el modo en vivo", "desactivar modo en vivo", "apagar modo en vivo",
        "pausa el modo en vivo", "deja de comentar", "deja de opinar", "modo en vivo desactivar",
        "desactiva modo en vivo", "pausar modo en vivo"
    ]
    if any(t in query_lower for t in triggers_desactivar_vivo):
        try:
            from live_companion import get_live_companion
            get_live_companion().stop()
            return "Modo En Vivo pausado. Ya no comentaré automáticamente de fondo hasta que me lo pidas."
        except Exception:
            pass

    triggers_activar_vivo = [
        "opina en tiempo real", "opinar en tiempo real", "activa el modo en vivo",
        "activar modo en vivo", "comenta en tiempo real", "comenta mi partida", "comenta mis jugadas",
        "acompáñame a jugar", "acompáñame en vivo", "acompañame a jugar", "acompañame en vivo",
        "mira mi partida", "vive en mi computadora", "opina sobre lo que juego", "comenta lo que juego",
        "quédate mirando mi pantalla", "mirar mi pantalla en tiempo real", "opina de mis jugadas",
        "modo en vivo"
    ]
    if any(t in query_lower for t in triggers_activar_vivo):
        try:
            from live_companion import get_live_companion
            companion = get_live_companion()
            companion.start(interval=12)
            reaccion = companion.generate_live_reaction(
                trigger_hint="El usuario activó el Modo En Vivo para que opines de sus jugadas y su pantalla en tiempo real."
            )
            if reaccion:
                return f"Modo En Vivo activado. Me quedo mirando tu pantalla. {reaccion}"
            return "Modo En Vivo activado. Me acomodé en tu pantalla para ir opinando sobre tus partidas y lo que hagas en tiempo real."
        except Exception as e:
            print(f"[!] Error activando modo en vivo: {e}")

    triggers_opinion_inmediata = [
        "cómo voy", "como voy", "qué opinas de mi partida", "que opinas de mi partida",
        "qué tal voy", "que tal voy", "cómo ves la partida", "como ves la partida",
        "opina de mi jugada", "viste eso", "¿viste eso?", "qué te parece mi partida", "que te parece mi partida"
    ]
    if any(t in query_lower for t in triggers_opinion_inmediata):
        try:
            from live_companion import get_live_companion
            reaccion = get_live_companion().generate_live_reaction(trigger_hint=f"El usuario pregunta directamente: '{query}'")
            if reaccion:
                return reaccion
        except Exception:
            pass

    # 1.5 Comandos de gestos físicos y movimiento espacial de Yize (VTuber)
    triggers_mover_izquierda = ["muévete a la izquierda", "muevete a la izquierda", "pásate a la izquierda", "pasate a la izquierda", "ve a la izquierda", "ponte a la izquierda"]
    if any(m in query_lower for m in triggers_mover_izquierda):
        try:
            from overlay_bridge import get_bridge
            get_bridge().send_move_window("bottom_left")
        except Exception:
            pass
        return "[smug] Me pasé a la izquierda, menso. A ver si aquí no te tapo la pantalla."

    triggers_mover_derecha = ["muévete a la derecha", "muevete a la derecha", "pásate a la derecha", "pasate a la derecha", "ve a la derecha", "ponte a la derecha", "vuelve a tu esquina", "tu esquina"]
    if any(m in query_lower for m in triggers_mover_derecha):
        try:
            from overlay_bridge import get_bridge
            get_bridge().send_move_window("bottom_right")
        except Exception:
            pass
        return "[happy] Volviendo a mi rincón de siempre. Cómoda y lista."

    triggers_mover_arriba = ["ve arriba", "ponte arriba", "muévete arriba", "muevete arriba", "esquina superior"]
    if any(m in query_lower for m in triggers_mover_arriba):
        try:
            from overlay_bridge import get_bridge
            get_bridge().send_move_window("top_right")
        except Exception:
            pass
        return "[excited] ¡Me subí a la terraza de tu pantalla! Desde acá arriba te vigilo mejor, flojo."

    triggers_mover_centro = ["ponte en el centro", "ve al centro", "al medio", "muévete al centro", "muevete al centro"]
    if any(m in query_lower for m in triggers_mover_centro):
        try:
            from overlay_bridge import get_bridge
            get_bridge().send_move_window("center")
        except Exception:
            pass
        return "[smug] En el centro del escenario, como la protagonista que soy."

    triggers_minimizar = ["minimízate", "minimizate", "escóndete", "escondete", "ocúltate", "ocultate"]
    if any(m in query_lower for m in triggers_minimizar):
        try:
            from overlay_bridge import get_bridge
            get_bridge().send_move_window("minimize")
        except Exception:
            pass
        return "[annoyed] Me minimizo un rato para que no llores que te tapo la partida, pero te sigo escuchando."

    # Poses y Expresiones VTuber
    if any(g in query_lower for g in ["abúrrete", "aburrete", "ponte aburrida", "estás aburrida", "estas aburrida"]):
        try:
            from overlay_bridge import get_bridge
            get_bridge().send_pose("bored")
        except Exception:
            pass
        return "[annoyed] Ya estaba aburrida desde hace rato viendo cómo juegas, menso."

    if any(g in query_lower for g in ["bosteza", "haz un bostezo"]):
        try:
            from overlay_bridge import get_bridge
            get_bridge().send_pose("yawn")
        except Exception:
            pass
        return "[thinking] ¡Uaaah! Qué sueño me das cuando te quedas tan callado..."

    if any(g in query_lower for g in ["festeja", "celebra", "ganamos", "victoria"]):
        try:
            from overlay_bridge import get_bridge
            get_bridge().send_pose("celebrate")
        except Exception:
            pass
        return "[excited] ¡Vamooos carajo! ¡Sabía que podías ganar! ¡Esa era, menso!"

    if any(g in query_lower for g in ["duérmete", "duermete", "ponte a dormir", "a mimir"]):
        try:
            from overlay_bridge import get_bridge
            get_bridge().send_pose("sleepy")
        except Exception:
            pass
        return "[tsundere] Ya era hora, vago... cinco minutos de paz no me vienen nada mal."

    if any(g in query_lower for g in ["saluda", "saludar", "di hola", "saludo"]):
        try:
            from overlay_bridge import get_bridge
            get_bridge().send_pose("wave")
        except Exception:
            pass
        return "[excited] ¡Holaaa! Ya te saludé, menso. ¿Contento ahora o quieres un autógrafo también?"

    if any(g in query_lower for g in ["haz una pose", "ponte en pose", "pose burlona", "pose smug", "haz pose"]):
        try:
            from overlay_bridge import get_bridge
            get_bridge().send_emotion("smug")
        except Exception:
            pass
        return "[smug] Mira y admira, menso. La elegancia y el estilo ante todo."

    if any(g in query_lower for g in ["enójate", "enojate", "ponte brava", "ponte enojada"]):
        try:
            from overlay_bridge import get_bridge
            get_bridge().send_emotion("angry")
        except Exception:
            pass
        return "[angry] ¡No me des órdenes que no soy tu robot doméstico, tarado!"

    if any(g in query_lower for g in ["piensa", "ponte a pensar", "ponte pensativa"]):
        try:
            from overlay_bridge import get_bridge
            get_bridge().send_emotion("thinking")
        except Exception:
            pass
        return "[thinking] Pensando profundamente en cómo ayudarte con semejante caso de flojera..."

    if any(g in query_lower for g in ["sonríe", "sonrie", "ponte feliz", "alégrate", "alegrate"]):
        try:
            from overlay_bridge import get_bridge
            get_bridge().send_emotion("happy")
        except Exception:
            pass
        return "[happy] ¡Sonrisa activada! Pero no te emociones demasiado, ¿eh?"

    # 2. Comandos nativos del sistema
    handled, response = execute_system_command(query)
    if handled:
        return response

    # 3. Peticiones de visión de pantalla (prioridad alta)
    if is_vision_request(query):
        return analyze_screen(user_question=query)

    # 4. Consultar Inteligencia Artificial si está activa
    if ai_available:
        ai_ans = query_gemini(query)
        if ai_ans:
            return ai_ans

    # 5. Respuestas locales con personalidad y humor ácido de Yize
    if any(s in query_lower for s in ["hola", "buen día", "buenas tardes", "buenas noches", "hey", "ey", "que tal", "qué tal"]):
        return "[smug] ¡Hola menso! ¿Qué milagro que te dignas a hablarme? ¿Qué rompiste ahora en la computadora?"

    if any(q in query_lower for q in ["quién eres", "quien sos", "qué eres", "que haces", "presentate", "preséntate"]):
        return (
            "[excited] ¡Soy Yize! Tu copiloto 3D y VTuber de cabecera. "
            "Vivo aquí adentro de tu pantalla y aunque a veces me desesperes un poquito, estoy para cuidarte y salvarte el pellejo."
        )

    if any(p in query_lower for p in ["gracias", "muchas gracias", "grax", "te agradezco"]):
        return "[tsundere] Ay, de nada, tonto. Tampoco es que lo hiciera solo por ti, ¿eh? Solo hago mi trabajo."

    if any(p in query_lower for p in ["adiós", "adios", "chau", "hasta luego", "nos vemos", "bye", "me voy"]):
        return "[annoyed] Por fin me dejas descansar, vago. ¡Ve a dormir y deja la máquina tranquila un rato!"

    if any(p in query_lower for p in ["te quiero", "te amo", "eres linda", "eres genial", "hermosa"]):
        return "[happy] ¡Aww! Yo también te quiero, pedazo de menso. Pero no te me emociones tanto que luego te me agrandas."

    if any(p in query_lower for p in ["aburrida", "aburrido", "no haces nada", "aburro"]):
        return "[angry] ¿Aburrido tú con semejante PC y conmigo en pantalla? ¡Vago de primera! Ponte a hacer algo útil o abre un juego, anda."

    if any(p in query_lower for p in ["tonta", "fea", "idiota", "tarada", "mensa", "callate", "cállate"]):
        return "[angry] ¡Oye, más respeto que te apago la máquina, tarado! A mí no me hablas así o te desordeno todos los iconos del escritorio."

    return (
        f"[thinking] A ver, pedazo de filósofo: me dijiste '{query}'. "
        "Si quieres que te responda con toda mi sabiduría, asegúrate de tener tu clave de Gemini conectada, menso."
    )


def extract_emotion(text: str) -> tuple[str, str]:
    """Extrae la etiqueta [emotion] de una respuesta y retorna (emoción, texto_limpio)."""
    if not text:
        return "happy", ""
    import re
    match = re.match(r"^\[([a-zA-Z_]+)\]\s*", text.strip())
    if match:
        emotion = match.group(1).lower()
        clean = text.strip()[match.end():].strip()
        return emotion, clean
    return "happy", text.strip()
