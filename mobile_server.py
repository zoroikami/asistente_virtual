"""
mobile_server.py — Servidor Web & WebSocket para el Asistente Virtual Yize.
Permite controlar la PC e interactuar con Yize por voz y texto desde el celular
(tanto en red Wi-Fi local como desde el exterior vía túnel Cloudflare).
"""

import os
import sys
import io
import json
import time
import socket
import asyncio
import logging
import threading
import subprocess
import urllib.parse
from pathlib import Path
from typing import Set

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import psutil
import pyautogui
import qrcode
from PIL import Image
from aiohttp import web

# Middleware CORS nativo sin dependencias externas
@web.middleware
async def cors_middleware(request: web.Request, handler):
    if request.method == "OPTIONS":
        response = web.Response(status=204)
    else:
        try:
            response = await handler(request)
        except web.HTTPException as ex:
            response = ex
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    return response

# Registrar directorios de core y bridges
_ROOT = Path(__file__).resolve().parent
for _p in [str(_ROOT / "core"), str(_ROOT / "bridges")]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Importar módulos del asistente
import config
from config import ASSISTANT_NAME, EDGE_VOICE
from brain import process_query, extract_emotion
from actions import execute_system_command, lanzar_juego_o_acceso_directo
from vision import capture_screen_bytes
from live_companion import LiveCompanion, get_live_companion

# Configurar logging
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
logger = logging.getLogger("MobileServer")

# Directorio raíz del proyecto y de la web móvil
ROOT_DIR = Path(__file__).resolve().parent
WEB_DIR = ROOT_DIR / "mobile_web"
WEB_DIR.mkdir(parents=True, exist_ok=True)

# PIN de seguridad opcional (definido en config o .env)
SECURITY_PIN = os.getenv("MOBILE_PIN", "").strip()

# Clientes WebSocket conectados
ws_clients: Set[web.WebSocketResponse] = set()

# Estado en memoria
latest_speech = {"text": f"Hola, soy {ASSISTANT_NAME}. Lista para recibir tus órdenes desde el móvil.", "emotion": "smug", "time": time.time()}


