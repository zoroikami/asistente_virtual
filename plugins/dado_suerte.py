"""
plugins/dado_suerte.py — Plugin de ejemplo: Tirar dados y número de la suerte
"""
import random

NAME = "Dado de la Suerte"
DESCRIPTION = "Lanza un dado de 6 o 20 caras y consulta tu suerte."
TRIGGERS = ["tira un dado", "lanza un dado", "dado d20", "número de la suerte", "mi suerte hoy"]

def run(command: str) -> tuple[bool, str]:
    cmd = command.lower()
    if "d20" in cmd:
        res = random.randint(1, 20)
        comentario = "¡Pifia crítica! Qué desastre." if res == 1 else ("¡Crítico natural! Eres un dios." if res == 20 else "Tirada decente.")
        return True, f"[smug] Salió un {res} en el D20. {comentario}"
    elif "suerte" in cmd:
        num = random.randint(1, 100)
        return True, f"[happy] Tu número de la suerte hoy es el {num}. No te fíes mucho, pero ahí lo tienes."
    else:
        res = random.randint(1, 6)
        return True, f"[relaxed] El dado cayó en {res}."
