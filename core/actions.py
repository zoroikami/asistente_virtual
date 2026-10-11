import os
import re
import subprocess
import webbrowser
import datetime
import ctypes
from pathlib import Path
import psutil
import pyautogui
import requests
from config import CAPTURES_DIR, NOTES_FILE


def lanzar_juego_o_acceso_directo(cmd: str) -> tuple[bool, str]:
    """
    Busca y lanza juegos y aplicaciones de Windows usando accesos directos (.lnk, .url),
    protocolos URI y ejecutables directos de Riot, Epic Games, Steam, etc.
    """
    cmd_low = cmd.lower().strip()

    # Mapeo de juegos conocidos con sus rutas prioritarias en este equipo
    rutas_conocidas = {
        "league of legends": [
            r"C:\Users\Public\Desktop\League of Legends.lnk",
            r"C:\Riot Games\League of Legends\LeagueClient.exe",
        ],
        "lol": [
            r"C:\Users\Public\Desktop\League of Legends.lnk",
            r"C:\Riot Games\League of Legends\LeagueClient.exe",
        ],
        "fortnite": [
            r"C:\Users\kj\Desktop\Fortnite.url",
            "com.epicgames.launcher://apps/fn%3A4fe75bbc5a674f4f9b356b5c90567da5%3AFortnite?action=launch&silent=true",
            r"C:\Users\Public\Desktop\Epic Games Launcher.lnk",
        ],
        "fornite": [
            r"C:\Users\kj\Desktop\Fortnite.url",
            "com.epicgames.launcher://apps/fn%3A4fe75bbc5a674f4f9b356b5c90567da5%3AFortnite?action=launch&silent=true",
        ],
        "epic games": [
            r"C:\Users\Public\Desktop\Epic Games Launcher.lnk",
            r"C:\Program Files (x86)\Epic Games\Launcher\Portal\Binaries\Win64\EpicGamesLauncher.exe",
        ],
        "riot client": [
            r"C:\Users\Public\Desktop\Cliente de Riot.lnk",
            r"C:\Riot Games\Riot Client\RiotClientServices.exe",
        ],
        "riot": [
            r"C:\Users\Public\Desktop\Cliente de Riot.lnk",
            r"C:\Riot Games\Riot Client\RiotClientServices.exe",
        ],
        "valorant": [
            r"C:\Users\Public\Desktop\VALORANT.lnk",
        ],
        "steam": [
            "steam://open/main",
            r"C:\Program Files (x86)\Steam\steam.exe",
        ],
        "sprout": [
            r"C:\Users\kj\AppData\Local\Sprout\terrace-desktop.exe",
        ],
        "vtube studio": [
            r"C:\Program Files (x86)\Steam\steamapps\common\VTube Studio\VTube Studio.exe",
        ]
    }

    # Descartar si el usuario está haciendo una pregunta o debatiendo
    pregunta_triggers = ["¿", "que opinas", "qué opinas", "vale la pena", "crees que", "por qué", "porque", "como ", "cómo ", "explica", "cuanto", "cuánto", "opinión", "opinion"]
    if any(q in cmd_low for q in pregunta_triggers):
        return False, ""

    # Verificar si hay intención explícita de abrir/iniciar o si solo se nombró el juego
    intencion_abrir = any(p in cmd_low for p in ["abre", "abrir", "inicia", "iniciar", "jugar", "ejecuta", "lanzar", "vamos a"])
    es_nombre_directo = cmd_low in ["fortnite", "fornite", "lol", "league of legends", "epic games", "riot client", "valorant", "steam"]

    if not (intencion_abrir or es_nombre_directo):
        return False, ""

    # 1. Comprobar juegos de la lista conocida si se menciona el nombre
    for clave, opciones in rutas_conocidas.items():
        if clave in cmd_low:
            for ruta in opciones:
                if ruta.startswith("com.") or ruta.startswith("steam://"):
                    try:
                        os.startfile(ruta)
                        return True, f"[excited] ¡Iniciando {clave.title()}! A ver si no manqueas como siempre, ¿eh?"
                    except Exception:
                        pass
                elif os.path.exists(ruta):
                    try:
                        os.startfile(ruta)
                        return True, f"[excited] Abriendo {clave.title()}. ¡A jugar se ha dicho!"
                    except Exception:
                        pass

    # 2. Búsqueda automática en escritorios y menú de inicio si la orden pide abrir
    palabras_orden = ["abre ", "abrir ", "inicia ", "iniciar ", "jugar ", "ejecuta ", "lanzar "]
    if any(p in cmd_low for p in palabras_orden):
        target = cmd_low
        for p in palabras_orden:
            target = target.replace(p, "")
        target = target.replace("el juego", "").replace("el", "").replace("la", "").strip()

        if target and len(target) >= 3:
            carpetas_busqueda = [
                Path(os.environ.get("USERPROFILE", "")) / "Desktop",
                Path("C:/Users/Public/Desktop"),
                Path(os.environ.get("APPDATA", "")) / "Microsoft/Windows/Start Menu/Programs",
                Path(os.environ.get("PROGRAMDATA", "")) / "Microsoft/Windows/Start Menu/Programs",
            ]
            for carpeta in carpetas_busqueda:
                if carpeta.exists():
                    for root, _, files in os.walk(carpeta):
                        for f in files:
                            if f.lower().endswith((".lnk", ".url", ".exe")):
                                if target in f.lower():
                                    full_path = os.path.join(root, f)
                                    try:
                                        os.startfile(full_path)
                                        nombre_juego = Path(f).stem
                                        return True, f"[excited] Abriendo {nombre_juego}."
                                    except Exception:
                                        pass

    return False, ""


