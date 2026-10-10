"""
vts_bridge.py — Conector oficial entre Yize y VTube Studio (Live2D).
Permite controlar el avatar Live2D en tiempo real:
- Sincronización labial (Lip Sync) mientras habla el asistente.
- Expresiones faciales y hotkeys según emociones o telemetría.
- Movimiento y estados (pensando, escuchando, hablando).
"""
import os
import sys
import time
import math
import asyncio
import threading
from pathlib import Path

# Codificación UTF-8
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent
TOKEN_FILE = BASE_DIR / "vts_token.txt"

PLUGIN_INFO = {
    "plugin_name": "Yize Assistant",
    "developer": "Yize AI",
    "authentication_token_path": str(TOKEN_FILE)
}

class VTubeStudioBridge:
    """Manejador de conexión y control para VTube Studio."""
    def __init__(self, port: int = 8001):
        self.port = port
        self.is_connected = False
        self.is_authenticated = False
        self.vts = None
        self._loop = None
        self._thread = None
        self._is_talking = False
        self._lip_thread = None
        self.available_hotkeys = []

    def start_background(self):
        """Inicia el bucle de eventos asíncronos en segundo plano."""
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self._thread.start()

    def _run_event_loop(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._connect_and_auth())
        self._loop.run_forever()

    async def _connect_and_auth(self) -> bool:
        """Intenta conectar y autenticar con VTube Studio."""
        import pyvts
        try:
            self.vts = pyvts.vts(plugin_info=PLUGIN_INFO, port=self.port)
            await self.vts.connect()
            self.is_connected = True
            print("✅ [VTS] Conectado a VTube Studio en puerto", self.port)

            # Autenticación con token
            if not TOKEN_FILE.exists() or not TOKEN_FILE.read_text().strip():
                print("🔑 [VTS] Solicitando autorización en VTube Studio... ¡Haz clic en 'Allow' en la ventana de VTS!")
                await self.vts.request_authenticate_token()
                await self.vts.write_token()

            await self.vts.read_token()
            auth_res = await self.vts.request_authenticate()
            if self.vts.get_authentic_status():
                self.is_authenticated = True
                print("✨ [VTS] ¡Yize vinculada exitosamente con tu modelo Live2D!")
                await self._fetch_hotkeys()
                return True
            else:
                print("⚠️ [VTS] Autorización pendiente o rechazada en VTube Studio.")
                return False
        except ConnectionRefusedError:
            self.is_connected = False
            self.is_authenticated = False
            return False
        except Exception as e:
            self.is_connected = False
            self.is_authenticated = False
            print(f"[VTS] Aviso de conexión: {e}")
            return False

    async def _fetch_hotkeys(self):
        """Obtiene la lista de hotkeys disponibles en el modelo actual."""
        if not self.is_authenticated:
            return
        try:
            req = self.vts.vts_request.requestHotKeyList()
            res = await self.vts.request(req)
            if res and "data" in res and "availableHotkeys" in res["data"]:
                self.available_hotkeys = res["data"]["availableHotkeys"]
                nombres = [h.get("name") for h in self.available_hotkeys if h.get("name")]
                if nombres:
                    print(f"🎭 [VTS] Hotkeys detectadas en tu modelo: {', '.join(nombres)}")
        except Exception:
            pass

    def run_coroutine(self, coro):
        """Ejecuta una corrutina en el hilo de VTS de forma segura."""
        if self._loop and self._loop.is_running():
            return asyncio.run_coroutine_threadsafe(coro, self._loop)
        return None

    # ──────────────────────────────────────────────────────────────────────────
    # Control de Sincronización Labial (Lip Sync)
    # ──────────────────────────────────────────────────────────────────────────

    def start_speaking_lip_sync(self):
        """Inicia animación procedural de movimiento de boca mientras habla."""
        if self._is_talking:
            return
        self._is_talking = True
        self._lip_thread = threading.Thread(target=self._lip_sync_loop, daemon=True)
        self._lip_thread.start()

    def stop_speaking_lip_sync(self):
        """Detiene el movimiento de boca y la cierra."""
        self._is_talking = False
        self.set_parameter("MouthOpen", 0.0)

    def _lip_sync_loop(self):
        """Genera aperturas y cierres naturales de boca mientras habla."""
        angle = 0.0
        while self._is_talking:
            if not self.is_authenticated:
                time.sleep(0.1)
                continue
            angle += 0.35
            # Oscilación natural entre 0.1 y 0.85
            val = (math.sin(angle) + 1.0) / 2.0 * 0.75 + 0.1
            self.set_parameter("MouthOpen", round(val, 2))
            time.sleep(0.045)
        # Cerrar boca al terminar
        self.set_parameter("MouthOpen", 0.0)

    # ──────────────────────────────────────────────────────────────────────────
    # Inyección de Parámetros y Expresiones
    # ──────────────────────────────────────────────────────────────────────────

    def set_parameter(self, param_name: str, value: float):
        """Envía un valor de parámetro a Live2D (ej. MouthOpen, FaceAngleX, etc.)."""
        if not self.is_authenticated or not self.vts:
            return

        async def _set():
            try:
                req = self.vts.vts_request.requestSetParameterValue(parameter=param_name, value=value)
                await self.vts.request(req)
            except Exception:
                pass

        self.run_coroutine(_set())

    def trigger_hotkey_by_name(self, name: str):
        """Dispara un hotkey por su nombre (ej. 'smile', 'angry', 'blush')."""
        if not self.is_authenticated or not self.vts:
            return

        target_id = None
        for hk in self.available_hotkeys:
            if name.lower() in hk.get("name", "").lower():
                target_id = hk.get("hotkeyID")
                break

        if not target_id:
            return

        async def _trigger():
            try:
                req = self.vts.vts_request.requestTriggerHotKey(hotkeyID=target_id)
                await self.vts.request(req)
                print(f"🎭 [VTS] Expresión activada: '{name}'")
            except Exception as e:
                print(f"[VTS] Error activando hotkey: {e}")

        self.run_coroutine(_trigger())

    # ──────────────────────────────────────────────────────────────────────────
    # Posturas y Reacciones de Estado (VTube Studio)
    # ──────────────────────────────────────────────────────────────────────────

    def set_state(self, state: str):
        """Ajusta las posturas y gestos faciales del modelo Live2D según el estado de Ruan Mei."""
        if not self.is_authenticated:
            return

        if state == "listening":
            # Inclinar suavemente la cabeza con atención
            self.set_parameter("FaceAngleZ", 4.0)
            self.set_parameter("FaceAngleY", 2.0)
            self.set_parameter("MouthSmile", 0.2)
        elif state == "thinking":
            # Mirada reflexiva hacia arriba / lateral
            self.set_parameter("FaceAngleX", -4.0)
            self.set_parameter("FaceAngleY", 6.0)
            self.set_parameter("FaceAngleZ", -3.0)
            self.set_parameter("Brows", 0.3)
        elif state == "speaking":
            self.set_parameter("FaceAngleZ", 1.0)
            self.set_parameter("MouthSmile", 0.5)
        elif state == "idle":
            # Postura serena natural
            self.set_parameter("FaceAngleX", 0.0)
            self.set_parameter("FaceAngleY", 0.0)
            self.set_parameter("FaceAngleZ", 0.0)
            self.set_parameter("Brows", 0.0)


