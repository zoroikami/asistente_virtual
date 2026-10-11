"""
overlay_bridge.py — Servidor WebSocket que conecta el backend de Yize
con el overlay Tauri. Se ejecuta junto con main.py o brain.py.

Protocolo (JSON):
  → Backend a Overlay:
    { "type": "speech",     "text": "...", "emotion": "happy" }
    { "type": "speech_end" }
    { "type": "listen_start" }
    { "type": "emotion",    "emotion": "surprised" }
    { "type": "idle_thought","text": "..." }

  ← Overlay a Backend:
    { "type": "command",    "cmd": "wave" | "dismiss" }
"""

import sys
import asyncio
import json
import logging
import threading
import websockets
from typing import Optional, Callable

logger = logging.getLogger("overlay_bridge")

# ─── Singleton del bridge ─────────────────────────────────────────────────────
class OverlayBridge:
    _instance: Optional["OverlayBridge"] = None
    
    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.clients: set = set()
        self.command_callback: Optional[Callable] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._audio_done_event = threading.Event()
        self._last_shake_time = 0.0
        self._last_poke_time = 0.0

    @classmethod
    def get(cls) -> "OverlayBridge":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ─── Servidor ─────────────────────────────────────────────────────────
    async def _handler(self, websocket):
        self.clients.add(websocket)
        logger.info(f"🔗 Overlay conectado ({len(self.clients)} clientes)")
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    logger.debug(f"← Overlay: {data}")
                    msg_type = data.get("type")
                    if msg_type == "audio_done":
                        self._audio_done_event.set()
                    elif msg_type == "poke":
                        self._handle_poke()
                    elif msg_type == "command" and data.get("cmd") == "shake":
                        self._handle_shake()
                    elif msg_type == "file_drop":
                        self._handle_file_drop(data)
                    elif self.command_callback:
                        self.command_callback(data)
                except json.JSONDecodeError:
                    pass
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.clients.discard(websocket)
            logger.info(f"🔌 Overlay desconectado ({len(self.clients)} clientes)")

    async def _serve(self):
        async with websockets.serve(self._handler, self.host, self.port):
            logger.info(f"🌐 Bridge WebSocket en ws://{self.host}:{self.port}")
            self._running = True
            await asyncio.Future()  # Corre para siempre

    def _run_loop(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._serve())
        except Exception as e:
            logger.error(f"Error en bridge: {e}")

    def start(self):
        """Inicia el servidor en un thread separado."""
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="OverlayBridge")
        self._thread.start()
        logger.info("✅ OverlayBridge iniciado")

    # ─── Enviar mensajes al overlay ───────────────────────────────────────
    def _send_sync(self, data: dict):
        """Enviar desde un thread que NO es el del event loop."""
        if not self._loop or not self.clients:
            return
        message = json.dumps(data, ensure_ascii=False)
        for client in list(self.clients):
            asyncio.run_coroutine_threadsafe(client.send(message), self._loop)

    def send_audio(self, audio_path: str, text: str = "", emotion: str = None, timeout: float = 25.0) -> bool:
        """Envía el archivo de audio (MP3/WAV) en base64 al overlay y espera la señal audio_done."""
        import base64
        import os
        if not os.path.exists(audio_path) or not self.clients:
            return False

        try:
            with open(audio_path, "rb") as f:
                b64_data = base64.b64encode(f.read()).decode("utf-8")
        except Exception as e:
            logger.error(f"Error leyendo archivo de audio para overlay: {e}")
            return False

        self._audio_done_event.clear()
        payload = {
            "type": "audio",
            "format": "mp3",
            "data": b64_data,
            "text": text,
            "emotion": emotion
        }
        self._send_sync(payload)

        # Esperar hasta que el frontend termine de reproducir o timeout
        done = self._audio_done_event.wait(timeout=timeout)
        return done

    def stop_audio(self):
        """Detiene inmediatamente el audio en el overlay."""
        self._send_sync({"type": "audio_stop"})
        self._audio_done_event.set()

    def send_speech(self, text: str, emotion: str = None):
        """Yize está hablando — muestra burbuja + mueve boca."""
        payload = {"type": "speech", "text": text}
        if emotion:
            payload["emotion"] = emotion
        self._send_sync(payload)

    def send_speech_end(self):
        """Terminó de hablar."""
        self._send_sync({"type": "speech_end"})

    def send_listen_start(self):
        """Empezó a escuchar (activa animación de escucha activa)."""
        self._send_sync({"type": "listen_start"})

    def send_listen_stop(self):
        """Terminó de escuchar (detiene animación de escucha activa)."""
        self._send_sync({"type": "listen_stop"})

    def send_emotion(self, emotion: str):
        """Cambiar expresión facial."""
        self._send_sync({"type": "emotion", "emotion": emotion})

    def send_move_window(self, position: str):
        """Mueve la ventana del avatar: 'left', 'right', 'top_left', 'top_right', 'center', 'bottom_right', 'minimize'."""
        self._send_sync({"type": "move_window", "position": position})

    def send_pose(self, pose: str):
        """Activa una pose o animación especial: 'bored', 'celebrate', 'yawn', 'sleepy', 'wave', 'poke'."""
        self._send_sync({"type": "set_pose", "pose": pose})

    def send_dance(self, action: str = "toggle"):
        """Activa o desactiva el baile rítmico sincronizado con la música ('start', 'stop', 'toggle')."""
        self._send_sync({"type": "dance", "action": action})

    def send_screen_target(self, x: int, y: int, label: str = "Elemento", box: list = None):
        """Envía evento para dibujar una diana holográfica en pantalla en la coordenada x, y."""
        self._send_sync({
            "type": "show_screen_target",
            "x": x,
            "y": y,
            "label": label,
            "box": box or []
        })

    def send_idle_thought(self, text: str):
        """Muestra una burbuja de pensamiento espontáneo en el overlay."""
        self._send_sync({"type": "idle_thought", "text": text})

    def send_wave(self):
        """Envía saludo con la mano."""
        self._send_sync({"type": "wave"})
        self.send_pose("wave")

    def send_window_dnd(self, active: bool):
        """Activa o desactiva el modo No Molestar para minimizar o restaurar a Yize."""
        self._send_sync({"type": "window_dnd", "active": active})

    def send_command(self, cmd: str):
        """Envía comando genérico al overlay."""
        self._send_sync({"type": "command", "cmd": cmd})

    def send(self, data: dict):
        """Envía un diccionario JSON arbitrario al overlay."""
        self._send_sync(data)

    def _handle_poke(self):
        """Reacción espontánea hablada de Yize al recibir un clic (poke) en el modelo 3D (con cooldown)."""
        import time
        now = time.time()
        if now - self._last_poke_time < 8.0:
            return
        self._last_poke_time = now

        import random
        frases = [
            "[annoyed] ¡Oye! ¿Quién te dio permiso para tocarme la cabeza, atrevido?",
            "[tsundere] ¡Déjame en paz, menso! Me vas a despeinar toda.",
            "[surprised] ¡Ah! ¡No me toques de la nada que me asustas, tarado!",
            "[smug] ¿Qué pasa KJ? ¿Tanto me extrañabas que tienes que andarme picando?",
            "[happy] Si me vas a tocar, por lo menos que sea para darme una caricia, tonto."
        ]
        frase = random.choice(frases)
        try:
            import sys
            from pathlib import Path
            core_dir = Path(__file__).resolve().parent.parent / "core"
            if str(core_dir) not in sys.path:
                sys.path.insert(0, str(core_dir))
            from voice import speak_async
            speak_async(frase)
        except Exception as e:
            logger.debug(f"Error procesando poke: {e}")

    def _handle_shake(self):
        """Reacción espontánea hablada de Yize al agitar rápidamente el mouse (con cooldown)."""
        import time
        now = time.time()
        if now - self._last_shake_time < 12.0:
            return
        self._last_shake_time = now

        import random
        frases = [
            "[surprised] ¡Oye! ¡Para de sacudir el mouse como un loco que me mareas!",
            "[angry] ¡Cálmate con el ratón, bestia! ¿Te dio un ataque o qué te pasa?",
            "[annoyed] ¿Qué haces agitando el puntero así? Casi me tiras de la pantalla, menso.",
            "[tsundere] ¡Déjame tranquila! Ya vi que estás ahí, no hace falta que provoques un terremoto."
        ]
        frase = random.choice(frases)
        try:
            import sys
            from pathlib import Path
            core_dir = Path(__file__).resolve().parent.parent / "core"
            if str(core_dir) not in sys.path:
                sys.path.insert(0, str(core_dir))
            from voice import speak_async
            speak_async(frase)
        except Exception as e:
            logger.debug(f"Error procesando shake: {e}")

    def _handle_file_drop(self, data: dict):
        """Procesa un archivo soltado sobre el avatar (código, logs o imagen)."""
        try:
            import sys
            import threading
            from pathlib import Path
            core_dir = Path(__file__).resolve().parent.parent / "core"
            if str(core_dir) not in sys.path:
                sys.path.insert(0, str(core_dir))
            from brain import process_file_drop
            from voice import speak_async

            def _worker():
                respuesta = process_file_drop(data)
                if respuesta:
                    speak_async(respuesta)

            threading.Thread(target=_worker, daemon=True).start()
        except Exception as e:
            logger.debug(f"Error procesando file_drop: {e}")

    def on_command(self, callback: Callable):
        """Registrar callback para comandos del overlay."""
        self.command_callback = callback