def lanzar_spotify() -> bool:
    """Abre Spotify en Windows buscando el ejecutable real o usando el protocolo URI."""
    appdata = os.environ.get("APPDATA", "")
    spotify_exe = Path(appdata) / "Spotify" / "Spotify.exe"
    if spotify_exe.exists():
        try:
            subprocess.Popen([str(spotify_exe)])
            return True
        except Exception:
            pass
    try:
        os.system('start "" "spotify:"')
        return True
    except Exception:
        pass
    try:
        webbrowser.open("https://open.spotify.com")
        return True
    except Exception:
        return False


def execute_system_command(command: str) -> tuple[bool, str]:
    """
    Intenta ejecutar comandos nativos del sistema en base a palabras clave.
    Retorna una tupla (ejecutado: bool, respuesta_verbal: str).
    """
    cmd = command.lower().strip()

    try:
        from diario import get_diario
        get_diario().registrar_evento("orden_usuario", command)
    except Exception:
        pass

    # Si es una orden de creación o programación compleja, dejar que Gemini con herramientas lo resuelva
    if any(cmd.startswith(v) for v in ["crea un archivo", "crear archivo", "escribe un archivo", "escribe código", "haz un script", "genera un archivo"]):
        return False, ""

    # --- 1. HORA Y FECHA ---
    if any(p == cmd or cmd.startswith(p) for p in ["qué hora es", "la hora", "dime la hora", "que hora es"]):
        now = datetime.datetime.now()
        minutos = f"{now.minute}" if now.minute > 9 else f"0{now.minute}"
        return True, f"[happy] Son las {now.hour} horas y {minutos} minutos, menso. ¿Tienes prisa o qué?"

    if any(p in cmd for p in ["qué día es", "qué fecha es", "fecha de hoy", "dia de hoy"]):
        dias = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
        meses = [
            "enero", "febrero", "marzo", "abril", "mayo", "junio",
            "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
        ]
        now = datetime.datetime.now()
        dia_sem = dias[now.weekday()]
        mes = meses[now.month - 1]
        return True, f"[happy] Hoy es {dia_sem} {now.day} de {mes} de {now.year}. De nada por recordártelo."

    # --- 2. ESTADO DEL SISTEMA (CPU, RAM, BATERÍA) ---
    sys_triggers = [
        "estado del sistema", "cómo está el sistema", "recursos del sistema",
        "rendimiento del sistema", "estado de la batería", "cuánta batería",
        "nivel de batería", "memoria ram", "uso de ram", "uso de memoria",
        "uso de cpu", "uso de procesador", "temperatura de cpu"
    ]
    if any(p in cmd for p in sys_triggers) or cmd in ["batería", "rendimiento", "recursos", "ram", "procesador"]:
        cpu = psutil.cpu_percent(interval=0.5)
        ram = psutil.virtual_memory()
        ram_gb_usada = round(ram.used / (1024**3), 1)
        ram_gb_total = round(ram.total / (1024**3), 1)

        mensaje = f"[thinking] El procesador está al {cpu}% de uso y la RAM al {ram.percent}%, ocupando {ram_gb_usada} de {ram_gb_total} gigas. Tu máquina aguanta, no te quejes tanto."

        battery = psutil.sensors_battery()
        if battery:
            estado_bat = "conectada a la corriente" if battery.power_plugged else "usando la batería"
            mensaje += f" La batería está al {battery.percent}%, {estado_bat}."
        return True, mensaje

    # --- 3. CAPTURA DE PANTALLA ---
    if any(p in cmd for p in ["captura de pantalla", "screenshot", "saca una captura", "toma una captura"]):
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = CAPTURES_DIR / f"captura_{timestamp}.png"
        screenshot = pyautogui.screenshot()
        screenshot.save(filename)
        os.startfile(str(filename))
        return True, "[happy] ¡Captura de pantalla lista y guardada! Sonríe para la próxima, menso."

    # --- 4. CONTROL DE VOLUMEN Y MULTIMEDIA ---
    if any(p in cmd for p in ["sube el volumen", "subir volumen", "más volumen"]):
        for _ in range(5):
            pyautogui.press("volumeup")
        return True, "[smug] Subiendo volumen. Cuidado no te vayas a quedar sordo, ¿eh?"

    if any(p in cmd for p in ["baja el volumen", "bajar volumen", "menos volumen"]):
        for _ in range(5):
            pyautogui.press("volumedown")
        return True, "[relaxed] Bajando volumen. Mucho mejor para mis oídos."

    if any(p in cmd for p in ["silencia el volumen", "mutear", "silencio", "mute"]):
        pyautogui.press("volumemute")
        return True, "[annoyed] Audio silenciado. Al fin un momento de paz."

    if any(p in cmd for p in ["pausa la música", "pausar", "reanudar", "play", "reproduce"]):
        pyautogui.press("playpause")
        return True, "[happy] Reproducción alternada."

    if any(p in cmd for p in ["siguiente canción", "siguiente pista", "siguiente tema"]):
        pyautogui.press("nexttrack")
        return True, "[smug] Pasando a la siguiente canción. Esa ya me tenía aburrida."

    if any(p in cmd for p in ["canción anterior", "pista anterior"]):
        pyautogui.press("prevtrack")
        return True, "[smug] Volviendo a la canción anterior."

    # --- 4.1 BAILE Y RITMO MUSICAL ---
    if any(p in cmd for p in ["baila", "ponte a bailar", "a bailar", "baila conmigo", "sigue el ritmo", "baila con la música", "baila con el tema"]):
        try:
            from overlay_bridge import get_bridge
            get_bridge().send_dance("start")
        except Exception:
            pass
        return True, "[happy] ¡Siii! Escuchando la música y siguiendo el tempo~ 🎶 ¡A bailar!"

    if any(p in cmd for p in ["deja de bailar", "para de bailar", "no bailes", "detén el baile", "para el baile", "deja el baile"]):
        try:
            from overlay_bridge import get_bridge
            get_bridge().send_dance("stop")
        except Exception:
            pass
        return True, "[relaxed] Vale, me calmo y me quedo quieta."

    # --- 4.2 MÚSICA Y CONTROL DE SPOTIFY ---
    spotify_triggers = [
        "pon algo para estudiar", "pon lofi", "pon lo-fi", "pon synthwave", "pon música de",
        "pon musica de", "pon canciones de", "reproduce en spotify", "pon en spotify",
        "pone en spotify", "pon música", "pon musica", "pone música", "pone musica",
        "reproduce algo de", "pon una canción", "pon una cancion", "pone una canción",
        "pone una cancion", "reproduce una canción", "reproduce una cancion",
        "canción en spotify", "cancion en spotify", "música en spotify", "musica en spotify",
        "pon canciones", "pone canciones", "ponme una canción", "ponme una cancion",
        "pon temas de", "pone temas de", "reproduce a", "pon a"
    ]
    es_intencion_musica = any(t in cmd for t in spotify_triggers) or (
        "spotify" in cmd and any(w in cmd for w in ["pon", "pone", "cancion", "canción", "musica", "música", "reproduce", "tema", "temas"])
    ) or (
        cmd.startswith("pon ") and any(k in cmd for k in ["rock", "chill", "anime", "gaming", "estudio", "concentracion"])
    )

    if es_intencion_musica:
        try:
            from core.spotify_client import spotify_ctl
            res = spotify_ctl.play_preset_or_query(cmd)
            # También activar baile si es música
            try:
                from overlay_bridge import get_bridge
                get_bridge().send_dance("start")
            except Exception:
                pass
            return True, f"[happy] {res}"
        except Exception as e:
            return True, f"[thinking] Intenté abrir la música pero ocurrió: {e}"

    # --- 4.3 GUÍA VISUAL SOBRE LA PANTALLA (PUNTERO HOLOGRÁFICO) ---
    try:
        from vision import is_vision_guide_request, locate_element_on_screen
        if is_vision_guide_request(cmd):
            encontrado, msg = locate_element_on_screen(cmd)
            return True, f"[{'happy' if encontrado else 'thinking'}] {msg}"
    except Exception as e:
        pass

    # --- 4.4 GESTOS FRENTE A LA WEBCAM (LOCAL) Y PIEDRA PAPEL O TIJERA ---
    if any(p in cmd for p in ["activa la cámara", "enciende la cámara", "prende la cámara", "activa la webcam", "activa los gestos", "activa gestos"]):
        try:
            from core.gestures import gesture_sentinel
            ok, msg = gesture_sentinel.start()
            return True, f"[{'happy' if ok else 'annoyed'}] {msg}"
        except Exception as e:
            return True, f"[angry] Error con la cámara: {e}"

    if any(p in cmd for p in ["apaga la cámara", "desactiva la cámara", "apaga la webcam", "desactiva los gestos", "apaga gestos", "apaga los sensores"]):
        try:
            from core.gestures import gesture_sentinel
            ok, msg = gesture_sentinel.stop()
            return True, f"[relaxed] {msg}"
        except Exception as e:
            return True, f"[thinking] Error al apagar cámara: {e}"

    if any(p in cmd for p in ["piedra papel o tijera", "piedra papel tijera", "juguemos piedra papel", "jugar piedra papel"]):
        try:
            from core.gestures import gesture_sentinel
            msg = gesture_sentinel.start_rps_game()
            return True, f"[smug] {msg}"
        except Exception as e:
            return True, f"[annoyed] Error iniciando juego: {e}"

    # --- 4.5 RECORDATORIOS CON ESCALADA DE SARCASMO Y HÁBITOS ---
    try:
        from core.reminders import reminder_manager

        # Hábitos saludables
        if any(p in cmd for p in ["recuérdame tomar agua", "recordatorio de agua", "avísame de tomar agua", "tomar agua cada"]):
            res = reminder_manager.add_habit("agua", 45)
            return True, f"[happy] {res}"

        if any(p in cmd for p in ["recuérdame la postura", "revisa mi postura", "recordatorio de postura", "postura cada"]):
            res = reminder_manager.add_habit("postura", 30)
            return True, f"[happy] {res}"

        if any(p in cmd for p in ["pausa para los ojos", "descanso de ojos", "recordatorio de ojos", "pausa de ojos"]):
            res = reminder_manager.add_habit("ojos", 20)
            return True, f"[happy] {res}"

        # Cumplimiento / Confirmación
        if any(p in cmd for p in ["ya lo hice", "ya lo cumplí", "ya lo termine", "ya terminé", "recordatorio listo", "listo el recordatorio", "ya tomé agua", "ya me senté bien"]):
            res = reminder_manager.acknowledge()
            return True, f"[happy] {res}"

        # Cancelar recordatorios
        if any(p in cmd for p in ["cancela los recordatorios", "cancelar recordatorios", "borra los recordatorios", "eliminar recordatorios"]):
            res = reminder_manager.cancel_all()
            return True, f"[relaxed] {res}"

        # Listar recordatorios
        if any(p in cmd for p in ["qué recordatorios tengo", "que recordatorios tengo", "cuáles son mis recordatorios", "mis recordatorios"]):
            res = reminder_manager.list_active()
            return True, f"[thinking] {res}"

        # Recordatorio puntual con tiempo
        m_rem = re.search(r'(?:recu[eé]rdame|av[ií]same)\s+en\s+(\d+(?:\.\d+)?)\s*(minutos?|mins?|segundos?|segs?|horas?|hs?)?(?:\s+(?:que|para|de)?\s*(.*))?', cmd, re.IGNORECASE)
        if m_rem:
            num = float(m_rem.group(1))
            unit = (m_rem.group(2) or "minutos").lower()
            task = (m_rem.group(3) or "hacer lo que tenías pendiente").strip()
            if "hora" in unit or "h" in unit:
                sec = num * 3600
            elif "seg" in unit:
                sec = num
            else:
                sec = num * 60
            res = reminder_manager.add_reminder(task, sec)
            return True, f"[happy] {res}"
    except Exception as e:
        pass

    # --- 4.6 CHISTES INTERNOS Y ANÉCDOTAS RECURRENTES ---
    try:
        from core.inside_jokes import jokes_manager

        if any(p in cmd for p in ["guarda ese chiste", "guarda este chiste", "anota este chiste", "recuerda este chiste"]):
            chiste_txt = cmd
            for pre in ["guarda ese chiste:", "guarda este chiste:", "anota este chiste:", "guarda ese chiste", "guarda este chiste", "anota este chiste"]:
                if chiste_txt.startswith(pre):
                    chiste_txt = chiste_txt[len(pre):].strip()
                    break
            chiste_txt = chiste_txt or "Un momento gracioso no detallado."
            res = jokes_manager.add_joke(chiste_txt)
            return True, f"[smug] {res}"

        if any(p in cmd for p in ["cuéntame un chiste interno", "cuentame un chiste interno", "dime un chiste interno", "dime una anécdota", "recuerdas cuando"]):
            j = jokes_manager.get_random_joke()
            if j:
                return True, f"[smug] ¿Cómo olvidar esto? {j}"
            return True, "[thinking] Todavía no tenemos suficientes chistes internos registrados. Dame más material cómico."
    except Exception as e:
        pass

    # --- 4.7 BUENOS DÍAS PERSONALIZADO (CLIMA DE SANTIAGO Y DIARIO) ---
    if any(p in cmd for p in ["buenos días", "buenos dias", "dime el briefing", "resumen de la mañana", "cómo empieza el día", "briefing matutino"]):
        try:
            from core.briefing import get_morning_briefing
            res = get_morning_briefing()
            return True, res
        except Exception as e:
            return True, f"[thinking] Error en briefing: {e}"

    # --- 4.8 JUEGOS Y NIVEL DE AFINIDAD ---
    try:
        from core.games import games_ctl
        from core.affinity import affinity_manager

        # Si hay una partida activa de trivia o tres en raya
        if games_ctl.active_game == "trivia":
            res_trivia = games_ctl.handle_trivia_answer(cmd)
            if res_trivia:
                return True, res_trivia

        if games_ctl.active_game == "tateti":
            res_tateti = games_ctl.handle_tateti_move(cmd)
            if res_tateti:
                return True, res_tateti

        if any(p in cmd for p in ["juguemos trivia", "trivia", "jugar trivia", "pregunta de trivia"]):
            return True, games_ctl.start_trivia()

        if any(p in cmd for p in ["juguemos tres en raya", "tres en raya", "tateti", "jugar tateti", "ta te ti"]):
            return True, games_ctl.start_tateti()

        if any(p in cmd for p in ["nivel de afinidad", "cuánta afinidad", "cuanta afinidad", "cómo está nuestra relación", "cuánto me quieres", "estado de afinidad"]):
            return True, affinity_manager.get_status_report()
    except Exception as e:
        pass

    # --- 4.9 SISTEMA DE PLUGINS DINÁMICOS ---
    try:
        from core.plugin_manager import plugin_manager
        if any(p in cmd for p in ["lista los plugins", "qué plugins tienes", "plugins activos"]):
            return True, f"[happy] {plugin_manager.list_plugins()}"

        plugin_handled, plugin_res = plugin_manager.dispatch(cmd)
        if plugin_handled:
            return True, plugin_res
    except Exception as e:
        pass

    # --- 5. CONTROL DE VENTANAS Y PANTALLA ---
    if any(p in cmd for p in ["bloquea la pantalla", "bloquear pantalla", "bloquear pc"]):
        ctypes.windll.user32.LockWorkStation()
        return True, "[annoyed] Bloqueando la computadora. ¡A ver si te paras de la silla un rato, flojo!"

    if any(p in cmd for p in ["minimiza todo", "mostrar escritorio", "minimizar todo", "muestra el escritorio"]):
        pyautogui.hotkey("win", "d")
        return True, "[smug] Mostrando el escritorio. Todo despejado."

    # --- 5.1 APAGADO Y REINICIO DEL SISTEMA ---
    if any(p in cmd for p in ["apaga el computador", "apagar la pc", "apagar el computador", "apaga la computadora", "apaga el equipo", "apagar equipo", "apagar sistema", "apaga la pc"]):
        try:
            subprocess.run(["shutdown", "/s", "/t", "60"], capture_output=True)
            return True, "[annoyed] Programando apagado del equipo en sesenta segundos. Si te arrepientes, di 'cancela el apagado', menso."
        except Exception as e:
            return True, f"[angry] Error intentando programar el apagado: {e}"

    if any(p in cmd for p in ["cancela el apagado", "cancelar apagado", "no apagues la pc", "anular apagado"]):
        try:
            subprocess.run(["shutdown", "/a"], capture_output=True)
            return True, "[happy] Apagado cancelado. Menos mal, ya me estaba asustando."
        except Exception as e:
            return True, f"[angry] Error al cancelar el apagado: {e}"

    if any(p in cmd for p in ["reinicia la pc", "reiniciar el computador", "reinicia la computadora", "reiniciar equipo"]):
        try:
            subprocess.run(["shutdown", "/r", "/t", "60"], capture_output=True)
            return True, "[thinking] Programando reinicio del equipo en sesenta segundos."
        except Exception as e:
            return True, f"[angry] Error intentando programar el reinicio: {e}"

    # --- 6. ABRIR JUEGOS Y ACCESOS DIRECTOS (FORTNITE, LOL, EPIC, RIOT, ETC.) ---
    abierto_juego, msg_juego = lanzar_juego_o_acceso_directo(cmd)
    if abierto_juego:
        return True, msg_juego

    # Control explícito de abrir Spotify con ruta real
    if any(cmd == t or cmd.startswith(t) for t in ["abre spotify", "abrir spotify", "inicia spotify", "iniciar spotify", "lanzar spotify"]) or cmd == "spotify":
        ok = lanzar_spotify()
        if ok:
            return True, "[smug] Abriendo Spotify. A ver si pones música decente, menso."
        else:
            return True, "[angry] No pude encontrar Spotify instalado en tu equipo."

    # --- 6.1 ABRIR APLICACIONES POPULARES ---
    app_commands = {
        ("abrir calculadora", "abre la calculadora", "calculadora"): ("calc", "[thinking] Abriendo la calculadora. ¿Tan malo eres con las cuentas?"),
        ("abrir bloc de notas", "abre el bloc de notas", "bloc de notas", "notepad"): ("notepad", "[smug] Abriendo el Bloc de Notas. A ver qué notas raras vas a escribir."),
        ("abrir visual studio code", "abre visual studio code", "abre vs code", "abre code"): ("code", "[smug] Abriendo Visual Studio Code. A picar código, pedazo de hacker."),
        ("abrir navegador", "abre chrome", "abrir chrome", "chrome"): ("chrome", "[smug] Abriendo Google Chrome. No te pongas a perder el tiempo en tonterías."),
        ("abre edge", "abrir edge"): ("msedge", "[smug] Abriendo Microsoft Edge."),
        ("abre discord", "abrir discord", "discord"): ("discord", "[happy] Abriendo Discord. A ver con quién vas a chismear ahora."),
        ("abre explorador de archivos", "abre explorador", "mis archivos", "explorador de archivos"): ("explorer", "[smug] Abriendo el Explorador de Archivos."),
        ("administrador de tareas", "abre administrador de tareas"): ("taskmgr", "[thinking] Abriendo el Administrador de Tareas. A ver qué proceso te está comiendo la memoria."),
        ("configuración", "abrir configuración", "abre configuración"): ("start ms-settings:", "[relaxed] Abriendo la configuración de Windows."),
        ("abrir terminal", "abre la terminal", "abre powershell", "abrir powershell"): ("powershell", "[smug] Abriendo la terminal. Ten cuidado con lo que tocas."),
        ("abrir paint", "abre paint"): ("mspaint", "[happy] Abriendo Paint. A ver con qué garabato me sales."),
    }

    for triggers, (app_exec, msg) in app_commands.items():
        if any(trigger in cmd for trigger in triggers):
            try:
                subprocess.Popen(app_exec, shell=True)
                return True, msg
            except Exception as e:
                return True, f"[angry] Intenté abrir la aplicación pero ocurrió un error: {e}"

    # --- 6.2 CERRAR / MATAR PROCESOS Y APLICACIONES ---
    close_commands = {
        ("cierra spotify", "cerrar spotify", "matar spotify"): ("Spotify.exe", "[smug] Spotify cerrado."),
        ("cierra discord", "cerrar discord", "matar discord"): ("Discord.exe", "[happy] Discord cerrado."),
        ("cierra chrome", "cerrar chrome", "cierra el navegador"): ("chrome.exe", "[smug] Google Chrome cerrado."),
        ("cierra edge", "cerrar edge"): ("msedge.exe", "[smug] Microsoft Edge cerrado."),
        ("cierra vs code", "cierra code", "cerrar vs code", "cerrar visual studio code"): ("Code.exe", "[smug] Visual Studio Code cerrado."),
        ("cierra bloc de notas", "cerrar bloc de notas", "cierra notepad"): ("notepad.exe", "[relaxed] Bloc de notas cerrado."),
        ("cierra lol", "cierra league of legends", "cerrar lol"): ("LeagueClient.exe", "[smug] League of Legends cerrado."),
        ("cierra fortnite", "cerrar fortnite"): ("FortniteClient-Win64-Shipping.exe", "[smug] Fortnite cerrado."),
        ("cierra steam", "cerrar steam"): ("steam.exe", "[smug] Steam cerrado."),
        ("cierra calculadora", "cerrar calculadora"): ("CalculatorApp.exe", "[relaxed] Calculadora cerrada."),
    }

    for triggers, (proc_name, msg) in close_commands.items():
        if any(trigger in cmd for trigger in triggers):
            try:
                subprocess.run(["taskkill", "/F", "/IM", proc_name], capture_output=True)
                return True, msg
            except Exception as e:
                return True, f"[angry] Error al intentar cerrar el proceso: {e}"

    # --- 7. BÚSQUEDAS EN GOOGLE, YOUTUBE Y WIKIPEDIA ---
    if cmd.startswith("busca en google ") or cmd.startswith("buscar en google "):
        query = cmd.replace("busca en google ", "").replace("buscar en google ", "").strip()
        webbrowser.open(f"https://www.google.com/search?q={query}")
        return True, f"[smug] Buscando '{query}' en Google. No sabes hacer nada sin mí, ¿verdad?"

    if cmd.startswith("busca en youtube ") or cmd.startswith("buscar en youtube "):
        query = cmd.replace("busca en youtube ", "").replace("buscar en youtube ", "").strip()
        webbrowser.open(f"https://www.youtube.com/results?search_query={query}")
        return True, f"[excited] Buscando '{query}' en YouTube. ¡A ver qué video raro vas a mirar!"

    if cmd.startswith("pon música ") or cmd.startswith("reproduce en youtube ") or cmd.startswith("pon ") and ("música" in cmd or "canción" in cmd):
        query = cmd.replace("pon música ", "").replace("reproduce en youtube ", "").replace("pon ", "").strip()
        webbrowser.open(f"https://www.youtube.com/results?search_query={query}")
        return True, f"[excited] Buscando '{query}' en YouTube para reproducir. ¡A disfrutar!"

    if cmd.startswith("busca en wikipedia ") or cmd.startswith("qué dice wikipedia sobre ") or cmd.startswith("wikipedia "):
        termino = cmd.replace("busca en wikipedia ", "").replace("qué dice wikipedia sobre ", "").replace("wikipedia ", "").strip()
        try:
            url = f"https://es.wikipedia.org/api/rest_v1/page/summary/{termino.replace(' ', '_')}"
            headers = {"User-Agent": "JarvisVirtualAssistant/1.0 (Windows NT 10.0; Win64; x64)"}
            res = requests.get(url, headers=headers, timeout=5)
            if res.status_code == 200:
                data = res.json()
                extracto = data.get("extract", "")
                if extracto:
                    primer_parrafo = extracto.split(".")[0] + "."
                    return True, f"Según Wikipedia: {primer_parrafo}"
            return True, f"No encontré un artículo directo en Wikipedia para {termino}."
        except Exception:
            webbrowser.open(f"https://es.wikipedia.org/wiki/{termino}")
            return True, f"Buscando {termino} en Wikipedia."

    # --- 8. CLIMA ---
    if any(p in cmd for p in ["qué clima hace", "clima de hoy", "cómo está el clima", "el clima", "temperatura"]):
        # Extraer ciudad si la menciona, ej. "clima en buenos aires"
        ciudad = ""
        if " en " in cmd:
            ciudad = cmd.split(" en ")[-1].strip()
        try:
            query_city = ciudad if ciudad else ""
            res = requests.get(f"https://wttr.in/{query_city}?format=%C,+temperatura+%t,+humedad+%h&lang=es", timeout=5)
            if res.status_code == 200:
                clima_txt = res.text.strip()
                ubicacion_txt = f"en {ciudad}" if ciudad else "en tu ubicación"
                return True, f"El clima {ubicacion_txt} reporta: {clima_txt}."
        except Exception:
            pass
        return True, "No pude consultar el clima en este momento, verifica la conexión."

    # --- 9. NOTAS Y RECORDATORIOS ---
    if cmd.startswith("anota ") or cmd.startswith("agrega una nota ") or cmd.startswith("guarda una nota "):
        nota = cmd.replace("anota ", "").replace("agrega una nota ", "").replace("guarda una nota ", "").strip()
        now = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
        with open(NOTES_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{now}] {nota}\n")
        return True, f"Nota guardada: {nota}"

    if any(p in cmd for p in ["lee mis notas", "qué notas tengo", "leer notas", "mis notas"]):
        if not NOTES_FILE.exists() or NOTES_FILE.stat().st_size == 0:
            return True, "No tienes ninguna nota guardada."
        with open(NOTES_FILE, "r", encoding="utf-8") as f:
            lineas = [l.strip() for l in f.readlines() if l.strip()]
        ultimas = lineas[-3:]  # Leer las últimas 3 notas
        res_notas = " ".join([f"Nota: {n.split('] ')[-1]}." for n in ultimas])
        return True, f"Tienes {len(lineas)} notas. Las más recientes dicen: {res_notas}"

    if any(p in cmd for p in ["borra mis notas", "eliminar notas", "vaciar notas"]):
        if NOTES_FILE.exists():
            with open(NOTES_FILE, "w", encoding="utf-8") as f:
                f.write("")
        return True, "Todas tus notas han sido borradas."

    # No coincide con ningún comando de sistema directo
    return False, ""
