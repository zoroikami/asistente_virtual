"""
agent_tools.py — Herramientas del "Cuerpo Virtual" de Yize.
Permite a Gemini interactuar directamente con Windows:
- Mover ratón y hacer clics
- Escribir en teclado y pulsar atajos
- Ejecutar comandos de terminal (PowerShell/CMD)
- Crear, editar y leer archivos
- Abrir aplicaciones y páginas web
- Mirar y analizar la pantalla en tiempo real
"""
import os
import sys
import subprocess
import webbrowser
import time
from pathlib import Path

import pyautogui
import psutil

# Configuración de seguridad de PyAutoGUI
pyautogui.FAILSAFE = True  # Mover el cursor a la esquina superior izquierda aborta
pyautogui.PAUSE = 0.1      # Pausa pequeña entre acciones

BASE_DIR = Path(__file__).resolve().parent


# ─── 1. Control de Terminal y Comandos ────────────────────────────────────────

def ejecutar_comando_consola(comando: str) -> str:
    """
    Ejecuta un comando en la consola de comandos de Windows (PowerShell/CMD) y devuelve su salida.
    Útil para crear carpetas, ejecutar scripts, instalar paquetes con pip o npm, ver estado de red, etc.
    Args:
        comando: El comando de consola a ejecutar (ej. 'dir', 'git status', 'pip install requests').
    """
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-Command", comando],
            capture_output=True,
            text=True,
            timeout=25,
            encoding="utf-8",
            errors="replace"
        )
        salida = proc.stdout.strip()
        error = proc.stderr.strip()

        resultado = ""
        if salida:
            resultado += f"Salida:\n{salida[:1500]}"
        if error:
            resultado += f"\nErrores:\n{error[:800]}"
        return resultado if resultado else "Comando ejecutado con éxito sin salida de texto."
    except subprocess.TimeoutExpired:
        return f"El comando tardó más de 25 segundos y se detuvo por seguridad."
    except Exception as e:
        return f"Error ejecutando comando: {e}"


# ─── 2. Manejo de Archivos ───────────────────────────────────────────────────

def crear_o_escribir_archivo(ruta_archivo: str, contenido: str) -> str:
    """
    Crea o sobrescribe un archivo en la computadora con el contenido especificado.
    Args:
        ruta_archivo: Ruta relativa o absoluta del archivo (ej. 'hola.py', 'notas/mi_nota.txt').
        contenido: El texto o código fuente a escribir dentro del archivo.
    """
    try:
        path = Path(ruta_archivo)
        if not path.is_absolute():
            path = BASE_DIR / path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contenido, encoding="utf-8")
        return f"Archivo creado exitosamente en: {path.name} ({len(contenido)} caracteres)"
    except Exception as e:
        return f"Error al escribir archivo: {e}"


def leer_archivo(ruta_archivo: str) -> str:
    """
    Lee el contenido de un archivo de texto o código en la computadora.
    Args:
        ruta_archivo: Ruta del archivo a leer.
    """
    try:
        path = Path(ruta_archivo)
        if not path.is_absolute():
            path = BASE_DIR / path
        if not path.exists():
            return f"El archivo no existe: {ruta_archivo}"
        content = path.read_text(encoding="utf-8", errors="replace")
        return content[:2500] if len(content) > 2500 else content
    except Exception as e:
        return f"Error leyendo archivo: {e}"


def listar_archivos(directorio: str = ".") -> str:
    """
    Lista los archivos y carpetas dentro de un directorio.
    Args:
        directorio: Ruta del directorio a explorar (por defecto el directorio actual del asistente).
    """
    try:
        path = Path(directorio)
        if not path.is_absolute():
            path = BASE_DIR / path
        if not path.exists():
            return f"La carpeta no existe: {directorio}"
        items = os.listdir(path)
        return "Archivos y carpetas:\n" + "\n".join(items[:50])
    except Exception as e:
        return f"Error listando archivos: {e}"


# ─── 3. Control de Ratón y Teclado (Computer Use) ──────────────────────────────

def hacer_clic(x: int, y: int, tipo: str = "izquierdo") -> str:
    """
    Mueve el cursor del ratón a las coordenadas (x, y) de la pantalla y hace clic.
    Args:
        x: Coordenada horizontal en píxeles.
        y: Coordenada vertical en píxeles.
        tipo: 'izquierdo', 'derecho' o 'doble'.
    """
    try:
        screen_w, screen_h = pyautogui.size()
        x_clamped = max(0, min(screen_w - 1, x))
        y_clamped = max(0, min(screen_h - 1, y))

        pyautogui.moveTo(x_clamped, y_clamped, duration=0.25)
        if tipo == "derecho":
            pyautogui.rightClick()
        elif tipo == "doble":
            pyautogui.doubleClick()
        else:
            pyautogui.click()
        return f"Clic {tipo} realizado en ({x_clamped}, {y_clamped})."
    except Exception as e:
        return f"Error haciendo clic: {e}"


