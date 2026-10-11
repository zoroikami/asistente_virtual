"""
core/plugin_manager.py — Sistema Modular de Plugins para Yize
Permite extender las habilidades de Yize simplemente agregando archivos .py
dentro de la carpeta plugins/. Cada plugin se autocarga dinámicamente.
"""

import sys
import importlib.util
from pathlib import Path
from typing import Dict, List, Tuple
from core.config import logger, BASE_DIR

PLUGINS_DIR = BASE_DIR / "plugins"


class PluginManager:
    def __init__(self):
        self.plugins: Dict[str, dict] = {}
        self.load_plugins()

    def load_plugins(self):
        PLUGINS_DIR.mkdir(parents=True, exist_ok=True)
        self.plugins.clear()

        for file_path in PLUGINS_DIR.glob("*.py"):
            if file_path.name.startswith("_"):
                continue

            plugin_name = file_path.stem
            try:
                spec = importlib.util.spec_from_file_location(plugin_name, str(file_path))
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)

                    if hasattr(mod, "run") and hasattr(mod, "TRIGGERS"):
                        self.plugins[plugin_name] = {
                            "name": getattr(mod, "NAME", plugin_name),
                            "description": getattr(mod, "DESCRIPTION", "Plugin sin descripción"),
                            "triggers": [t.lower().strip() for t in getattr(mod, "TRIGGERS", [])],
                            "module": mod,
                        }
                        logger.info(f"🧩 [Plugin] Cargado: {plugin_name} ('{self.plugins[plugin_name]['name']}')")
            except Exception as e:
                logger.error(f"❌ [Plugin] Error cargando {plugin_name}: {e}")

    def dispatch(self, command: str) -> Tuple[bool, str]:
        cmd_lower = command.lower().strip()
        for _, pdata in self.plugins.items():
            for t in pdata["triggers"]:
                if t in cmd_lower or cmd_lower.startswith(t):
                    try:
                        ok, res = pdata["module"].run(command)
                        if ok:
                            return True, res
                    except Exception as e:
                        logger.debug(f"[Plugin] Error en ejecución: {e}")
        return False, ""

    def list_plugins(self) -> str:
        if not self.plugins:
            return "No hay plugins adicionales instalados en la carpeta plugins/."
        lineas = [f"• {p['name']}: {p['description']}" for p in self.plugins.values()]
        return "Plugins activos cargados:\n" + "\n".join(lineas)


plugin_manager = PluginManager()
