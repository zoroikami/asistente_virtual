"""
system_sentinel.py — Centinela del Sistema y Ciberseguridad para Yize.
Monitorea en segundo plano:
1. Nivel de batería baja y conexión de cargador (Laptops/Portátiles).
2. Detección de nuevas unidades o memorias USB conectadas.
3. Centinela de puertos de red: alerta sobre nuevos puertos abiertos en escucha (LISTEN).
4. Fatiga y tiempo de sesión prolongado (> 5 horas de uso continuo).
"""

import sys
import time
import threading
import psutil
from typing import Set

class SystemSentinel:
    def __init__(self):
        self._thread = None
        self._running = False
        self.interval = 15.0  # segundos entre revisiones

        # Estado previo
        self._last_battery_plugged = None
        self._last_battery_low_alert = 0.0
        self._known_drives: Set[str] = set()
        self._known_ports: Set[int] = set()
        self._start_time = time.time()
        self._fatigue_alert_sent = False
        self._dnd_active = False

        self._init_baselines()

    def _init_baselines(self):
        """Inicializa las líneas base de unidades de disco y puertos abiertos."""
        try:
            self._known_drives = {p.device for p in psutil.disk_partitions()}
        except Exception:
            self._known_drives = set()

        try:
            battery = psutil.sensors_battery()
            if battery:
                self._last_battery_plugged = battery.power_plugged
        except Exception:
            pass

        try:
            self._known_ports = {
                c.laddr.port for c in psutil.net_connections(kind='inet')
                if c.status == 'LISTEN' and c.laddr and c.laddr.ip not in ("127.0.0.1", "::1", "localhost") and c.laddr.port <= 10000
            }
        except Exception:
            self._known_ports = set()

    def _notify(self, message: str):
        """Emite la alerta hablada y actualiza el overlay y la UI."""
        print(f"🛡️ [Centinela] {message}")
        try:
            from voice import speak_async
            speak_async(message)
        except Exception:
            pass

    def _check_battery(self):
        try:
            battery = psutil.sensors_battery()
            if not battery:
                return

            now = time.time()
            plugged = battery.power_plugged
            percent = int(battery.percent)

            # Notificar si se enchufa después de estar desconectado
            if self._last_battery_plugged is False and plugged is True:
                self._notify("[happy] ¡Ahhh, energía fresca! Ya me estaba sintiendo débil, gracias por conectarme.")
            self._last_battery_plugged = plugged

            # Alerta de batería baja (< 20% y sin cargador)
            if not plugged and percent <= 20:
                if now - self._last_battery_low_alert > 900:  # cada 15 min máximo
                    self._last_battery_low_alert = now
                    self._notify(f"[annoyed] ¡Oye KJ! La batería está al {percent}%. ¡Enchúfame antes de que se me apague la mente, menso!")
        except Exception:
            pass

    def _check_usb_and_drives(self):
        try:
            current_drives = {p.device for p in psutil.disk_partitions()}
            new_drives = current_drives - self._known_drives
            if new_drives:
                for drive in new_drives:
                    self._notify(f"[surprised] ¡Atención! Detecté un nuevo dispositivo o unidad USB conectada ({drive}). Ojo con lo que metes ahí.")
            self._known_drives = current_drives
        except Exception:
            pass

    def _check_network_ports(self):
        """Centinela de ciberseguridad: detecta nuevos puertos externos en estado LISTEN."""
        try:
            current_external_ports = set()
            for c in psutil.net_connections(kind='inet'):
                if c.status == 'LISTEN' and c.laddr:
                    ip = c.laddr.ip
                    port = c.laddr.port
                    # Ignorar loopback local puro (127.0.0.1, ::1)
                    if ip in ("127.0.0.1", "::1", "localhost"):
                        continue
                    # Ignorar puertos efímeros altos de Windows/Electron/Chrome/Spotify (> 10000)
                    if port > 10000:
                        continue
                    current_external_ports.add(port)

            new_ports = current_external_ports - self._known_ports
            # Filtrar puertos de desarrollo conocidos de Yize
            ignored = {8765, 8080, 5173, 3000, 5000}
            new_significant = [p for p in new_ports if p not in ignored]

            if new_significant:
                port_str = ", ".join(str(p) for p in new_significant[:3])
                self._notify(f"[thinking] Ojo KJ: detecté que se acaba de abrir el puerto {port_str} escuchando conexiones en la red. ¿Estás levantando algún servidor o servicio?")
            self._known_ports.update(current_external_ports)
        except Exception:
            pass

    def _check_fatigue(self):
        hours = (time.time() - self._start_time) / 3600.0
        if hours >= 5.0 and not self._fatigue_alert_sent:
            self._fatigue_alert_sent = True
            self._notify("[annoyed] Llevas más de 5 horas seguidas pegado a la pantalla, flojo. Levántate a estirar las piernas y tomar un vaso de agua.")

    def _check_fullscreen_dnd(self):
        """Detecta si hay una aplicación o juego a pantalla completa para activar 'No Molestar'."""
        if sys.platform != "win32":
            return
        try:
            import ctypes
            from ctypes import wintypes
            user32 = ctypes.windll.user32
            hwnd = user32.GetForegroundWindow()
            if not hwnd:
                return

            desktop = user32.GetDesktopWindow()
            shell = user32.GetShellWindow()
            if hwnd in (desktop, shell):
                if self._dnd_active:
                    self._dnd_active = False
                    self._on_dnd_change(False)
                return

            rect = wintypes.RECT()
            if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                return

            sw = user32.GetSystemMetrics(0)
            sh = user32.GetSystemMetrics(1)

            is_fullscreen = (rect.left <= 0 and rect.top <= 0 and rect.right >= sw and rect.bottom >= sh)
            if is_fullscreen and not self._dnd_active:
                self._dnd_active = True
                self._on_dnd_change(True)
            elif not is_fullscreen and self._dnd_active:
                self._dnd_active = False
                self._on_dnd_change(False)
        except Exception:
            pass

    def _on_dnd_change(self, active: bool):
        try:
            from bridges.overlay_bridge import get_bridge
            get_bridge().send_window_dnd(active)
            if active:
                print("🌙 [Centinela] Modo 'No Molestar' automático: pantalla completa detectada.")
            else:
                print("☀️ [Centinela] Fin de pantalla completa: restableciendo Yize.")
        except Exception:
            pass

    def _run_loop(self):
        time.sleep(5.0)  # Espera inicial para estabilizar inicio
        while self._running:
            self._check_fullscreen_dnd()
            self._check_battery()
            self._check_usb_and_drives()
            self._check_network_ports()
            self._check_fatigue()
            time.sleep(self.interval)

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="SystemSentinel")
        self._thread.start()
        print("🛡️ [Centinela] Vigilante de sistema y seguridad iniciado.")

    def stop(self):
        self._running = False


_instance = None

def get_sentinel() -> SystemSentinel:
    global _instance
    if _instance is None:
        _instance = SystemSentinel()
    return _instance
