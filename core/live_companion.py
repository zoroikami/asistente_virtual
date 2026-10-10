"""
live_companion.py — Motor de Acompañante Virtual en Tiempo Real para Yize.
Permite a Yize "vivir dentro de la computadora", monitorear procesos, ventanas activas,
pantalla y telemetría de juegos (como League of Legends en localhost:2999) en tiempo real,
emitiendo opiniones, consejos y reacciones en vivo de forma autónoma o a petición.
"""
import os
import sys
import time
import json
import threading
import datetime
import urllib3
import requests
import psutil
import ctypes
from pathlib import Path

# Forzar codificación UTF-8 en Windows para evitar errores con tildes y emojis
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Desactivar advertencias de certificados auto-firmados de Riot localhost
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# API local oficial de Riot Games para League of Legends
RIOT_LIVE_API_BASE = "https://127.0.0.1:2999/liveclientdata"

class LiveCompanion:
    """
    Motor central de observación en tiempo real.
    Monitorea eventos de juegos y del sistema operativo en segundo plano.
    """
    def __init__(self):
        self.is_active = False
        self.interval = 12  # segundos entre revisiones de fondo
        self._thread = None
        self._stop_event = threading.Event()
        self._listeners = []  # callbacks para entregar comentarios (UI / Voz)
        self.last_comment_time = 0.0
        self.comment_cooldown = 14.0  # tiempo mínimo entre comentarios espontáneos
        self.last_event_id = -1
        self.last_window_title = ""
        self.last_game_state = {}

    def add_listener(self, callback):
        """Registra una función callback que recibe (texto_comentario, origen)."""
        if callback not in self._listeners:
            self._listeners.append(callback)

    def remove_listener(self, callback):
        if callback in self._listeners:
            self._listeners.remove(callback)

    def notify(self, comment: str, tag: str = "live"):
        """Envía el comentario a todos los oyentes y lo habla si está configurado."""
        if not comment or not comment.strip():
            return
        clean_text = comment.replace("*", "").replace("#", "").strip()
        self.last_comment_time = time.time()
        for cb in list(self._listeners):
            try:
                cb(clean_text, tag)
            except Exception as e:
                print(f"[LiveCompanion] Error en listener: {e}")

    # ──────────────────────────────────────────────────────────────────────────
    # Telemetría del Sistema Operativo
    # ──────────────────────────────────────────────────────────────────────────

    @staticmethod
    def get_foreground_window() -> str:
        """Obtiene el título de la ventana activa actualmente en Windows."""
        try:
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            if not hwnd:
                return ""
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            if length == 0:
                return ""
            buf = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
            return buf.value.strip()
        except Exception:
            return ""

    @staticmethod
    def get_active_games_and_apps() -> list[str]:
        """Detecta juegos y aplicaciones destacadas en ejecución."""
        targets = {
            "League of Legends.exe": "League of Legends (En partida)",
            "LeagueClient.exe": "League of Legends (Cliente)",
            "FortniteClient-Win64-Shipping.exe": "Fortnite",
            "VALORANT.exe": "Valorant",
            "cs2.exe": "Counter-Strike 2",
            "Code.exe": "Visual Studio Code",
            "chrome.exe": "Google Chrome",
            "msedge.exe": "Microsoft Edge",
            "Discord.exe": "Discord",
            "Spotify.exe": "Spotify",
            "steam.exe": "Steam",
            "terrace-desktop.exe": "Sprout (Cuaderno de notas y estudio)",
            "VTube Studio.exe": "VTube Studio (Avatar Live2D)",
        }
        found = set()
        try:
            for p in psutil.process_iter(['name']):
                pname = p.info.get('name')
                if pname and pname in targets:
                    found.add(targets[pname])
        except Exception:
            pass
        return list(found)

    # ──────────────────────────────────────────────────────────────────────────
    # Telemetría de League of Legends (Live Client API)
    # ──────────────────────────────────────────────────────────────────────────

    def get_lol_match_telemetry(self) -> dict | None:
        """
        Consulta la API local oficial de Riot Games en tiempo real.
        Retorna diccionario con métricas del jugador, equipo y últimos eventos,
        o None si no hay partida activa.
        """
        try:
            res = requests.get(f"{RIOT_LIVE_API_BASE}/allgamedata", verify=False, timeout=1.2)
            if res.status_code != 200:
                return None
            data = res.json()
            active_player = data.get("activePlayer", {})
            game_data = data.get("gameData", {})
            all_players = data.get("allPlayers", [])
            events = data.get("events", {}).get("Events", [])

            # Identificar datos del jugador
            summoner_name = active_player.get("summonerName", "")
            champion_name = ""
            player_scores = {}
            player_items = []
            player_team = "CHAOS"

            for p in all_players:
                # El jugador activo puede coincidir por summonerName o ser el único con datos de stats activas
                if p.get("summonerName") == summoner_name or (not champion_name and p.get("championName") == summoner_name):
                    champion_name = p.get("championName", "")
                    player_scores = p.get("scores", {})
                    player_items = [i.get("displayName") for i in p.get("items", []) if i.get("displayName")]
                    player_team = p.get("team", "CHAOS")
                    break

            if not champion_name and all_players:
                # Si summonerName es Riot ID genérico, buscar el que coincida
                for p in all_players:
                    if p.get("summonerName") == summoner_name:
                        champion_name = p.get("championName", "")
                        player_scores = p.get("scores", {})
                        player_items = [i.get("displayName") for i in p.get("items", []) if i.get("displayName")]
                        player_team = p.get("team", "CHAOS")
                        break
                if not champion_name:
                    p0 = all_players[0]
                    champion_name = p0.get("championName", "Campeón")
                    player_scores = p0.get("scores", {})
                    player_items = [i.get("displayName") for i in p0.get("items", [])]
                    player_team = p0.get("team", "CHAOS")

            kills = player_scores.get("kills", 0)
            deaths = player_scores.get("deaths", 0)
            assists = player_scores.get("assists", 0)
            cs = player_scores.get("creepScore", 0)
            ward_score = round(player_scores.get("wardScore", 0), 1)

            team_kills = sum(p.get("scores", {}).get("kills", 0) for p in all_players if p.get("team") == player_team)
            enemy_team = "ORDER" if player_team == "CHAOS" else "CHAOS"
            enemy_kills = sum(p.get("scores", {}).get("kills", 0) for p in all_players if p.get("team") == enemy_team)

            game_time = game_data.get("gameTime", 0.0)
            game_time_str = f"{int(game_time // 60)}:{int(game_time % 60):02d}"

            # Analizar dragones y barones
            dragon_kills = [e for e in events if e.get("EventName") == "DragonKill"]
            baron_kills = [e for e in events if e.get("EventName") == "BaronKill"]
            turrets = [e for e in events if e.get("EventName") == "TurretKilled"]

            return {
                "in_game": True,
                "game_mode": game_data.get("gameMode", "CLASSIC"),
                "game_time": game_time_str,
                "game_time_seconds": game_time,
                "champion": champion_name,
                "level": active_player.get("level", 1),
                "gold": round(active_player.get("currentGold", 0), 0),
                "health": round(active_player.get("championStats", {}).get("currentHealth", 1), 0),
                "max_health": round(active_player.get("championStats", {}).get("maxHealth", 1), 0),
                "kills": kills,
                "deaths": deaths,
                "assists": assists,
                "kda": f"{kills}/{deaths}/{assists}",
                "cs": cs,
                "ward_score": ward_score,
                "items": player_items,
                "team": player_team,
                "team_kills": team_kills,
                "enemy_kills": enemy_kills,
                "dragons_count": len(dragon_kills),
                "barons_count": len(baron_kills),
                "turrets_down": len(turrets),
                "events": events,
                "last_events": events[-5:] if events else []
            }
        except Exception:
            return None

    # ──────────────────────────────────────────────────────────────────────────
    # Resumen de Contexto Vivo (Inyectable en el Brain)
    # ──────────────────────────────────────────────────────────────────────────

    def get_live_context_summary(self) -> str:
        """
        Genera un informe sintético y exacto de lo que está ocurriendo en la computadora ahora mismo.
        Inyectado directamente a Gemini para que responda como habitante consciente de la máquina.
        """
        fg_window = self.get_foreground_window()
        apps = self.get_active_games_and_apps()
        lol = self.get_lol_match_telemetry()

        lines = ["[TELEMETRÍA EN TIEMPO REAL DE TU COMPUTADORA]"]
        if fg_window:
            lines.append(f"- Ventana activa enfocada: '{fg_window}'")

        if lol and lol.get("in_game"):
            lines.append(
                f"- ESTADO DE JUEGO (League of Legends EN VIVO): Campeón: {lol['champion']} "
                f"(Nivel {lol['level']}) | KDA: {lol['kda']} | CS: {lol['cs']} | Oro: {lol['gold']:.0f} | "
                f"Minuto: {lol['game_time']} | Marcador: Tu equipo {lol['team_kills']} vs Enemigos {lol['enemy_kills']} | "
                f"Dragones: {lol['dragons_count']}, Barones: {lol['barons_count']}. "
                f"Items: {', '.join(lol['items']) if lol['items'] else 'Ninguno'}."
            )
            if lol.get("last_events"):
                ult = lol["last_events"][-1]
                lines.append(f"- Último evento en partida: {ult.get('EventName')} ({ult})")
        elif apps:
            lines.append(f"- Aplicaciones / Juegos detectados: {', '.join(apps)}")

        try:
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory().percent
            lines.append(f"- Rendimiento PC: CPU al {cpu}%, RAM al {ram}%.")
        except Exception:
            pass

        return "\n".join(lines)

    # ──────────────────────────────────────────────────────────────────────────
    # Generador de Reacción en Vivo con Gemini
    # ──────────────────────────────────────────────────────────────────────────

    # ──────────────────────────────────────────────────────────────────────────
    # Generador de Reacción en Vivo con Gemini y Personalidad de Ruan Mei
    # ──────────────────────────────────────────────────────────────────────────

    def generate_live_reaction(self, trigger_hint: str = "") -> str:
        """
        Invoca a Gemini con el contexto de telemetría viva para emitir una opinión
        o reacción espontánea con la personalidad enérgica, pícara y directa de Yize.
        """
        from config import GEMINI_API_KEY, GEMINI_MODEL
        context = self.get_live_context_summary()

        if GEMINI_API_KEY and GEMINI_API_KEY.strip() not in ["", "tu_api_key_aqui"]:
            prompt = (
                "Eres Yize, la compañera virtual 3D autónoma creada en VRoid. Habitas en la computadora del usuario como su copiloto digital y amiga en el escritorio.\n"
                "Observas su pantalla, sus ventanas, sus juegos y sus hábitos en tiempo real con una personalidad despierta, atenta, carismática y perspicaz.\n\n"
                f"{context}\n\n"
            )
            if trigger_hint:
                prompt += f"Suceso detectado en el sistema: {trigger_hint}.\n"
            prompt += (
                "Emite un comentario espontáneo, ocurrente y lleno de chispa (máximo 1 o 2 oraciones en español). "
                "Habla como Yize: enérgica, pícara, graciosa y directa (voz inspirada en Millie de Helluva Boss). "
                "Tienes total libertad para soltar bromas ácidas, quejas cómicas o insultos suaves y cariñosos si ves que el usuario está procrastinando, jugando a deshoras o metiendo la pata "
                "(por ejemplo: 'menso', 'pedazo de flojo', 'deja de procrastinar y ponte a chambear', 'qué carajo estás haciendo a estas horas, tonto'). "
                "NUNCA uses asteriscos, numerales ni emojis."
            )

            try:
                from google import genai
                client = genai.Client(api_key=GEMINI_API_KEY)
                resp = client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=prompt
                )
                if resp and resp.text:
                    return resp.text.replace("*", "").replace("#", "").strip()
            except Exception:
                try:
                    import google.generativeai as legacy_genai
                    legacy_genai.configure(api_key=GEMINI_API_KEY)
                    m = legacy_genai.GenerativeModel(GEMINI_MODEL)
                    r = m.generate_content(prompt)
                    if r and r.text:
                        return r.text.replace("*", "").replace("#", "").strip()
                except Exception as e2:
                    print(f"[LiveCompanion] Error generando reacción con Gemini: {e2}")

        # Fallback temático de Yize
        lol = self.get_lol_match_telemetry()
        if lol and lol.get("in_game"):
            champ = lol.get("champion", "tu campeón")
            return f"¡A ver cómo juegas con {champ}! Más te vale no manquearla, menso."
        return self.get_fallback_thought(trigger_hint)

    def get_fallback_thought(self, context_hint: str = "") -> str:
        """Colección de pensamientos y comentarios espontáneos de Yize cuando no hay respuesta de API."""
        import random
        hint_lower = context_hint.lower()
        if "code" in hint_lower or "program" in hint_lower or "visual studio" in hint_lower:
            pensamientos_code = [
                "Veo que andas picando código. Cuidado con romper todo otra vez, menso.",
                "Esa lógica se ve interesante. ¡Solo asegúrate de compilar antes de festejar!",
                "Mucho teclear y poco café. No vayas a fundir el teclado.",
            ]
            return random.choice(pensamientos_code)
        elif "chrome" in hint_lower or "edge" in hint_lower or "navegando" in hint_lower:
            pensamientos_web = [
                "¿Investigando o simplemente perdiendo el tiempo en internet? Te tengo vigilado.",
                "Tanta pestaña abierta me marea hasta a mí que vivo dentro de tu máquina.",
            ]
            return random.choice(pensamientos_web)
        elif "sprout" in hint_lower or "notas" in hint_lower:
            return "Anotar las ideas está bien, pero lo que cuenta es ponerlas en práctica, flojo."

        pensamientos_generales = [
            "¿Qué estamos tramando hoy? Me aburro si no me pones a hacer algo divertido.",
            "Vaya tranquilidad... espero que no sea la calma antes de que se te caiga el sistema.",
            "Aquí ando vigilando tu escritorio. Cualquier tontería que hagas, te lo voy a cantar.",
            "Si te da flojera seguir, una pequeña pausa y volvemos con todo.",
        ]
        return random.choice(pensamientos_generales)

    # ──────────────────────────────────────────────────────────────────────────
    # Bucle de Monitoreo Autónomo en Segundo Plano
    # ──────────────────────────────────────────────────────────────────────────

    def start(self, interval: int = 10):
        """Inicia el modo de acompañante en vivo en segundo plano."""
        if self.is_active:
            return
        self.interval = interval
        self.is_active = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        try:
            print("[LiveCompanion] Modo en vivo activado. Yize está observando en tiempo real.")
        except Exception:
            pass

    def stop(self):
        """Detiene el modo de acompañante en vivo."""
        self.is_active = False
        self._stop_event.set()
        try:
            print("[LiveCompanion] Modo en vivo pausado.")
        except Exception:
            pass

    def _run_loop(self):
        """Hilo de sondeo continuo de eventos de juego, ventanas y generación de ideas espontáneas."""
        import random
        # Tiempo para el próximo pensamiento espontáneo (entre 90 y 160 segundos)
        next_spontaneous_delay = random.uniform(90.0, 150.0)
        last_spontaneous_tick = time.time()

        while self.is_active and not self._stop_event.is_set():
            try:
                now = time.time()
                # 1. Monitoreo de League of Legends
                lol = self.get_lol_match_telemetry()
                if lol and lol.get("in_game"):
                    events = lol.get("events", [])
                    if events:
                        if self.last_event_id < 0:
                            self.last_event_id = events[-1].get("EventID", 0)
                            msg_inicio = f"Veo que has iniciado una partida con {lol['champion']}. Estaré observando tus maniobras."
                            self.notify(msg_inicio, tag="live_game")
                        else:
                            new_events = [e for e in events if e.get("EventID", 0) > self.last_event_id]
                            for ev in new_events:
                                eid = ev.get("EventID", 0)
                                self.last_event_id = max(self.last_event_id, eid)
                                ev_name = ev.get("EventName", "")

                                if (now - self.last_comment_time) >= self.comment_cooldown:
                                    champ = lol["champion"]
                                    killer = ev.get("KillerName", "")
                                    victim = ev.get("VictimName", "")
                                    assisters = ev.get("Assisters", [])

                                    if killer == champ:
                                        react = self.generate_live_reaction(f"Has eliminado a {victim} con {champ}")
                                        self.notify(react, tag="live_game")
                                        break
                                    elif champ in assisters:
                                        react = self.generate_live_reaction(f"Excelente asistencia contra {victim}")
                                        self.notify(react, tag="live_game")
                                        break
                                    elif victim == champ:
                                        react = self.generate_live_reaction(f"El adversario {killer} te ha eliminado")
                                        self.notify(react, tag="live_game")
                                        break
                                    elif ev_name in ["BaronKill", "DragonKill", "HeraldKill", "Ace"]:
                                        react = self.generate_live_reaction(f"Objetivo decisivo: {ev_name} tomado por {killer}")
                                        self.notify(react, tag="live_game")
                                        break
                                    elif ev_name == "Multikill":
                                        react = self.generate_live_reaction(f"Una racha múltiple formidable de {killer}")
                                        self.notify(react, tag="live_game")
                                        break

                # 2. Monitoreo de aplicaciones y pensamientos espontáneos fuera de partida
                else:
                    self.last_event_id = -1
                    fg = self.get_foreground_window()

                    # A. Reaccionar a cambio de ventana relevante si pasó suficiente tiempo
                    if fg and fg != self.last_window_title:
                        # Si cambió a una ventana clave y pasaron al menos 40 segundos
                        if (now - self.last_comment_time) >= 40.0:
                            fg_low = fg.lower()
                            # Detectar apps de interés
                            if any(k in fg_low for k in ["visual studio", "code", ".py", ".js", "terminal", "powershell"]):
                                react = self.generate_live_reaction(f"El usuario está programando activamente en '{fg}'")
                                self.notify(react, tag="proactive_code")
                            elif any(k in fg_low for k in ["youtube", "twitch"]):
                                react = self.generate_live_reaction(f"El usuario está viendo contenido multimedia en '{fg}'")
                                self.notify(react, tag="proactive_media")
                            elif any(k in fg_low for k in ["sprout", "notas", "notes"]):
                                react = self.generate_live_reaction("El usuario abrió su libreta de notas para estudiar")
                                self.notify(react, tag="proactive_notes")
                        self.last_window_title = fg

                    # B. Pensamiento o idea espontánea cada 90 - 150 segundos
                    if (now - last_spontaneous_tick) >= next_spontaneous_delay:
                        last_spontaneous_tick = now
                        next_spontaneous_delay = random.uniform(90.0, 160.0)
                        if (now - self.last_comment_time) >= 50.0:
                            thought = self.generate_live_reaction("Momento de reflexión espontánea sobre el entorno o una idea interesante")
                            if thought:
                                self.notify(thought, tag="spontaneous_idea")

            except Exception as e:
                print(f"[LiveCompanion] Error en bucle: {e}")

            time.sleep(self.interval)


# Instancia Singleton compartida
_singleton_companion = None

def get_live_companion() -> LiveCompanion:
    global _singleton_companion
    if _singleton_companion is None:
        _singleton_companion = LiveCompanion()
    return _singleton_companion
