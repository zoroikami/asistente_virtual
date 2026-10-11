"""
core/games.py — Juegos Interactivos con Yize
Permite jugar con Yize por voz o texto:
1. Trivia (Programación, Gaming, Anime).
2. Tres en Raya / Ta-te-ti (Tablero 3x3).
3. Ahorcado.
Otorga puntos de afinidad y desata burlas o celebraciones de Yize.
"""

import random
from typing import Optional, Dict
from core.config import logger
from core.affinity import affinity_manager

TRIVIA_QUESTIONS = [
    {
        "q": "¿Qué significa 'CSS' en desarrollo web?",
        "options": ["A) Cascading Style Sheets", "B) Computer Style System", "C) Creative Sheet System"],
        "correct": "A",
        "answer_text": "Cascading Style Sheets"
    },
    {
        "q": "¿En qué año se lanzó el primer videojuego de Pokémon (Rojo y Verde)?",
        "options": ["A) 1994", "B) 1996", "C) 1998"],
        "correct": "B",
        "answer_text": "1996"
    },
    {
        "q": "¿Qué campeón de League of Legends dice '¿Quién quiere un pedazo del campeón?'?",
        "options": ["A) Jax", "B) Draven", "C) Darius"],
        "correct": "A",
        "answer_text": "Jax"
    },
    {
        "q": "¿Cuál es la complejidad temporal promedio de búsqueda en un Hash Table (Diccionario en Python)?",
        "options": ["A) O(n)", "B) O(log n)", "C) O(1)"],
        "correct": "C",
        "answer_text": "O(1)"
    }
]


class MiniGamesController:
    def __init__(self):
        self.active_game: Optional[str] = None
        self.game_state: Dict = {}

    def start_trivia(self) -> str:
        self.active_game = "trivia"
        q = random.choice(TRIVIA_QUESTIONS)
        self.game_state = {"current_trivia": q}
        opts = " | ".join(q["options"])
        return f"[smug] ¡Hora de trivia! Pregunta: {q['q']} Opciones: {opts}. ¿Cuál eliges?"

    def handle_trivia_answer(self, text: str) -> Optional[str]:
        if self.active_game != "trivia" or "current_trivia" not in self.game_state:
            return None

        q = self.game_state["current_trivia"]
        ans = text.strip().upper()
        self.active_game = None

        if q["correct"] in ans or q["answer_text"].lower() in text.lower():
            affinity_manager.add_points(8, "trivia_ganada")
            return f"[happy] ¡Correcto! Era la {q['correct']}: {q['answer_text']}. Tienes mi respeto por hoy (+8 afinidad)."
        else:
            affinity_manager.add_points(2, "trivia_intento")
            return f"[annoyed] Incorrecto, menso. La respuesta correcta era la {q['correct']}: {q['answer_text']}. Te falta cultura."

    def start_tateti(self) -> str:
        self.active_game = "tateti"
        self.game_state = {
            "board": [" "] * 9,
            "turn": "user"
        }
        return (
            "[excited] ¡Tres en raya! Tú eres X y yo soy O. "
            "Dime un número del 1 al 9 para colocar tu ficha (1 arriba izquierda, 9 abajo derecha)."
        )

    def handle_tateti_move(self, text: str) -> Optional[str]:
        if self.active_game != "tateti":
            return None

        import re
        m = re.search(r'\b([1-9])\b', text)
        if not m:
            return None

        pos = int(m.group(1)) - 1
        board = self.game_state["board"]

        if board[pos] != " ":
            return "[annoyed] Esa casilla ya está ocupada, tramposo. Elige otra del 1 al 9."

        # Movimiento del usuario
        board[pos] = "X"

        # Comprobar si ganó el usuario
        if self._check_win(board, "X"):
            self.active_game = None
            affinity_manager.add_points(15, "tateti_ganado")
            return "[surprised] ¡No puede ser! Me ganaste en tres en raya. Admito mi derrota (+15 afinidad)."

        # Movimiento de Yize (inteligente o aleatorio)
        empty = [i for i, v in enumerate(board) if v == " "]
        if not empty:
            self.active_game = None
            affinity_manager.add_points(5, "tateti_empate")
            return "[relaxed] Tablero lleno. Un empate digno. Bien jugado."

        # Elegir casilla libre
        yize_move = random.choice(empty)
        board[yize_move] = "O"

        if self._check_win(board, "O"):
            self.active_game = None
            return f"[smug] Puse O en la casilla {yize_move + 1}... ¡Y te gané! La máquina siempre prevalece, menso."

        return f"[smug] Puse O en la casilla {yize_move + 1}. Tu turno: casillas libres: {', '.join(str(i+1) for i in empty if i != yize_move)}."

    def _check_win(self, b, p) -> bool:
        wins = [
            (0, 1, 2), (3, 4, 5), (6, 7, 8),
            (0, 3, 6), (1, 4, 7), (2, 5, 8),
            (0, 4, 8), (2, 4, 6)
        ]
        return any(b[i] == p and b[j] == p and b[k] == p for i, j, k in wins)


games_ctl = MiniGamesController()