def get_local_ip() -> str:
    """Detecta la IP local de la PC en la red Wi-Fi / LAN."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def generate_qr_image(url: str, output_path: Path):
    """Genera imagen QR guardada en disco para el cliente web."""
    try:
        qr = qrcode.QRCode(
            version=1,
            box_size=10,
            border=2,
        )
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#9d4edd", back_color="#0b0b14")
        img.save(output_path)
    except Exception as e:
        logger.error(f"Error generando imagen QR: {e}")


def print_terminal_qr(url: str):
    """Muestra el código QR en la consola de texto."""
    try:
        qr = qrcode.QRCode()
        qr.add_data(url)
        qr.make(fit=True)
        print("\n" + "="*56)
        print("  ESCANEA ESTE CÓDIGO CON LA CÁMARA DE TU CELULAR:")
        print("="*56 + "\n")
        qr.print_ascii(invert=True)
        print("\n" + "="*56)
        print(f"  O abre esta URL en el navegador de tu celular:")
        print(f"  👉  {url}")
        print("="*56 + "\n")
    except Exception as e:
        print(f"URL Móvil: {url} (Error QR terminal: {e})")


async def broadcast_ws(data: dict):
    """Envía un mensaje JSON a todos los teléfonos conectados."""
    if not ws_clients:
        return
    msg = json.dumps(data, ensure_ascii=False)
    dead_clients = []
    for ws in list(ws_clients):
        try:
            if not ws.closed:
                await ws.send_str(msg)
            else:
                dead_clients.append(ws)
        except Exception:
            dead_clients.append(ws)
    for ws in dead_clients:
        ws_clients.discard(ws)


# ─── LISTENERS DE EVENTOS DE YIZE EN VIVO ─────────────────────────────────────
def setup_live_listeners(loop: asyncio.AbstractEventLoop):
    """Registra callbacks en live_companion para enviar comentarios en tiempo real al celular."""
    try:
        companion = get_live_companion()
        def on_live_comment(text: str, tag: str = "live"):
            emotion, clean_text = extract_emotion(text)
            payload = {
                "type": "live_comment",
                "tag": tag,
                "text": clean_text,
                "emotion": emotion or "happy",
                "timestamp": time.time()
            }
            asyncio.run_coroutine_threadsafe(broadcast_ws(payload), loop)

        companion.add_listener(on_live_comment)
        logger.info("📡 Escuchador de LiveCompanion vinculado al WebSocket móvil")
    except Exception as e:
        logger.warning(f"No se pudo vincular LiveCompanion: {e}")


# ─── RUTAS HTTP ───────────────────────────────────────────────────────────────

async def handle_index(request: web.Request):
    """Sirve la app PWA móvil."""
    index_file = WEB_DIR / "index.html"
    if index_file.exists():
        return web.FileResponse(index_file)
    return web.Response(text="Yize Mobile Web UI no encontrada.", status=404)


async def handle_manifest(request: web.Request):
    manifest_file = WEB_DIR / "manifest.json"
    if manifest_file.exists():
        return web.FileResponse(manifest_file, headers={"Content-Type": "application/manifest+json"})
    return web.Response(status=404)


async def handle_sw(request: web.Request):
    sw_file = WEB_DIR / "sw.js"
    if sw_file.exists():
        return web.FileResponse(sw_file, headers={"Content-Type": "application/javascript"})
    return web.Response(status=404)


async def handle_status(request: web.Request):
    """Retorna estado del hardware y sistema de la PC en tiempo real."""
    cpu_percent = psutil.cpu_percent(interval=None)
    mem = psutil.virtual_memory()
    battery = psutil.sensors_battery()
    
    battery_info = None
    if battery:
        battery_info = {
            "percent": battery.percent,
            "power_plugged": battery.power_plugged,
            "seconds_left": battery.secsleft if battery.secsleft != psutil.POWER_TIME_UNLIMITED else -1
        }

    # Ventana activa
    active_window = LiveCompanion.get_foreground_window()
    active_apps = LiveCompanion.get_active_games_and_apps()

    return web.json_response({
        "ok": True,
        "assistant_name": ASSISTANT_NAME,
        "cpu_percent": cpu_percent,
        "ram_percent": mem.percent,
        "ram_used_gb": round(mem.used / (1024**3), 2),
        "ram_total_gb": round(mem.total / (1024**3), 2),
        "battery": battery_info,
        "active_window": active_window or "Escritorio / Desconocido",
        "active_apps": active_apps,
        "latest_speech": latest_speech,
        "connected_phones": len(ws_clients),
        "timestamp": time.time()
    })


async def handle_command(request: web.Request):
    """
    Ejecuta una instrucción enviada desde el móvil.
    {
      "command": "abre spotify",
      "speak_pc": true,
      "pin": "1234"
    }
    """
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "JSON inválido"}, status=400)

    if SECURITY_PIN and data.get("pin") != SECURITY_PIN:
        return web.json_response({"ok": False, "error": "PIN incorrecto"}, status=401)

    command = data.get("command", "").strip()
    speak_pc = data.get("speak_pc", True)

    if not command:
        return web.json_response({"ok": False, "error": "Comando vacío"}, status=400)

    logger.info(f"📱 Comando desde móvil: '{command}' (speak_pc={speak_pc})")

    # Procesar la orden con el cerebro de Yize
    loop = asyncio.get_running_loop()
    raw_response = await loop.run_in_executor(None, process_query, command)
    emotion, clean_text = extract_emotion(raw_response)
    if not emotion:
        emotion = "happy"

    global latest_speech
    latest_speech = {"text": clean_text, "emotion": emotion, "time": time.time()}

    # Enviar al overlay 3D en pantalla de la PC si está disponible
    try:
        from overlay_bridge import get_bridge
        b = get_bridge()
        if b:
            b.send_emotion(emotion)
            b.send_speech(clean_text, emotion)
            b.send_speech_end()
    except Exception:
        pass

    # Reproducir voz en los altavoces de la PC si está habilitado
    if speak_pc and clean_text:
        try:
            from voice import speak
            threading.Thread(target=speak, args=(clean_text,), daemon=True).start()
        except Exception as e:
            logger.warning(f"Error reproduciendo voz en PC: {e}")

    # Notificar a todos los móviles conectados vía WebSocket
    res_payload = {
        "type": "assistant_response",
        "user_command": command,
        "text": clean_text,
        "emotion": emotion,
        "raw": raw_response,
        "timestamp": time.time()
    }
    await broadcast_ws(res_payload)

    return web.json_response({
        "ok": True,
        "command": command,
        "text": clean_text,
        "emotion": emotion,
        "raw": raw_response
    })


async def handle_action(request: web.Request):
    """
    Ejecuta una acción directa del deck de control:
    volumen, multimedia, ventanas, abrir programas, bloquear PC, etc.
    """
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "JSON inválido"}, status=400)

    if SECURITY_PIN and data.get("pin") != SECURITY_PIN:
        return web.json_response({"ok": False, "error": "PIN incorrecto"}, status=401)

    action = data.get("action", "").lower().strip()
    param = data.get("param", "")
    logger.info(f"🎮 Acción rápida desde móvil: '{action}' (param={param})")

    loop = asyncio.get_running_loop()

    def do_action():
        import ctypes
        if action == "volume_up":
            for _ in range(5):
                pyautogui.press("volumeup")
            return "Volumen aumentado (+10%)"
        elif action == "volume_down":
            for _ in range(5):
                pyautogui.press("volumedown")
            return "Volumen reducido (-10%)"
        elif action == "mute":
            pyautogui.press("volumemute")
            return "Silencio alternado"
        elif action == "play_pause":
            pyautogui.press("playpause")
            return "Reproducción alternada"
        elif action == "next_track":
            pyautogui.press("nexttrack")
            return "Siguiente pista"
        elif action == "prev_track":
            pyautogui.press("prevtrack")
            return "Pista anterior"
        elif action == "lock_pc":
            ctypes.windll.user32.LockWorkStation()
            return "PC Bloqueada"
        elif action == "show_desktop":
            pyautogui.hotkey("win", "d")
            return "Escritorio mostrado"
        elif action == "screenshot":
            ts = time.strftime("%Y%m%d_%H%M%S")
            cap_path = ROOT_DIR / "capturas" / f"captura_movil_{ts}.png"
            cap_path.parent.mkdir(exist_ok=True)
            shot = pyautogui.screenshot()
            shot.save(cap_path)
            return f"Captura guardada: {cap_path.name}"
        elif action == "launch_app":
            target = param.lower().strip()
            # Mapeo rápido
            urls = {
                "youtube": "https://www.youtube.com",
                "google": "https://www.google.com",
                "chatgpt": "https://chatgpt.com",
                "twitch": "https://www.twitch.tv",
                "whatsapp": "https://web.whatsapp.com",
            }
            if target in urls:
                import webbrowser
                webbrowser.open(urls[target])
                return f"Abriendo {target.title()}"

            # Probar lanzador de juegos
            ok, msg = lanzar_juego_o_acceso_directo(f"abre {target}")
            if ok:
                return msg
            # Probar comando del sistema
            ok_sys, msg_sys = execute_system_command(f"abre {target}")
            if ok_sys:
                return msg_sys
            return f"No se pudo encontrar o abrir {target}"

        elif action == "cancel_shutdown":
            subprocess.run(["shutdown", "/a"], capture_output=True)
            return "Apagado cancelado"
        elif action == "press_key":
            if param:
                pyautogui.press(param)
                return f"Tecla '{param}' presionada"
        elif action == "type_text":
            if param:
                pyautogui.write(param)
                return "Texto escrito en la PC"
        return "Acción no reconocida"

    result_msg = await loop.run_in_executor(None, do_action)

    # Notificar WebSocket
    await broadcast_ws({
        "type": "action_executed",
        "action": action,
        "message": result_msg,
        "timestamp": time.time()
    })

    return web.json_response({"ok": True, "action": action, "message": result_msg})


async def handle_screenshot(request: web.Request):
    """Devuelve captura en vivo de la pantalla de la PC en formato JPEG ligero."""
    loop = asyncio.get_running_loop()
    try:
        jpeg_bytes, _ = await loop.run_in_executor(None, capture_screen_bytes)
        return web.Response(body=jpeg_bytes, content_type="image/jpeg", headers={
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Pragma": "no-cache"
        })
    except Exception as e:
        logger.warning(f"Aviso capturando pantalla ({e}), generando imagen de estado...")
        def make_placeholder():
            from PIL import ImageDraw
            img = Image.new("RGB", (1280, 720), color=(16, 14, 29))
            draw = ImageDraw.Draw(img)
            draw.rectangle([(20, 20), (1260, 700)], outline=(157, 78, 221), width=3)
            draw.text((640, 330), "PANTALLA DE LA PC", fill=(199, 125, 255), anchor="mm")
            draw.text((640, 375), f"Yize Copilot Activa — {time.strftime('%H:%M:%S')}", fill=(160, 160, 189), anchor="mm")
            draw.text((640, 415), "La pantalla interactiva se mostrará en sesión abierta.", fill=(108, 108, 138), anchor="mm")
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=85)
            return buf.getvalue()

        fallback_bytes = await loop.run_in_executor(None, make_placeholder)
        return web.Response(body=fallback_bytes, content_type="image/jpeg", headers={
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Pragma": "no-cache"
        })


async def handle_tts(request: web.Request):
    """
    Genera voz de Yize en tiempo real con edge-tts y la transmite como MP3 al móvil.
    GET /api/tts?text=Hola+amo
    """
    text = request.query.get("text", "").strip()
    if not text:
        return web.Response(status=400, text="Falta parámetro 'text'")

    import edge_tts
    try:
        communicate = edge_tts.Communicate(text, EDGE_VOICE)
        audio_chunks = []
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_chunks.append(chunk["data"])
        audio_data = b"".join(audio_chunks)

        return web.Response(
            body=audio_data,
            content_type="audio/mpeg",
            headers={"Content-Length": str(len(audio_data)), "Cache-Control": "public, max-age=3600"}
        )
    except Exception as e:
        logger.error(f"Error generando TTS móvil: {e}")
        return web.Response(status=500, text=f"Error TTS: {e}")


async def handle_voice_upload(request: web.Request):
    """
    Recibe un archivo de audio grabado en el móvil (WAV/WebM) y lo transcribe.
    """
    reader = await request.multipart()
    field = await reader.next()
    if not field or field.name != "audio":
        return web.json_response({"ok": False, "error": "Campo 'audio' faltante"}, status=400)

    audio_bytes = await field.read()
    if not audio_bytes:
        return web.json_response({"ok": False, "error": "Audio vacío"}, status=400)

    import speech_recognition as sr
    loop = asyncio.get_running_loop()

    def transcribe_audio():
        import tempfile
        r = sr.Recognizer()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name
            f.write(audio_bytes)

        try:
            with sr.AudioFile(temp_path) as source:
                audio_data = r.record(source)
                text = r.recognize_google(audio_data, language="es-ES")
                return text
        except sr.UnknownValueError:
            return ""
        except Exception as e:
            logger.warning(f"Fallo reconocimiento local: {e}")
            return ""
        finally:
            try:
                os.remove(temp_path)
            except Exception:
                pass

    transcribed = await loop.run_in_executor(None, transcribe_audio)
    if not transcribed:
        return web.json_response({"ok": False, "error": "No se entendió el audio"}, status=400)

    # Procesar como comando
    raw_response = await loop.run_in_executor(None, process_query, transcribed)
    emotion, clean_text = extract_emotion(raw_response)

    return web.json_response({
        "ok": True,
        "transcription": transcribed,
        "text": clean_text,
        "emotion": emotion or "happy",
        "raw": raw_response
    })


async def handle_qrcode(request: web.Request):
    """Sirve la imagen PNG del código QR."""
    qr_path = WEB_DIR / "qr.png"
    if qr_path.exists():
        return web.FileResponse(qr_path)
    return web.Response(status=404)


async def handle_ws(request: web.Request):
    """Conexión WebSocket bidireccional en tiempo real con el celular."""
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    ws_clients.add(ws)
    logger.info(f"📱 Celular conectado por WebSocket. Total activos: {len(ws_clients)}")

    # Enviar estado inicial y bienvenida
    await ws.send_str(json.dumps({
        "type": "welcome",
        "assistant_name": ASSISTANT_NAME,
        "latest_speech": latest_speech,
        "timestamp": time.time()
    }, ensure_ascii=False))

    try:
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                try:
                    payload = json.loads(msg.data)
                    msg_type = payload.get("type")
                    if msg_type == "ping":
                        await ws.send_str(json.dumps({"type": "pong", "time": time.time()}))
                    elif msg_type == "command":
                        cmd = payload.get("command", "")
                        if cmd:
                            loop = asyncio.get_running_loop()
                            res = await loop.run_in_executor(None, process_query, cmd)
                            emo, cln = extract_emotion(res)
                            await broadcast_ws({
                                "type": "assistant_response",
                                "user_command": cmd,
                                "text": cln,
                                "emotion": emo or "happy",
                                "raw": res,
                                "timestamp": time.time()
                            })
                except Exception as e:
                    logger.warning(f"Error procesando WS message: {e}")
            elif msg.type == web.WSMsgType.ERROR:
                logger.warning(f"WS connection closed with error {ws.exception()}")
    finally:
        ws_clients.discard(ws)
        logger.info(f"📱 Celular desconectado. Total activos: {len(ws_clients)}")

    return ws


# ─── TÚNEL CLOUDFLARE (ACCESO FUERA DE CASA 4G/5G) ───────────────────────────
def start_cloudflare_tunnel_if_requested(port: int, enable_tunnel: bool):
    """Inicia Cloudflare Quick Tunnel para dar acceso HTTPS público desde cualquier lugar."""
    if not enable_tunnel:
        return

    tools_cloudflared = ROOT_DIR / "tools" / "cloudflared.exe"
    cloudflared_path = tools_cloudflared if tools_cloudflared.exists() else (ROOT_DIR / "cloudflared.exe")
    if not cloudflared_path.exists():
        logger.info("⬇️ Descargando binario oficial portátil cloudflared.exe para acceso remoto...")
        import urllib.request
        try:
            (ROOT_DIR / "tools").mkdir(parents=True, exist_ok=True)
            cloudflared_path = tools_cloudflared
            url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
            urllib.request.urlretrieve(url, cloudflared_path)
            logger.info("✅ cloudflared.exe descargado correctamente.")
        except Exception as e:
            logger.error(f"Error descargando cloudflared: {e}")
            return

    def run_tunnel():
        try:
            proc = subprocess.Popen(
                [str(cloudflared_path), "tunnel", "--url", f"http://localhost:{port}"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace"
            )
            for line in proc.stderr:
                if "trycloudflare.com" in line:
                    parts = line.strip().split()
                    for p in parts:
                        if p.startswith("https://") and "trycloudflare.com" in p:
                            tunnel_url = p
                            print("\n" + "★"*64)
                            print(f"  🌐 URL PÚBLICA SEGURA (DESDE CUALQUIER LUGAR CON DATOS MÓVILES):")
                            print(f"  👉 {tunnel_url}")
                            print("★"*64 + "\n")
                            generate_qr_image(tunnel_url, WEB_DIR / "qr_tunnel.png")
                            print_terminal_qr(tunnel_url)
                            break
        except Exception as e:
            logger.error(f"Error en Cloudflare Tunnel: {e}")

    threading.Thread(target=run_tunnel, daemon=True).start()


# ─── INICIALIZACIÓN DE LA APLICACIÓN ──────────────────────────────────────────
def create_app() -> web.Application:
    app = web.Application(middlewares=[cors_middleware], client_max_size=30 * 1024 * 1024)

    # Rutas principales
    app.router.add_get("/", handle_index)
    app.router.add_get("/manifest.json", handle_manifest)
    app.router.add_get("/sw.js", handle_sw)
    app.router.add_get("/api/status", handle_status)
    app.router.add_post("/api/command", handle_command)
    app.router.add_post("/api/action", handle_action)
    app.router.add_get("/api/screenshot", handle_screenshot)
    app.router.add_get("/api/tts", handle_tts)
    app.router.add_post("/api/voice", handle_voice_upload)
    app.router.add_get("/api/qrcode", handle_qrcode)
    app.router.add_get("/ws", handle_ws)

    # Servir archivos estáticos del cliente móvil
    app.router.add_static("/static", WEB_DIR, show_index=False)
    app.router.add_static("/assets", ROOT_DIR / "assets", show_index=False)

    return app


def main():
    import argparse
    parser = argparse.ArgumentParser(description=f"Servidor Móvil {ASSISTANT_NAME}")
    parser.add_argument("--port", type=int, default=8080, help="Puerto del servidor (default: 8080)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host (default: 0.0.0.0)")
    parser.add_argument("--tunnel", action="store_true", help="Habilitar túnel HTTPS Cloudflare para acceso 4G/5G fuera de casa")
    args = parser.parse_args()

    local_ip = get_local_ip()
    local_url = f"http://{local_ip}:{args.port}"

    # Generar QR para la red Wi-Fi local
    generate_qr_image(local_url, WEB_DIR / "qr.png")

    banner = f"""
