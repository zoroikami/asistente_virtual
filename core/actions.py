import os
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


def execute_system_command(command: str) -> tuple[bool, str]:
    """
    Intenta ejecutar comandos nativos del sistema en base a palabras clave.
    Retorna una tupla (ejecutado: bool, respuesta_verbal: str).
    """
    cmd = command.lower().strip()

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

    # --- 6.1 ABRIR APLICACIONES POPULARES ---
    app_commands = {
        ("abrir spotify", "abre spotify", "spotify"): ("spotify", "[smug] Abriendo Spotify. A ver si pones música decente, menso."),
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
