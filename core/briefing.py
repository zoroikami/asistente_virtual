"""
core/briefing.py — Buenos Días Personalizado de Yize
Resumen matutino conciso de 20 segundos al arrancar:
1. Clima en tiempo real de Santiago de Chile.
2. Tareas o notas pendientes del usuario.
3. Resumen sarcástico del diario de la sesión anterior.
4. Saludo animado (wave) en el modelo 3D.
"""

import json
import urllib.request
from pathlib import Path
from core.config import logger, BASE_DIR

WEATHER_CODES = {
    0: "despejado y soleado",
    1: "principalmente despejado",
    2: "parcialmente nublado",
    3: "nublado",
    45: "con niebla",
    48: "con niebla densa",
    51: "con llovizna suave",
    61: "con lluvia ligera",
    63: "con lluvia moderada",
    65: "con lluvia intensa",
    71: "con nieve",
    95: "con tormenta eléctrica",
}


def get_santiago_weather() -> str:
    """Obtiene temperatura y condición actual de Santiago de Chile vía Open-Meteo."""
    try:
        url = "https://api.open-meteo.com/v1/forecast?latitude=-33.4569&longitude=-70.6483&current_weather=true"
        req = urllib.request.Request(url, headers={"User-Agent": "YizeCopilot/1.0"})
        with urllib.request.urlopen(req, timeout=3.5) as resp:
            data = json.loads(resp.read().decode())
            cw = data.get("current_weather", {})
            temp = round(cw.get("temperature", 18), 1)
            code = cw.get("weathercode", 0)
            cond = WEATHER_CODES.get(code, "tiempo templado")
            return f"{temp}°C, {cond}"
    except Exception as e:
        logger.debug(f"[Briefing] No se pudo obtener clima: {e}")
        return "un clima templado"


def get_morning_briefing() -> str:
    """Genera el mensaje completo del Buenos Días personalizado."""
    clima = get_santiago_weather()

    # 1. Notas pendientes
    notas_file = BASE_DIR / "data" / "notas.txt"
    num_notas = 0
    if notas_file.exists():
        try:
            lineas = [l.strip() for l in notas_file.read_text(encoding="utf-8").splitlines() if l.strip()]
            num_notas = len(lineas)
        except Exception:
            pass

    # 2. Resumen del diario anterior
    resumen_ayer = ""
    try:
        from core.diario import get_diario
        ultima = get_diario().leer_ultima_entrada()
        if ultima:
            lineas = [l.strip().replace('"', '').replace('>', '').strip() for l in ultima.splitlines() if l.strip()]
            if lineas:
                # Extraer última frase corta
                frase = lineas[-1]
                if len(frase) > 85:
                    frase = frase[:85] + "..."
                resumen_ayer = f" En mi diario de ayer anoté: \"{frase}\"."
    except Exception:
        pass

    tareas_txt = f"Tienes {num_notas} tareas anotadas en tus notas." if num_notas > 0 else "Tu lista de notas está limpia (o no has anotado nada)."

    saludo = (
        f"[happy] ¡Buenos días! En Santiago tenemos {clima}. {tareas_txt}{resumen_ayer} "
        "En marcha, no te quedes dormido frente al monitor."
    )

    # Disparar saludo físico en el overlay
    try:
        from bridges.overlay_bridge import overlay_bridge
        overlay_bridge.send_wave()
    except Exception:
        pass

    return saludo
