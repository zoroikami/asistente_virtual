"""
memory.py — Sistema de memoria persistente a largo plazo para Yize.
Permite a Yize recordar hechos, preferencias, proyectos y aprendizajes
a través de reinicios del sistema.
"""
import json
import os
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
MEMORY_FILE = (DATA_DIR / "memoria_yize.json") if (DATA_DIR / "memoria_yize.json").exists() else (BASE_DIR / "memoria_yize.json")

DEFAULT_MEMORY = {
    "perfil_usuario": {
        "nombre_o_apodo": "Usuario",
        "intereses_y_juegos": "League of Legends, Fortnite, Anime (Crunchyroll, jkanime), tecnología",
        "estilo_preferido": "Enérgico, divertido, pícaro y directo (inspirado en Millie de Helluva Boss), con humor, capacidad de debate y ayuda técnica en Windows."
    },
    "aprendizajes_y_preferencias": {
        "fortnite": "Ubicado en C:\\Users\\kj\\Desktop\\Fortnite.url y launcher de Epic Games.",
        "league_of_legends": "Ubicado en C:\\Users\\Public\\Desktop\\League of Legends.lnk y C:\\Riot Games.",
        "voz": "Voz configurada."
    },
    "proyectos_y_contexto": {
        "asistente": "Yize tiene un cuerpo virtual 3D con control de Windows (teclado, ratón, terminal, archivos y visión)."
    }
}


def _load_memory() -> dict:
    """Carga el archivo JSON de memoria o lo crea con valores por defecto."""
    if not MEMORY_FILE.exists():
        _save_raw_memory(DEFAULT_MEMORY)
        return DEFAULT_MEMORY.copy()
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[Memoria] Error cargando memoria: {e}")
        return DEFAULT_MEMORY.copy()


def _save_raw_memory(data: dict) -> bool:
    """Guarda los datos en el archivo JSON."""
    try:
        MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[Memoria] Error guardando memoria: {e}")
        return False


def guardar_recuerdo(categoria: str, clave: str, valor: str) -> str:
    """
    Guarda un nuevo hecho o preferencia en la memoria a largo plazo de Yize.
    Args:
        categoria: 'perfil_usuario', 'aprendizajes_y_preferencias' o 'proyectos_y_contexto'.
        clave: Tema o concepto a recordar (ej. 'juego_favorito', 'libreria_preferida').
        valor: La información detallada a recordar.
    """
    data = _load_memory()
    cat = categoria.strip().lower().replace(" ", "_")
    if cat not in data:
        data[cat] = {}
    data[cat][clave.strip()] = valor.strip()
    if _save_raw_memory(data):
        return f"Memoria actualizada: recordaré que en '{cat}', '{clave}' es '{valor}'."
    return "Error al guardar en memoria."


def consultar_recuerdos(termino: str = "") -> str:
    """
    Consulta la memoria a largo plazo de Yize.
    Si se pasa un término, busca coincidencias; si está vacío, devuelve un resumen.
    """
    data = _load_memory()
    if not termino or not termino.strip():
        return get_memory_prompt_summary()

    term_low = termino.lower()
    coincidencias = []
    for cat, items in data.items():
        if isinstance(items, dict):
            for k, v in items.items():
                if term_low in k.lower() or term_low in str(v).lower():
                    coincidencias.append(f"[{cat}] {k}: {v}")

    if coincidencias:
        return "Recuerdos encontrados:\n" + "\n".join(coincidencias)
    return f"No encontré recuerdos asociados a '{termino}'."


def get_memory_prompt_summary() -> str:
    """
    Genera un resumen conciso de la memoria persistente para inyectarlo en el System Prompt.
    """
    data = _load_memory()
    lineas = []
    for cat, items in data.items():
        if isinstance(items, dict):
            sublineas = [f"- {k}: {v}" for k, v in items.items()]
            lineas.append(f"**{cat.replace('_', ' ').title()}**:\n" + "\n".join(sublineas))
    return "\n\n".join(lineas)
