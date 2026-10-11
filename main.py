import sys
import os
import time
import argparse
import atexit
import signal
import subprocess
from pathlib import Path
from colorama import init, Fore, Style

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

_ROOT = Path(__file__).resolve().parent
for _p in [str(_ROOT / "core"), str(_ROOT / "bridges")]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from config import (
    ASSISTANT_NAME, WAKE_WORDS, GEMINI_API_KEY,
    OVERLAY_ENABLED, MOBILE_ENABLED, MOBILE_TUNNEL, INTERACTION_MODE
)
from voice import speak, VoiceRecognizer
from brain import process_query, extract_emotion

init(autoreset=True)

# ─── SUPERVISOR DE PROCESOS (ELECTRON & SERVIDOR MÓVIL) ──────────────────────
_CHILD_PROCESSES = []
_SHUTTING_DOWN = False


def lanzar_proceso(cmd, cwd=None, name="Proceso"):
    """Inicia un subproceso en segundo plano sin ventana emergente y lo registra para apagado seguro."""
    try:
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        proc = subprocess.Popen(
            cmd,
            cwd=str(cwd) if cwd else None,
            creationflags=creationflags
        )
        _CHILD_PROCESSES.append((proc, name))
        return proc
    except Exception as e:
        print(f"  {Fore.YELLOW}[!] No se pudo iniciar {name}: {e}{Style.RESET_ALL}")
        return None


def apagar_todo():
    """Apaga todos los servicios y subprocesos hijos de Yize garantizando que no queden zombies."""
    global _SHUTTING_DOWN
    if _SHUTTING_DOWN:
        return
    _SHUTTING_DOWN = True
    print(f"\n{Fore.CYAN}✦ Apagando servicios y cerrando Yize...{Style.RESET_ALL}")

    for proc, name in reversed(_CHILD_PROCESSES):
        if proc and proc.poll() is None:
            try:
                if os.name == 'nt':
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                        capture_output=True,
                        timeout=4
                    )
                else:
                    proc.terminate()
                    proc.wait(timeout=2)
                print(f"  {Fore.GREEN}✓ {name} detenido.{Style.RESET_ALL}")
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass

    # Limpieza preventiva de procesos Electron residuales en Windows
    if os.name == 'nt':
        try:
            subprocess.run(["taskkill", "/F", "/IM", "electron.exe"], capture_output=True, timeout=3)
        except Exception:
            pass

    # Generar entrada de diario sarcástica de la sesión
    try:
        from diario import get_diario
        entrada = get_diario().generar_entrada()
        if entrada:
            print(f"\n  {Fore.MAGENTA}📖 [El Diario de Yize]: \"{entrada}\"{Style.RESET_ALL}")
    except Exception:
        pass

    try:
        from system_sentinel import get_sentinel
        get_sentinel().stop()
    except Exception:
        pass

    try:
        from core.reminders import reminder_manager
        reminder_manager.stop()
    except Exception:
        pass

    try:
        from core.gestures import gesture_sentinel
        gesture_sentinel.stop()
    except Exception:
        pass

    print(f"\n{Fore.MAGENTA}✦ Yize ha descansado. ¡Hasta pronto! 💜{Style.RESET_ALL}\n")


atexit.register(apagar_todo)


def _sig_handler(sig, frame):
    apagar_todo()
    sys.exit(0)


signal.signal(signal.SIGINT, _sig_handler)
signal.signal(signal.SIGTERM, _sig_handler)

if sys.platform == "win32":
    try:
        import win32api
        def _win_handler(dw_ctrl):
            apagar_todo()
            return True
        win32api.SetConsoleCtrlHandler(_win_handler, True)
    except Exception:
        pass


# ─── ENLACES CON VTS Y OVERLAY ────────────────────────────────────────────────
def init_bridges():
    """Inicia los enlaces con VTube Studio y el servidor WebSocket del overlay 3D."""
    try:
        from vts_bridge import get_vts_bridge
        get_vts_bridge().start_background()
    except Exception:
        pass

    try:
        from overlay_bridge import start_bridge
        start_bridge()
    except Exception as _e:
        print(f"[~] Overlay bridge no disponible: {_e}")

    try:
        from system_sentinel import get_sentinel
        get_sentinel().start()
    except Exception as _e:
        print(f"[~] Centinela no disponible: {_e}")

    try:
        from core.reminders import reminder_manager
        reminder_manager.start()
    except Exception as _e:
        print(f"[~] Recordatorios no disponibles: {_e}")


BANNER = f"""
{Fore.CYAN}╔══════════════════════════════════════════════════════════════════════╗
║        ✦  {ASSISTANT_NAME.upper()} — COMPAÑERA 3D & COPILOTO AUTÓNOMA  ✦              ║
║         Mente Activa, Visión de Sistema & Presencia de Escritorio     ║
╚══════════════════════════════════════════════════════════════════════╝{Style.RESET_ALL}
"""


