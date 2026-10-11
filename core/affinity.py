"""
core/affinity.py — Sistema de Afinidad y Vínculo (Bond Level)
Gamificación de la relación con Yize:
Sube puntos con el tiempo compartido, partidas jugadas y órdenes cumplidas,
desbloqueando gradualmente un trato más cercano y cómplice.
"""

import json
import time
from pathlib import Path
from core.config import logger, BASE_DIR

AFFINITY_FILE = BASE_DIR / "data" / "afinidad.json"

LEVELS = [
    (0, 1, "Tsundere Distante", "Te trata como a un usuario cualquiera; sarcasmo puro y desconfianza."),
    (50, 2, "Compañera Tolerante", "Ya se acostumbró a tu presencia; bromea más y se queja menos."),
    (150, 3, "Amiga Leal", "Te felicita cuando logras algo y defiende tu tiempo de descanso."),
    (300, 4, "Cómplice Incondicional", "Muestra preocupación genuina, apodos y bromas exclusivas."),
    (500, 5, "Vínculo Máximo", "Confianza absoluta; poses cariñosas y lealtad total frente a todo."),
]


class AffinityManager:
    def __init__(self):
        self.data = {
            "points": 10,
            "level": 1,
            "rank": "Tsundere Distante",
            "last_interaction": time.time(),
            "games_played": 0,
            "time_together_minutes": 0,
        }
        self._load()

    def _load(self):
        try:
            if AFFINITY_FILE.exists():
                with open(AFFINITY_FILE, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    self.data.update(saved)
                    self._update_level()
        except Exception as e:
            logger.debug(f"[Affinity] Error cargando afinidad: {e}")

    def _save(self):
        try:
            AFFINITY_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(AFFINITY_FILE, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.debug(f"[Affinity] Error guardando afinidad: {e}")

    def _update_level(self):
        pts = self.data["points"]
        current_lvl = 1
        current_rank = "Tsundere Distante"
        for min_pts, lvl, rank, _ in LEVELS:
            if pts >= min_pts:
                current_lvl = lvl
                current_rank = rank
            else:
                break
        self.data["level"] = current_lvl
        self.data["rank"] = current_rank

    def add_points(self, amount: int, reason: str = "") -> str:
        """Suma puntos de afinidad y notifica si hubo subida de nivel."""
        prev_lvl = self.data["level"]
        self.data["points"] = max(0, self.data["points"] + amount)
        self.data["last_interaction"] = time.time()
        self._update_level()
        self._save()

        if self.data["level"] > prev_lvl:
            return (
                f"¡Subimos de nivel de afinidad! Nivel {self.data['level']}: {self.data['rank']}. "
                "Supongo que ya no me caes tan mal después de todo."
            )
        return ""

    def get_status_report(self) -> str:
        pts = self.data["points"]
        lvl = self.data["level"]
        rank = self.data["rank"]
        # Calcular puntos para el siguiente nivel
        next_pts = "Máximo"
        for min_pts, l, _, _ in LEVELS:
            if l == lvl + 1:
                next_pts = f"{min_pts - pts} pts más"
                break

        return (
            f"[happy] Nivel de afinidad: {lvl} ({rank}) con {pts} puntos. "
            f"Siguiente rango: {next_pts}. ¿Ves? Pasar tiempo conmigo sí da frutos."
        )

    def get_prompt_instruction(self) -> str:
        """Instrucción para inyectar en Gemini/Ollama según el nivel alcanzado."""
        lvl = self.data.get("level", 1)
        rank = self.data.get("rank", "Tsundere Distante")
        if lvl == 1:
            return f"NIVEL DE AFINIDAD CON EL USUARIO: {lvl} ({rank}). Eres distante, mordaz y lo tratas como un conocido que debe ganarse tu respeto."
        elif lvl == 2:
            return f"NIVEL DE AFINIDAD CON EL USUARIO: {lvl} ({rank}). Ya toleras su presencia, sueltas bromas más cómplices y aceptas sus gustos."
        elif lvl == 3:
            return f"NIVEL DE AFINIDAD CON EL USUARIO: {lvl} ({rank}). Lo consideras un amigo leal, te alegras por sus logros y lo animas si falla."
        elif lvl >= 4:
            return f"NIVEL DE AFINIDAD CON EL USUARIO: {lvl} ({rank}). Cómplice incondicional, tono cariñoso bajo la fachada divertida, confianza total."
        return ""


affinity_manager = AffinityManager()
