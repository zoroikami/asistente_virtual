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
