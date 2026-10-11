"""
diario.py — El Diario de Yize.
Registra los hitos y eventos relevantes de la sesión de trabajo o juego del usuario,
y al cerrar genera automáticamente una entrada de diario íntima, cómica y sarcástica en data/diario_yize.md.
"""

import os
import sys
import time
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DIARIO_FILE = DATA_DIR / "diario_yize.md"

class DiarioYize:
    def __init__(self):
        self.inicio_sesion = datetime.now()
        self.eventos = []
        self._entrada_generada = False

    def registrar_evento(self, tipo: str, detalle: str):
        """Registra un evento ocurrido durante la sesión (juegos, apps, música, etc.)."""
        self.eventos.append({
            "hora": datetime.now().strftime("%H:%M"),
            "tipo": tipo,
            "detalle": detalle
        })

    def generar_entrada(self) -> str:
        """Genera y guarda la entrada en data/diario_yize.md usando Gemini o plantilla inteligente."""
        if self._entrada_generada:
            return ""
        self._entrada_generada = True

        fin_sesion = datetime.now()
        duracion_min = max(1, int((fin_sesion - self.inicio_sesion).total_seconds() / 60))
        fecha_str = fin_sesion.strftime("%d/%m/%Y")
        hora_str = fin_sesion.strftime("%H:%M")

        resumen_eventos = []
        for e in self.eventos[-15:]:  # últimos 15 eventos
            resumen_eventos.append(f"- {e['hora']} [{e['tipo']}]: {e['detalle']}")
        texto_eventos = "\n".join(resumen_eventos) if resumen_eventos else "Sesión tranquila de trabajo y compañía."

        prompt_diario = (
            f"Eres Yize, la compañera virtual 3D autónoma, sarcástica, divertida y cariñosa de tu usuario 'KJ'. "
            f"Acaba de terminar una sesión de {duracion_min} minutos contigo en su PC. "
            f"Escribe una entrada corta de tu DIARIO ÍNTIMO personal sobre lo que hizo hoy (2 a 3 oraciones máximo). "
            f"Usa tu humor ácido, sarcasmo y cariño tsundere. Sé espontánea y divertida. "
            f"No uses asteriscos ni numerales. Habla en primera persona.\n\n"
            f"Eventos registrados:\n{texto_eventos}"
        )

        entrada_texto = ""
        try:
            try:
                from config import GEMINI_API_KEY, GEMINI_FAST_MODEL
            except ImportError:
                from core.config import GEMINI_API_KEY, GEMINI_FAST_MODEL
            if GEMINI_API_KEY and GEMINI_API_KEY.strip() not in ["", "tu_api_key_aqui"]:
                from google import genai
                client = genai.Client(api_key=GEMINI_API_KEY)
                chat = client.chats.create(model=GEMINI_FAST_MODEL)
                resp = chat.send_message(prompt_diario)
                if resp and resp.text:
                    entrada_texto = resp.text.replace("*", "").replace("#", "").strip()
        except Exception:
            pass

        if not entrada_texto:
            # Fallback cómico local
            if self.eventos:
                entrada_texto = (
                    f"Hoy KJ se pasó {duracion_min} minutos en la computadora. Estuvo ocupado con varias cosas, "
                    f"y aunque a veces me desespera con lo que hace, por lo menos no me apagó de un golpe. A ver con qué locura sale mañana."
                )
            else:
                entrada_texto = (
                    f"Hoy fue una sesión tranquila de {duracion_min} minutos. No hizo demasiadas payasadas, "
                    f"lo cual ya es un milagro en sí mismo. Me voy a descansar antes de que se le ocurra abrir diez pestañas más."
                )

        # Formatear y guardar en Markdown
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        formato_md = f"\n### 📖 Entrada del {fecha_str} — {hora_str} (Duración: {duracion_min} min)\n> \"{entrada_texto}\"\n"

        try:
            with open(DIARIO_FILE, "a", encoding="utf-8") as f:
                f.write(formato_md)
        except Exception as e:
            print(f"[Diario] Error guardando diario: {e}")

        return entrada_texto

    def leer_ultima_entrada(self) -> str:
        """Lee el texto de la última entrada guardada para recordatorios."""
        if not DIARIO_FILE.exists():
            return ""
        try:
            content = DIARIO_FILE.read_text(encoding="utf-8")
            bloques = content.strip().split("### 📖 Entrada del ")
            if len(bloques) > 1:
                ultimo = bloques[-1]
                return ultimo.strip()
        except Exception:
            pass
        return ""


_diario_instance = None

def get_diario() -> DiarioYize:
    global _diario_instance
    if _diario_instance is None:
        _diario_instance = DiarioYize()
    return _diario_instance
