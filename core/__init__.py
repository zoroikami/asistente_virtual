"""
core — Núcleo de inteligencia, lógica de sistema y hardware para Yize.
"""
import sys
from pathlib import Path

# Registrar directorios en sys.path para compatibilidad universal
_ROOT = Path(__file__).resolve().parent.parent
_CORE = _ROOT / "core"
_BRIDGES = _ROOT / "bridges"

for _p in [str(_ROOT), str(_CORE), str(_BRIDGES)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)
