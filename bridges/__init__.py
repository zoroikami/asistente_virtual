"""
bridges — Puentes de comunicación externa (WebSocket, Overlay 3D, VTube Studio).
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_CORE = _ROOT / "core"
_BRIDGES = _ROOT / "bridges"

for _p in [str(_ROOT), str(_CORE), str(_BRIDGES)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)