def extract_command_from_wake(text: str) -> tuple[bool, str]:
    """
    Verifica si el texto contiene alguna palabra de activación.
    Retorna (activado: bool, comando_restante: str).
    """
    text_lower = text.lower().strip()
    for wake in sorted(WAKE_WORDS, key=len, reverse=True):
        if wake in text_lower:
            parts = text_lower.split(wake, 1)
            remaining = parts[1].strip() if len(parts) > 1 else ""
            remaining = remaining.lstrip(",.!? ")
            return True, remaining
    return False, ""


def run_text_mode():
    """Modo interactivo por texto (útil para pruebas o ambientes silenciosos)."""
    from live_companion import get_live_companion
    def on_live(txt, tag):
        print(f"\n{Fore.MAGENTA}🔴 [En Vivo] {ASSISTANT_NAME}: {txt}{Style.RESET_ALL}\n{Fore.YELLOW}Tú: {Style.RESET_ALL}", end="", flush=True)
        speak(txt)
    get_live_companion().add_listener(on_live)

    print(f"""
{Fore.GREEN}[Modo Interactivo Activo]{Style.RESET_ALL} — Habla con Yize directamente o dale órdenes.
{Fore.CYAN}✦ Comandos y acciones rápidas que puedes probar:{Style.RESET_ALL}
  • {Fore.YELLOW}Gestos:{Style.RESET_ALL} "saluda", "haz una pose", "enójate", "piensa", "sonríe"
  • {Fore.YELLOW}Aplicaciones:{Style.RESET_ALL} "abre spotify", "abre discord", "abre chrome", "abre youtube", "abre bloc de notas"
  • {Fore.YELLOW}Juegos:{Style.RESET_ALL} "abre steam", "abre fortnite", "abre lol", "abre valorant"
  • {Fore.YELLOW}Sistema:{Style.RESET_ALL} "qué hora es", "qué día es", "estado del sistema", "captura de pantalla"
  • {Fore.YELLOW}Audio:{Style.RESET_ALL} "sube el volumen", "baja el volumen", "silencia", "siguiente canción"
  • {Fore.YELLOW}Búsquedas:{Style.RESET_ALL} "busca en google [tema]", "busca en youtube [canción o video]"
  • {Fore.YELLOW}Conversación:{Style.RESET_ALL} Charlar libremente con su personalidad (o escribe 'salir' para cerrar).
""")
    while True:
        try:
            user_input = input(f"{Fore.YELLOW}Tú: {Style.RESET_ALL}").strip()
            if not user_input:
                continue
            if user_input.lower() in ["salir", "exit", "quit", "cerrar", "apágate", "descansar"]:
                get_live_companion().stop()
                speak("Hasta luego.")
                break

            response = process_query(user_input)
            emotion, clean_text = extract_emotion(response)
            try:
                from overlay_bridge import get_bridge
                get_bridge().send_emotion(emotion)
            except Exception:
                pass
            speak(clean_text)
        except (KeyboardInterrupt, EOFError):
            get_live_companion().stop()
            print("\nSaliendo...")
            break


def run_voice_mode():
    """Modo principal: escucha en segundo plano por micrófono."""
    from live_companion import get_live_companion
    try:
        from overlay_bridge import get_bridge
        bridge = get_bridge()
    except Exception:
        bridge = None

    def on_live_v(txt, tag):
        print(f"\n{Fore.MAGENTA}🔴 [En Vivo] {ASSISTANT_NAME}: {txt}{Style.RESET_ALL}")
        if bridge:
            bridge.send_idle_thought(txt)
        speak(txt)
    get_live_companion().add_listener(on_live_v)
    print(f"{Fore.MAGENTA}Iniciando sistema de audio y reconocimiento...{Style.RESET_ALL}")
    recognizer = VoiceRecognizer()
    if not recognizer.has_microphone:
        print(f"\n{Fore.YELLOW}[!] No se detectó un micrófono disponible en el sistema.")
        print(f"    Cambiando automáticamente al modo de texto interactivo...{Style.RESET_ALL}\n")
        speak("No se detectó un micrófono disponible. Iniciando modo texto.")
        run_text_mode()
        return

    print(f"\n{Fore.GREEN}💬 Modo Voz Directo Activo:{Style.RESET_ALL} Yize responderá a todo lo que hables por micrófono.")
    print(f"{Fore.LIGHTBLACK_EX}Presiona Ctrl+C en cualquier momento para detener.{Style.RESET_ALL}\n")

    speak(f"{ASSISTANT_NAME} conectada y escuchándote en directo.")

    while True:
        try:
            print(f"\r{Fore.BLUE}🎧 [Escuchando micrófono...]{Style.RESET_ALL}", end="", flush=True)
            if bridge:
                bridge.send_listen_start()
            detected_text = recognizer.listen(timeout=None, phrase_time_limit=8)

            if not detected_text or not detected_text.strip():
                continue

            clean_input = detected_text.strip()
            _, stripped_cmd = extract_command_from_wake(clean_input)
            command_to_process = stripped_cmd if stripped_cmd else clean_input

            print(f"\n{Fore.YELLOW}🎙️ Tú dijiste:{Style.RESET_ALL} '{clean_input}'")

            if any(c in clean_input.lower() for c in ["apágate", "cerrar asistente", "detener asistente", "descansar", "apagar asistente"]):
                farewell = "Entendido. Desactivando asistente. Que tengas un buen día."
                speak(farewell)
                if bridge:
                    bridge.send_speech(farewell, "sad")
                print(f"\n{Fore.RED}Asistente apagado.{Style.RESET_ALL}")
                break

            response = process_query(command_to_process)
            emotion, clean_text = extract_emotion(response)
            if bridge:
                bridge.send_emotion(emotion)
                bridge.send_speech(clean_text, emotion)
            speak(clean_text)
            if bridge:
                bridge.send_speech_end()

        except KeyboardInterrupt:
            print(f"\n{Fore.RED}Detención manual solicitada por el usuario.{Style.RESET_ALL}")
            speak("Hasta luego.")
            if bridge:
                bridge.send_speech("Hasta luego... 💜", "sad")
            break
        except Exception as e:
            print(f"\n{Fore.RED}[!] Error inesperado en el bucle: {e}{Style.RESET_ALL}")
            time.sleep(1)