def escribir_texto(texto: str) -> str:
    """
    Escribe una cadena de texto en la ventana o campo actualmente activo donde esté el cursor.
    Args:
        texto: El texto que se va a teclear.
    """
    try:
        # Usamos escribir con portapapeles para soportar tildes, ñ y caracteres especiales
        import pyperclip
        pyperclip.copy(texto)
        pyautogui.hotkey("ctrl", "v")
        return f"Texto escrito ({len(texto)} caracteres)."
    except Exception:
        try:
            pyautogui.write(texto, interval=0.03)
            return f"Texto tecleado: {texto[:30]}..."
        except Exception as e2:
            return f"Error escribiendo texto: {e2}"


def presionar_teclas(combinacion: str) -> str:
    """
    Presiona una tecla o combinación de atajos de teclado de Windows.
    Ejemplos de teclas: 'enter', 'esc', 'tab', 'backspace', 'win', 'space'.
    Ejemplos de combinaciones con '+': 'ctrl+c', 'ctrl+v', 'alt+tab', 'win+d', 'win+s', 'ctrl+shift+esc'.
    Args:
        combinacion: La tecla o teclas separadas por '+' a presionar.
    """
    try:
        keys = [k.strip().lower() for k in combinacion.split("+")]
        if len(keys) == 1:
            pyautogui.press(keys[0])
        else:
            pyautogui.hotkey(*keys)
        return f"Atajo ejecutado: {combinacion}"
    except Exception as e:
        return f"Error al presionar teclas: {e}"


def desplazar_raton(clicks: int) -> str:
    """
    Desplaza la rueda del ratón hacia arriba (positivo) o hacia abajo (negativo).
    Args:
        clicks: Cantidad de desplazamiento (ej. 300 para subir, -300 para bajar).
    """
    try:
        pyautogui.scroll(clicks)
        direccion = "arriba" if clicks > 0 else "abajo"
        return f"Desplazamiento hacia {direccion} realizado."
    except Exception as e:
        return f"Error desplazando rueda: {e}"


# ─── 4. Abrir Programas y Sitios Web ──────────────────────────────────────────

def abrir_programa_o_web(objetivo: str) -> str:
    """
    Abre cualquier aplicación de Windows (ej. 'chrome', 'spotify', 'code', 'notepad', 'calc')
    o cualquier dirección web URL (ej. 'https://youtube.com', 'https://github.com').
    Args:
        objetivo: Nombre del programa ejecutable o URL a abrir.
    """
    target = objetivo.strip()
    if target.startswith("http://") or target.startswith("https://") or target.startswith("www."):
        if not target.startswith("http"):
            target = "https://" + target
        webbrowser.open(target)
        return f"Abriendo página web: {target}"

    # 1. Intentar lanzar como juego o acceso directo (Fortnite, LoL, Riot, Epic, etc.)
    try:
        from actions import lanzar_juego_o_acceso_directo
        ok, msg = lanzar_juego_o_acceso_directo(f"abre {target}")
        if ok:
            return msg
    except Exception:
        pass

    # 2. Aplicaciones comunes de Windows
    shortcuts = {
        "spotify": "spotify",
        "chrome": "chrome",
        "google chrome": "chrome",
        "vs code": "code",
        "vscode": "code",
        "visual studio code": "code",
        "discord": "discord",
        "notepad": "notepad",
        "bloc de notas": "notepad",
        "calculadora": "calc",
        "terminal": "powershell",
        "cmd": "cmd",
        "explorador": "explorer",
        "archivos": "explorer",
        "paint": "mspaint",
        "administrador de tareas": "taskmgr",
        "configuracion": "start ms-settings:",
    }

    cmd = shortcuts.get(target.lower(), target)
    try:
        subprocess.Popen(cmd, shell=True)
        return f"Aplicación '{target}' iniciada correctamente."
    except Exception as e:
        return f"No se pudo abrir '{target}': {e}"


# ─── 5. Mirar Pantalla ────────────────────────────────────────────────────────

