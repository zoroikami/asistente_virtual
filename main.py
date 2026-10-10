import sys
import os
import time
import argparse
from colorama import init, Fore, Style

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from pathlib import Path
_ROOT = Path(__file__).resolve().parent
for _p in [str(_ROOT / "core"), str(_ROOT / "bridges")]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from config import ASSISTANT_NAME, WAKE_WORDS, GEMINI_API_KEY
from voice import speak, VoiceRecognizer
from brain import process_query, extract_emotion

init(autoreset=True)

# Iniciar enlace con VTube Studio en segundo plano si está disponible
try:
    from vts_bridge import get_vts_bridge
    get_vts_bridge().start_background()
except Exception:
    pass

# Iniciar bridge WebSocket con el overlay Tauri
try:
    from overlay_bridge import start_bridge
    _overlay = start_bridge()
except Exception as _e:
    _overlay = None
    print(f"[~] Overlay bridge no disponible: {_e}")


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
            # Eliminar la palabra de activación de la frase
            parts = text_lower.split(wake, 1)
            remaining = parts[1].strip() if len(parts) > 1 else ""
            # Quitar comas o puntos iniciales
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
            if user_input.lower() in ["salir", "exit", "quit", "cerrar"]:
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

    api_status = (
        f"{Fore.GREEN}Conectado con Gemini AI{Style.RESET_ALL}"
        if GEMINI_API_KEY and GEMINI_API_KEY != "tu_api_key_aqui"
        else f"{Fore.YELLOW}Modo Local (Comandos de Sistema){Style.RESET_ALL}"
    )

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

            # Limpiar si el usuario dijo su nombre como saludo, pero procesar la frase completa
            clean_input = detected_text.strip()
            _, stripped_cmd = extract_command_from_wake(clean_input)
            command_to_process = stripped_cmd if stripped_cmd else clean_input

            print(f"\n{Fore.YELLOW}🎙️ Tú dijiste:{Style.RESET_ALL} '{clean_input}'")

            # Comandos de apagado del asistente
            if any(c in clean_input.lower() for c in ["apágate", "cerrar asistente", "detener asistente", "descansar", "apagar asistente"]):
                farewell = "Entendido. Desactivando asistente. Que tengas un buen día."
                speak(farewell)
                if bridge:
                    bridge.send_speech(farewell, "sad")
                print(f"\n{Fore.RED}Asistente apagado.{Style.RESET_ALL}")
                break

            # Procesar consulta de forma inmediata
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


def main():
    parser = argparse.ArgumentParser(description=f"Asistente Virtual {ASSISTANT_NAME}")
    parser.add_argument(
        "--texto",
        action="store_true",
        help="Iniciar en modo texto en consola en lugar de voz por micrófono"
    )
    args = parser.parse_args()

    print(BANNER)

    if args.texto:
        run_text_mode()
    else:
        run_voice_mode()


if __name__ == "__main__":
    main()