def start_services(args):
    """Inicia el Overlay 3D y el Servidor Móvil según la configuración de .env y CLI."""
    # 1. Overlay 3D de Electron
    if OVERLAY_ENABLED and not args.sin_overlay:
        electron_dir = _ROOT / "yize_overlay"
        electron_exe = electron_dir / "node_modules" / "electron" / "dist" / "electron.exe"
        main_cjs = electron_dir / "electron-main.cjs"
        if electron_exe.exists() and main_cjs.exists():
            import psutil
            is_running = False
            for p in psutil.process_iter(['name']):
                try:
                    pname = p.info.get('name') or ""
                    if "electron" in pname.lower():
                        is_running = True
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            if not is_running:
                print(f"  {Fore.CYAN}[*] Iniciando Yize 3D Overlay sobre tu escritorio...{Style.RESET_ALL}")
                lanzar_proceso([str(electron_exe), str(main_cjs)], cwd=electron_dir, name="Overlay 3D (Electron)")
                time.sleep(1.2)
            else:
                print(f"  {Fore.GREEN}[✓] Yize 3D Overlay ya está activo en tu escritorio.{Style.RESET_ALL}")
        else:
            print(f"  {Fore.YELLOW}[~] Overlay no encontrado en yize_overlay.{Style.RESET_ALL}")

    # 2. Servidor Móvil
    want_mobile = args.con_movil or (MOBILE_ENABLED and not args.sin_movil)
    if want_mobile:
        mobile_py = _ROOT / "mobile_server.py"
        if mobile_py.exists():
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            port_busy = sock.connect_ex(('127.0.0.1', 8080)) == 0
            sock.close()
            if not port_busy:
                cmd = [sys.executable, str(mobile_py)]
                if args.tunnel or MOBILE_TUNNEL:
                    cmd.append("--tunnel")
                print(f"  {Fore.CYAN}[*] Iniciando Servidor Móvil (http://localhost:8080)...{Style.RESET_ALL}")
                lanzar_proceso(cmd, cwd=_ROOT, name="Servidor Móvil (PWA)")
                time.sleep(1.0)
            else:
                print(f"  {Fore.GREEN}[✓] Servidor Móvil ya está activo en puerto 8080.{Style.RESET_ALL}")


def main():
    parser = argparse.ArgumentParser(description=f"Asistente Virtual {ASSISTANT_NAME}")
    parser.add_argument("--texto", action="store_true", help="Iniciar en modo texto en consola")
    parser.add_argument("--voz", action="store_true", help="Iniciar en modo voz por micrófono")
    parser.add_argument("--sin-overlay", action="store_true", help="No iniciar la ventana 3D de Electron")
    parser.add_argument("--con-movil", action="store_true", help="Forzar inicio del servidor móvil")
    parser.add_argument("--sin-movil", action="store_true", help="Desactivar servidor móvil")
    parser.add_argument("--tunnel", action="store_true", help="Activar túnel HTTPS Cloudflare para el móvil")
    args = parser.parse_args()

    print(BANNER)

    try:
        from diario import get_diario
        ultima = get_diario().leer_ultima_entrada()
        if ultima:
            lineas = [l.strip().replace('"', '').replace('>', '').strip() for l in ultima.splitlines() if l.strip()]
            if lineas:
                print(f"  {Fore.MAGENTA}✦ En el diario de Yize:{Style.RESET_ALL}")
                print(f"  {Fore.LIGHTMAGENTA_EX}\"{lineas[-1]}\"{Style.RESET_ALL}\n")
    except Exception:
        pass

    init_bridges()
    start_services(args)

    modo_texto = args.texto or (not args.voz and INTERACTION_MODE.lower() in ["texto", "text", "console"])

    try:
        if modo_texto:
            run_text_mode()
        else:
            run_voice_mode()
    finally:
        apagar_todo()


if __name__ == "__main__":
    main()