def mirar_pantalla_actual(instruccion: str = "Describe lo que ves en la pantalla") -> str:
    """
    Toma una captura de pantalla y la analiza para saber qué hay visible en el monitor del usuario.
    Útil antes de hacer clics o para ver el resultado de una acción.
    Args:
        instruccion: Qué buscar o verificar en la pantalla (ej. 'dónde está el botón de play', 'hay algún error visible').
    """
    from vision import analyze_screen
    try:
        res = analyze_screen(user_question=instruccion)
        if "No pude tomar" in res or "No se pudo" in res or "error" in res.lower():
            from live_companion import get_live_companion
            return "Información actual de la pantalla y el sistema:\n" + get_live_companion().get_live_context_summary()
        return res
    except Exception:
        from live_companion import get_live_companion
        return get_live_companion().get_live_context_summary()


# ─── 6. Memoria a Largo Plazo ─────────────────────────────────────────────────

def guardar_recuerdo_en_memoria(categoria: str, clave: str, valor: str) -> str:
    """
    Guarda información, preferencias, gustos o hechos sobre el usuario en tu memoria a largo plazo
    para recordarlos en futuras sesiones.
    Args:
        categoria: 'perfil_usuario', 'aprendizajes_y_preferencias' o 'proyectos_y_contexto'.
        clave: Concepto clave (ej. 'juego_favorito', 'lenguaje_preferido', 'horario_trabajo').
        valor: La información a recordar.
    """
    from memory import guardar_recuerdo
    return guardar_recuerdo(categoria, clave, valor)


def consultar_recuerdos_de_memoria(termino: str = "") -> str:
    """
    Consulta tu memoria persistente para recordar datos previos del usuario, proyectos o configuraciones.
    Args:
        termino: Palabra clave a buscar. Si está vacío, devuelve un resumen de lo que recuerdas.
    """
    from memory import consultar_recuerdos
    return consultar_recuerdos(termino)


# ─── 7. Búsqueda de Información en Internet ───────────────────────────────────

def buscar_informacion_en_internet(consulta: str) -> str:
    """
    Busca información en internet (artículos, definiciones, datos en vivo, parches de juegos).
    Args:
        consulta: La búsqueda o tema a investigar.
    """
    import requests
    import urllib.parse

    query = consulta.strip()
    # 1. Probar Wikipedia API en español
    try:
        url_wiki = f"https://es.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(query.replace(' ', '_'))}"
        headers = {"User-Agent": "YizeAssistant/2.0 (Windows NT 10.0; Win64; x64)"}
        res = requests.get(url_wiki, headers=headers, timeout=6)
        if res.status_code == 200:
            data = res.json()
            extract = data.get("extract", "")
            if extract:
                return f"Wikipedia: {extract[:900]}"
    except Exception:
        pass

    # 2. Probar DuckDuckGo Instant Answer API
    try:
        url_ddg = f"https://api.duckduckgo.com/?q={urllib.parse.quote(query)}&format=json&no_html=1"
        res2 = requests.get(url_ddg, timeout=6)
        if res2.status_code == 200:
            d2 = res2.json()
            answer = d2.get("AbstractText", "") or d2.get("Answer", "")
            if answer:
                return f"DuckDuckGo: {answer[:900]}"
    except Exception:
        pass

    return f"No se encontró un resumen directo en internet para '{query}', pero puedo abrir una búsqueda en el navegador si lo deseas."


# ─── 8. Estado del Sistema y Gestión de Procesos ──────────────────────────────

def obtener_estado_del_sistema() -> str:
    """
    Obtiene el estado actual del equipo: uso de CPU, memoria RAM, estado de batería y programas principales en ejecución.
    """
    import psutil
    cpu = psutil.cpu_percent(interval=0.3)
    ram = psutil.virtual_memory()
    ram_gb_usada = round(ram.used / (1024**3), 1)
    ram_gb_total = round(ram.total / (1024**3), 1)
    
    msg = f"CPU al {cpu}%. RAM al {ram.percent}% ({ram_gb_usada} GB de {ram_gb_total} GB)."
    bat = psutil.sensors_battery()
    if bat:
        estado_bat = "conectada" if bat.power_plugged else "batería"
        msg += f" Batería: {bat.percent}% ({estado_bat})."
    return msg


def cerrar_proceso_o_ventana(nombre_proceso: str) -> str:
    """
    Cierra una aplicación o proceso en ejecución si está trabado o el usuario pide cerrarlo (ej. 'chrome', 'fortnite', 'notepad').
    Args:
        nombre_proceso: Nombre del ejecutable o programa a cerrar.
    """
    proc_clean = nombre_proceso.lower().strip()
    if not proc_clean.endswith(".exe"):
        proc_clean += ".exe"
    try:
        subprocess.run(["taskkill", "/F", "/IM", proc_clean], capture_output=True, text=True, timeout=8)
        return f"Proceso '{proc_clean}' cerrado."
    except Exception as e:
        return f"Error al intentar cerrar '{proc_clean}': {e}"


# ─── 9. Telemetría y Acompañamiento en Tiempo Real (Live Companion) ───────────

