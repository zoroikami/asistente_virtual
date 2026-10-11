"""
vision.py — Módulo de visión de pantalla para Yize.
Captura la pantalla y la analiza usando Gemini Vision API.
"""
import io
import os
import base64
from pathlib import Path

import pyautogui
from PIL import Image

from config import GEMINI_API_KEY, GEMINI_MODEL

VISION_FALLBACK_MODELS = [
    GEMINI_MODEL,
    "gemini-flash-lite-latest",
    "gemini-3.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-3.5-flash-lite"
]
MAX_WIDTH    = 1280                         # ancho máximo del screenshot enviado
JPEG_QUALITY = 75                           # calidad JPEG para compresión

VISION_PROMPT_PREFIX = (
    "Eres Yize, la compañera virtual 3D autónoma y copiloto de escritorio del usuario. "
    "Se te muestra una captura de pantalla en tiempo real de su equipo. Analízala con tu personalidad enérgica, pícara y directa (inspirada en Millie de Helluva Boss): "
    "sé perspicaz, observadora y constructiva. Si notas errores en su código, videojuegos o que está procrastinando, puedes hacerle una burla ligera o un comentario divertido y útil. "
    "Da una respuesta concisa y natural en español (máximo 1 a 2 oraciones). No uses asteriscos, numerales ni emojis. "
    "Habla con naturalidad, como una amiga que vive dentro de su pantalla y ve lo que hace. "
)


# ─── Estado del cliente de visión ────────────────────────────────────────────
_vision_client = None
_vision_available = False


def _init_vision_client():
    """Inicializa el cliente de Gemini si hay API key disponible."""
    global _vision_client, _vision_available
    if _vision_available:
        return True
    if not GEMINI_API_KEY or GEMINI_API_KEY.strip() in ["", "tu_api_key_aqui"]:
        return False
    try:
        from google import genai
        _vision_client = genai.Client(api_key=GEMINI_API_KEY)
        _vision_available = True
        return True
    except Exception as e:
        print(f"[Vision] Error inicializando cliente: {e}")
        return False


def capture_screen_bytes() -> tuple[bytes, tuple]:
    """
    Toma un screenshot de la pantalla completa.
    Intenta pyautogui, luego mss, luego PIL ImageGrab.
    Retorna (jpeg_bytes, (width, height)).
    """
    screenshot = None

    # Método 1: pyautogui
    try:
        screenshot = pyautogui.screenshot()
    except Exception as e:
        pass

    # Método 2: mss
    if screenshot is None:
        try:
            import mss
            with mss.MSS() as sct:
                mon = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
                shot = sct.grab(mon)
                screenshot = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
        except Exception:
            pass

    # Método 3: PIL ImageGrab
    if screenshot is None:
        try:
            from PIL import ImageGrab
            screenshot = ImageGrab.grab(all_screens=True)
        except Exception:
            pass

    if screenshot is None:
        raise RuntimeError("No se pudo capturar la pantalla por ningún método.")

    orig_size = screenshot.size

    # Redimensionar si es muy grande
    if screenshot.width > MAX_WIDTH:
        ratio = MAX_WIDTH / screenshot.width
        new_h = int(screenshot.height * ratio)
        screenshot = screenshot.resize((MAX_WIDTH, new_h), Image.Resampling.LANCZOS)

    buf = io.BytesIO()
    screenshot.convert("RGB").save(buf, format="JPEG", quality=JPEG_QUALITY)
    return buf.getvalue(), orig_size


def analyze_screen(user_question: str = "") -> str:
    """
    Captura la pantalla y la analiza con Gemini Vision.
    
    Args:
        user_question: Pregunta específica del usuario sobre la pantalla.
                       Si está vacía, Yize describe lo que ve.
    
    Returns:
        Respuesta textual de Yize sobre lo que ve en pantalla.
    """
    if not _init_vision_client():
        return "Oye, necesito mi API Key de Gemini en el archivo .env para poder ver tu pantalla."

    try:
        img_bytes, orig_size = capture_screen_bytes()
    except Exception as e:
        print(f"[Vision] Error capturando pantalla: {e}")
        return "No pude tomar una captura de pantalla en este momento, algo bloqueó la captura."

    try:
        from google import genai
        from google.genai import types

        if user_question.strip():
            prompt_text = (
                VISION_PROMPT_PREFIX
                + f"El usuario pregunta: '{user_question}'. "
                + "Responde basándote en lo que ves en la pantalla."
            )
        else:
            prompt_text = (
                VISION_PROMPT_PREFIX
                + "Describe brevemente qué está haciendo el usuario en su pantalla y ofrece ayuda o comenta algo si procede."
            )

        # Construir contenido multimodal: texto + imagen
        image_part = types.Part.from_bytes(
            data=img_bytes,
            mime_type="image/jpeg"
        )
        text_part = types.Part.from_text(text=prompt_text)

        seen = set()
        models_to_try = [m for m in VISION_FALLBACK_MODELS if m and not (m in seen or seen.add(m))]
        for vm in models_to_try:
            try:
                response = _vision_client.models.generate_content(
                    model=vm,
                    contents=[types.Content(
                        role="user",
                        parts=[text_part, image_part]
                    )]
                )
                if response and response.text:
                    answer = response.text.replace("*", "").replace("#", "").strip()
                    return answer
            except Exception as model_err:
                print(f"[Vision] Falló {vm}: {model_err}, probando siguiente...")
                continue

        return "Hmm, no logré interpretar con claridad lo que hay en tu pantalla."

    except Exception as e:
        print(f"[Vision] Error en análisis: {e}")
        return "Hubo un error al procesar la imagen de tu pantalla con Gemini."