# ─── API pública simple ───────────────────────────────────────────────────────
def ensure_overlay_running() -> bool:
    """Verifica si el overlay 3D de Electron está corriendo; si no, lo inicia de forma limpia y transparente."""
    import psutil
    import subprocess
    from pathlib import Path

    # 1. Verificar si ya hay una instancia de electron activa
    for proc in psutil.process_iter(['name']):
        try:
            if proc.info['name'] and 'electron' in proc.info['name'].lower():
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    # 2. Iniciar el overlay de Electron directamente sin consolas negras intermedias
    root_dir = Path(__file__).resolve().parent.parent
    overlay_dir = root_dir / "yize_overlay"
    electron_exe = overlay_dir / "node_modules" / "electron" / "dist" / "electron.exe"
    main_cjs = overlay_dir / "electron-main.cjs"

    if electron_exe.exists() and main_cjs.exists():
        subprocess.Popen(
            [str(electron_exe), str(main_cjs)],
            cwd=str(overlay_dir)
        )
        return True
    return False

def start_bridge(auto_launch_overlay: bool = True):
    bridge = OverlayBridge.get()
    bridge.start()
    if auto_launch_overlay:
        try:
            ensure_overlay_running()
        except Exception as e:
            logger.warning(f"No se pudo autoiniciar el overlay: {e}")
    return bridge

def get_bridge() -> OverlayBridge:
    return OverlayBridge.get()

overlay_bridge = OverlayBridge.get()


if __name__ == "__main__":
    import time
    logging.basicConfig(level=logging.DEBUG)
    
    bridge = start_bridge()
    bridge.on_command(lambda cmd: print(f"Comando recibido: {cmd}"))
    
    print("Bridge corriendo. Prueba con: ws://localhost:8765")
    
    # Demo: enviar mensajes de prueba
    time.sleep(3)
    bridge.send_speech("¡Hola! Soy Yize, tu asistente. 💜", "happy")
    time.sleep(4)
    bridge.send_speech_end()
    
    while True:
        time.sleep(1)
