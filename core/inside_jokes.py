"""
core/inside_jokes.py - Sistema de Chistes Internos y Comedia Recurrente de Yize
Guarda momentos graciosos, frases célebres y anécdotas compartidas para
retomarlas espontáneamente en momentos oportunos, creando historia y complicidad.
"""

import json
import random
import time
from pathlib import Path
from typing import List, Dict, Optional
from core.config import logger, BASE_DIR

JOKES_FILE = BASE_DIR / "data" / "chistes_internos.json"

CHISTES_POR_DEFECTO = [
    {
        "id": "joke_1",
        "joke": "La vez que pasaste horas depurando código solo para darte cuenta de que no habías guardado el archivo.",
        "tags": ["codigo", "programar", "bug", "error", "guardar", "python", "javascript"],
        "origin": "Clásico error de programador.",
        "times_used": 0,
        "created_at": "2026-10-10"
    },
    {
        "id": "joke_2",
        "joke": "Esa promesa solemne de 'una partidita más y me voy a dormir' a las 3:45 AM.",
        "tags": ["juego", "dormir", "lol", "noche", "desvelo", "mañana"],
        "origin": "Partidas infinitas de madrugada.",
        "times_used": 0,
        "created_at": "2026-10-10"
    },
    {
        "id": "joke_3",
        "joke": "Tu legendaria técnica de cerrar 40 pestañas de Chrome diciendo 'hoy ordeno mi vida'.",
        "tags": ["chrome", "navegador", "ram", "pestañas", "orden"],
        "origin": "Exceso de pestañas abiertas.",
        "times_used": 0,
        "created_at": "2026-10-10"
    }
]


class InsideJokesManager:
    def __init__(self):
        self.jokes: List[Dict] = []
        self._load()

    def _load(self):
        try:
            if JOKES_FILE.exists():
                with open(JOKES_FILE, "r", encoding="utf-8") as f:
                    self.jokes = json.load(f)
            else:
                self.jokes = list(CHISTES_POR_DEFECTO)
                self._save()
        except Exception as e:
            logger.debug(f"[InsideJokes] Error cargando chistes: {e}")
            self.jokes = list(CHISTES_POR_DEFECTO)

    def _save(self):
        try:
            JOKES_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(JOKES_FILE, "w", encoding="utf-8") as f:
                json.dump(self.jokes, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.debug(f"[InsideJokes] Error guardando chistes: {e}")

    def add_joke(self, joke: str, tags: Optional[List[str]] = None, origin: str = "") -> str:
        """Añade un chiste o anécdota recurrente."""
        if not tags:
            # Auto-inferir tags básicos de las palabras más largas
            palabras = [w.lower().strip(".,:;!?") for w in joke.split() if len(w) > 4]
            tags = palabras[:4] or ["general"]

        new_item = {
            "id": f"joke_{int(time.time())}",
            "joke": joke.strip(),
            "tags": [t.lower().strip() for t in tags],
            "origin": origin.strip(),
            "times_used": 0,
            "created_at": time.strftime("%Y-%m-%d %H:%M")
        }
        self.jokes.append(new_item)
        self._save()
        logger.info(f"😂 [InsideJokes] Nuevo chiste guardado: '{joke[:40]}...' tags={tags}")
        return f"Anotado en mi colección de chistes internos: '{joke}'."

    def get_relevant_joke(self, text: str) -> Optional[Dict]:
        """Busca un chiste que coincida con las palabras del texto actual."""
        if not self.jokes:
            return None

        text_lower = text.lower()
        coincidencias = []
        for j in self.jokes:
            score = sum(1 for tag in j.get("tags", []) if tag in text_lower)
            if score > 0:
                coincidencias.append((score, j))

        if coincidencias:
            # Elegir la que más coincidencias tenga (o la menos usada)
            coincidencias.sort(key=lambda x: (x[0], -x[1].get("times_used", 0)), reverse=True)
            mejor = coincidencias[0][1]
            mejor["times_used"] = mejor.get("times_used", 0) + 1
            self._save()
            return mejor

        return None

    def get_random_joke(self) -> Optional[str]:
        if not self.jokes:
            return None
        j = random.choice(self.jokes)
        j["times_used"] = j.get("times_used", 0) + 1
        self._save()
        return j["joke"]

    def format_for_prompt(self, max_count: int = 5) -> str:
        """Formatea un resumen para inyectar en las instrucciones del sistema de Gemini/Ollama."""
        if not self.jokes:
            return ""

        # Tomar los 5 más recientes o más variados
        sample = self.jokes[-max_count:]
        lineas = []
        for j in sample:
            tags_str = ", ".join(j.get("tags", []))
            lineas.append(f"- [{tags_str}]: \"{j.get('joke')}\"")

        return (
            "\nANÉCDOTAS Y CHISTES INTERNOS COMPARTIDOS CON EL USUARIO (Comedia recurrente):\n"
            "Si la conversación se relaciona con alguno de estos temas, haz referencias cómplices y sarcásticas a ellos:\n"
            + "\n".join(lineas) + "\n"
        )


jokes_manager = InsideJokesManager()