def is_vision_request(query: str) -> bool:
    """
    Detecta si el usuario está pidiendo que Yize mire la pantalla.
    """
    query_lower = query.lower().strip()
    vision_triggers = [
        "qué ves", "que ves", "mira la pantalla", "mira mi pantalla",
        "qué hay en mi pantalla", "que hay en mi pantalla",
        "qué estoy haciendo", "que estoy haciendo",
        "qué ves en pantalla", "que ves en pantalla",
        "analiza mi pantalla", "analiza la pantalla",
        "describe mi pantalla", "describe la pantalla",
        "puedes ver", "puedes ver mi pantalla",
        "qué puedes ver", "que puedes ver",
        "ves algo", "qué ves ahí", "que ves ahi",
        "mira lo que tengo", "mira lo que estoy",
        "qué está en pantalla", "que está en pantalla",
        "captura de pantalla", "screenshot",
    ]
    return any(trigger in query_lower for trigger in vision_triggers)


def is_vision_guide_request(query: str) -> bool:
    """Detecta si el usuario le pide a Yize localizar y señalar un elemento en pantalla."""
    q = query.lower().strip()
    triggers = [
        "dónde está", "donde esta", "dónde queda", "donde queda",
        "dónde se encuentra", "donde se encuentra", "encuentra el botón",
        "encuentra la opción", "encuentra el menu", "busca el botón",
        "busca la opción", "señala dónde", "señala donde", "señala el",
        "apunta al", "apunta a la", "dónde está la opción", "donde esta la opcion"
    ]
    return any(t in q for t in triggers)


def locate_element_on_screen(element_query: str) -> tuple[bool, str]:
    """
    Captura la pantalla, le pide a Gemini las coordenadas del elemento y
    le envía al overlay Electron la orden de dibujar la diana holográfica en esas coordenadas.
    """
    import json
    import re
    from google.genai import types

    if not _init_vision_client():
        return False, "Necesito que configures tu GEMINI_API_KEY en .env para poder analizar la pantalla."

    # Extraer el nombre del elemento limpiando prefijos
    nombre_elem = element_query.lower()
    for p in ["dónde está la opción", "donde esta la opcion", "dónde está el botón", "donde esta el boton",
              "dónde está", "donde esta", "encuentra el botón", "encuentra la opción", "encuentra", "busca el", "busca la", "señala"]:
        if nombre_elem.startswith(p):
            nombre_elem = nombre_elem[len(p):].strip()
            break
    nombre_elem = nombre_elem.strip("?¿!¡ ").title() or "Elemento"

    img_bytes, (orig_w, orig_h) = capture_screen_bytes()
    if not img_bytes:
        return False, "No pude capturar la pantalla del equipo."

    prompt_text = (
        f"Analiza esta captura de pantalla y localiza el elemento o botón: '{nombre_elem}'.\n"
        "Devuelve ÚNICAMENTE un objeto JSON sin formato Markdown adicional con este esquema exacto:\n"
        "{\"found\": true, \"box_2d\": [ymin, xmin, ymax, xmax], \"label\": \"nombre breve\"}\n"
        "donde ymin, xmin, ymax, xmax son números enteros normalizados en escala de 0 a 1000.\n"
        "Si el elemento no está visible en pantalla, responde exactamente: {\"found\": false}"
    )

    image_part = types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg")
    text_part = types.Part.from_text(text=prompt_text)

    for vm in VISION_FALLBACK_MODELS:
        try:
            resp = _vision_client.models.generate_content(
                model=vm,
                contents=[types.Content(role="user", parts=[text_part, image_part])]
            )
            if resp and resp.text:
                raw = resp.text.strip()
                # Extraer bloque JSON
                match = re.search(r'\{.*\}', raw, re.DOTALL)
                if match:
                    data = json.loads(match.group(0))
                    if data.get("found") and "box_2d" in data:
                        ymin, xmin, ymax, xmax = data["box_2d"]
                        center_x = int(((xmin + xmax) / 2) / 1000.0 * orig_w)
                        center_y = int(((ymin + ymax) / 2) / 1000.0 * orig_h)
                        label = data.get("label", nombre_elem)

                        # Enviar coordenadas al overlay Electron
                        try:
                            from bridges.overlay_bridge import overlay_bridge
                            overlay_bridge.send_screen_target(center_x, center_y, label, [xmin, ymin, xmax, ymax])
                        except Exception as e:
                            print(f"[Vision] Error enviando target a overlay: {e}")

                        return True, f"Te acabo de señalar '{label}' en pantalla con el puntero holográfico. ¿Lo ves ahora o necesitas lentes?"
                    else:
                        return False, f"Revisé la pantalla, pero no veo '{nombre_elem}' abierto o visible en este momento."
        except Exception as e:
            print(f"[Vision] Falló localización con {vm}: {e}")
            continue

    return False, f"No logré ubicar '{nombre_elem}' con certeza en tu pantalla."