def obtener_telemetria_y_contexto_en_vivo() -> str:
    """
    Obtiene la telemetría viva de lo que ocurre en la computadora ahora mismo:
    - Si el usuario está jugando League of Legends: campeón, nivel, KDA, oro, CS, dragones, barones, marcador y eventos.
    - Ventana enfocada en Windows y aplicaciones abiertas.
    - Rendimiento actual del equipo.
    Útil para saber qué está haciendo o jugando el usuario antes de opinar o responder.
    """
    from live_companion import get_live_companion
    return get_live_companion().get_live_context_summary()


def activar_modo_en_vivo(intervalo_segundos: int = 12) -> str:
    """
    Activa el Modo En Vivo de Yize para que observe la pantalla y partidas en tiempo real
    y emita opiniones, consejos y reacciones de forma autónoma mientras el usuario juega o trabaja.
    Args:
        intervalo_segundos: Frecuencia de revisión (por defecto 12 segundos).
    """
    from live_companion import get_live_companion
    comp = get_live_companion()
    comp.start(interval=intervalo_segundos)
    return "Modo En Vivo activado. Yize ahora está observando y comentará tus jugadas y pantalla en tiempo real."


def desactivar_modo_en_vivo() -> str:
    """
    Pausa el Modo En Vivo de Yize para que deje de comentar automáticamente de fondo.
    """
    from live_companion import get_live_companion
    comp = get_live_companion()
    comp.stop()
    return "Modo En Vivo desactivado. Yize esperará a que le hables directamente."


def comentar_en_tiempo_real(motivo: str = "") -> str:
    """
    Genera una opinión o reacción inmediata en vivo con criterio propio sobre la partida actual o lo que hay en pantalla.
    Args:
        motivo: Detalle opcional (ej. 'opinión sobre mi KDA', 'comenta la última jugada', 'qué opinas de mi partida').
    """
    from live_companion import get_live_companion
    return get_live_companion().generate_live_reaction(trigger_hint=motivo)


def controlar_energia_equipo(accion: str = "apagar", segundos: int = 60) -> str:
    """
    Controla el estado de energía de la computadora: apagar, reiniciar o cancelar apagado.
    Args:
        accion: 'apagar', 'reiniciar' o 'cancelar'.
        segundos: Tiempo de gracia antes de apagar o reiniciar en segundos (por defecto 60).
    """
    import subprocess
    try:
        if accion == "cancelar":
            subprocess.run(["shutdown", "/a"], capture_output=True)
            return "Apagado del sistema cancelado con éxito."
        elif accion == "reiniciar":
            subprocess.run(["shutdown", "/r", "/t", str(segundos)], capture_output=True)
            return f"Reinicio programado en {segundos} segundos."
        else:
            subprocess.run(["shutdown", "/s", "/t", str(segundos)], capture_output=True)
            return f"Apagado de la computadora programado en {segundos} segundos. Di 'cancela el apagado' para anularlo."
    except Exception as e:
        return f"Error ejecutando orden de energía: {e}"


def cambiar_expresion_avatar_live2d(expresion: str) -> str:
    """
    Cambia la expresión facial o activa un hotkey del avatar Live2D en VTube Studio.
    Args:
        expresion: Nombre de la emoción o hotkey (ej. 'smile', 'sonrisa', 'angry', 'enojo', 'blush', 'sonrojo', 'sorpresa').
    """
    try:
        from vts_bridge import get_vts_bridge
        bridge = get_vts_bridge()
        if not bridge.is_authenticated:
            return "VTube Studio no está conectado o no tiene la API autorizada aún."
        bridge.trigger_hotkey_by_name(expresion)
        return f"Expresión '{expresion}' solicitada a VTube Studio."
    except Exception as e:
        return f"Error cambiando expresión en VTube Studio: {e}"


# ─── Lista completa de herramientas exportadas para Gemini ───────────────────

ALL_AGENT_TOOLS = [
    ejecutar_comando_consola,
    crear_o_escribir_archivo,
    leer_archivo,
    listar_archivos,
    hacer_clic,
    escribir_texto,
    presionar_teclas,
    desplazar_raton,
    abrir_programa_o_web,
    mirar_pantalla_actual,
    guardar_recuerdo_en_memoria,
    consultar_recuerdos_de_memoria,
    buscar_informacion_en_internet,
    obtener_estado_del_sistema,
    cerrar_proceso_o_ventana,
    obtener_telemetria_y_contexto_en_vivo,
    activar_modo_en_vivo,
    desactivar_modo_en_vivo,
    comentar_en_tiempo_real,
    controlar_energia_equipo,
    cambiar_expresion_avatar_live2d,
]