# Instancia Singleton compartida
_bridge_instance = None

def get_vts_bridge() -> VTubeStudioBridge:
    global _bridge_instance
    if _bridge_instance is None:
        _bridge_instance = VTubeStudioBridge()
    return _bridge_instance


if __name__ == "__main__":
    print("=======================================================")
    print("       CONECTOR DE YIZE CON VTUBE STUDIO (LIVE2D)      ")
    print("=======================================================")
    print("\nVerificando si VTube Studio tiene la API activada en el puerto 8001...\n")

    bridge = get_vts_bridge()
    bridge.start_background()

    time.sleep(2)
    if not bridge.is_connected:
        print("\n⚠️ VTube Studio está abierto, pero la API aún no está activada.")
        print("\n👉 Pasos para activarla en VTube Studio:")
        print("  1. Haz clic en el ícono de engranaje (⚙️ Ajustes) en el menú lateral.")
        print("  2. En la pestaña de configuración, baja hasta 'VTube Studio API'.")
        print("  3. Activa la casilla 'Iniciar API (Permitir plugins)' [puerto 8001].")
        print("  4. Cuando aparezca el cartel, presiona 'Allow' para autorizar a Yize.")
        print("\nEsperando conexión (presiona Ctrl+C para salir)...")
        while not bridge.is_authenticated:
            time.sleep(1)
            # Reintentar conexión periódicamente si se activó el switch
            if not bridge.is_connected and bridge._loop:
                asyncio.run_coroutine_threadsafe(bridge._connect_and_auth(), bridge._loop)

    print("\n🎉 ¡CONEXIÓN EXITOSA!")
    print("Probando movimiento de boca (Lip Sync) durante 3 segundos...")
    bridge.start_speaking_lip_sync()
    time.sleep(3)
    bridge.stop_speaking_lip_sync()
    print("✅ Prueba completada.")
