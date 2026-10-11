import os
import logging
from pathlib import Path
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("Yize")

# Cargar variables de entorno desde .env local o raíz
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# Configuración del Asistente y Supervisor
ASSISTANT_NAME = os.getenv("ASSISTANT_NAME", "Yize")
INTERACTION_MODE = os.getenv("INTERACTION_MODE", "texto")
OVERLAY_ENABLED = os.getenv("OVERLAY_ENABLED", "1").strip().lower() in ("1", "true", "yes")
MOBILE_ENABLED = os.getenv("MOBILE_ENABLED", "1").strip().lower() in ("1", "true", "yes")
MOBILE_TUNNEL = os.getenv("MOBILE_TUNNEL", "0").strip().lower() in ("1", "true", "yes")
WAKE_WORDS = [
    "yize",
    "yise",
    "yis",
    "oye yize",
    "hey yize",
    "hola yize",
    "ok yize",
    "llise",
    "jize",
    "ruan mei",
    "ruán méi",
    "ruanmei",
    "ruán",
    "ruan",
    "mei",
    "aroha",
    "ahora",
    "oye aroha",
    "hey aroha",
    "asistente",
]

# Configuración de Voz
# Idioma para reconocimiento de voz (es-ES, es-AR, es-MX, etc.)
STT_LANGUAGE = os.getenv("STT_LANGUAGE", "es-AR")

# Motor TTS: 'elevenlabs' (hiperrealista personalizada), 'edge' (neuronal Microsoft gratuita) o 'pyttsx3' (local)
TTS_ENGINE = os.getenv("TTS_ENGINE", "fish")

# Configuración de Fish Audio (Voz de Yize - Cherry)
# ID del modelo: 47a44476780a4f33bba12e834ff1d461
FISH_AUDIO_API_KEY = os.getenv("FISH_AUDIO_API_KEY", "")
FISH_AUDIO_VOICE_ID = os.getenv("FISH_AUDIO_VOICE_ID", "47a44476780a4f33bba12e834ff1d461")

# Configuración de ElevenLabs
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "EXAVITQu4vr4xnSDxMaL")

# Voces de respaldo con Edge-TTS:
# es-MX-DaliaNeural (Suave, joven y conversacional)
# es-AR-ElenaNeural (Femenina y natural)
# es-ES-ElviraNeural (Madura y ejecutiva)
EDGE_VOICE = os.getenv("EDGE_VOICE", "es-MX-DaliaNeural")

# Configuración de Inteligencia Artificial (Gemini)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
GEMINI_FAST_MODEL = os.getenv("GEMINI_FAST_MODEL", "gemini-flash-lite-latest")
GEMINI_SMART_MODEL = os.getenv("GEMINI_SMART_MODEL", "gemini-3.8-flash")

# Directorios de datos
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

CAPTURES_DIR = BASE_DIR / "capturas"
CAPTURES_DIR.mkdir(exist_ok=True)

NOTES_FILE = DATA_DIR / "notas.txt"
SOUNDS_DIR = BASE_DIR / "sonidos"
SOUNDS_DIR.mkdir(exist_ok=True)