╔══════════════════════════════════════════════════════════════════════╗
║        📱 SERVIDOR MÓVIL — {ASSISTANT_NAME.upper()} REMOTE CONTROL & COPILOT        ║
║   Conecta tu celular para darle órdenes por voz y controlar tu PC    ║
╚══════════════════════════════════════════════════════════════════════╝
    """
    print(banner)
    print(f"[*] IP Local de tu PC : {local_ip}")
    print(f"[*] Puerto            : {args.port}")
    print(f"[*] Enlace Wi-Fi Local: {local_url}")
    if SECURITY_PIN:
        print(f"[*] PIN de Seguridad  : {SECURITY_PIN}")
    else:
        print(f"[*] PIN de Seguridad  : Desactivado (acceso libre)")

    # Mostrar QR en terminal
    print_terminal_qr(local_url)

    # Iniciar túnel si se solicitó
    if args.tunnel:
        start_cloudflare_tunnel_if_requested(args.port, True)
    else:
        print("💡 TIP: Para acceder desde fuera de tu casa por datos móviles 4G/5G,")
        print("        ejecuta con el parámetro --tunnel o usa 'iniciar_servidor_movil.bat'.\n")

    app = create_app()

    # Iniciar listeners de background
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    setup_live_listeners(loop)

    web.run_app(app, host=args.host, port=args.port, loop=loop)


if __name__ == "__main__":
    main()
