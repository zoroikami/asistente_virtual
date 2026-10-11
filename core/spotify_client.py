"""
core/spotify_client.py - Control de Spotify y Música por Voz para Yize
Permite pedirle a Yize canciones, artistas o playlists temáticas ("algo para estudiar", "synthwave"),
usando la API oficial de Spotify (si hay credenciales) o el protocolo URI nativo de Windows (sin necesidad de API).
"""

import os
import urllib.parse
import webbrowser
import pyautogui
from typing import Optional
from core.config import logger

PRESETS_PLAYLISTS = {
    "estudiar": "spotify:playlist:37i9dQZF1DX8Uebhn9wzrS",      # Lo-Fi Beats
    "lofi": "spotify:playlist:37i9dQZF1DX8Uebhn9wzrS",          # Lo-Fi Beats
    "estudio": "spotify:playlist:37i9dQZF1DX8Uebhn9wzrS",
    "concentracion": "spotify:playlist:37i9dQZF1DX3qCx52yW8Bs",  # Deep Focus
    "concentrarse": "spotify:playlist:37i9dQZF1DX3qCx52yW8Bs",
    "synthwave": "spotify:playlist:37i9dQZF1DXdLEN7aqioXM",     # Retrowave / Synthwave
    "chill": "spotify:playlist:37i9dQZF1DX4WYpdgoIcn6",         # Chill Tracks
    "rock": "spotify:playlist:37i9dQZF1DXCF6MNR0TM96",          # Rock Classics
    "anime": "spotify:playlist:37i9dQZF1DX6XceWZJ1Ap4",         # Anime Hits
    "gaming": "spotify:playlist:37i9dQZF1DWTyiBJ6yEqeu",        # Top Gaming Tracks
}


class SpotifyController:
    def __init__(self):
        self.client_id = os.getenv("SPOTIFY_CLIENT_ID")
        self.client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
        self._sp = None
        self._init_api()

    def _init_api(self):
        if self.client_id and self.client_secret:
            try:
                import spotipy
                from spotipy.oauth2 import SpotifyOAuth
                scope = "user-modify-playback-state user-read-playback-state"
                self._sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
                    client_id=self.client_id,
                    client_secret=self.client_secret,
                    redirect_uri="http://localhost:8888/callback",
                    scope=scope,
                    open_browser=False
                ))
                logger.info("🎵 [Spotify] Cliente Spotipy Web API inicializado")
            except Exception as e:
                logger.debug(f"[Spotify] Spotipy no configurado o sin token: {e}")
                self._sp = None

    def play_preset_or_query(self, query: str) -> str:
        """Reproduce música buscando por preset temático o nombre de canción/artista."""
        q_clean = query.lower().strip()

        # 1. Comprobar presets
        for key, uri in PRESETS_PLAYLISTS.items():
            if key in q_clean:
                self._launch_uri(uri)
                respuestas = {
                    "estudiar": "Poniendo Lo-Fi Beats para que finjas que estás estudiando seriamente.",
                    "lofi": "Poniendo algo de Lo-Fi relajante. Respira hondo.",
                    "concentracion": "Poniendo música de enfoque profundo. Sin distracciones esta vez.",
                    "synthwave": "Subiendo el synthwave ochentero. Ahora sí pareces un hacker de película.",
                    "gaming": "Música para subir la adrenalina. Espero que no manquées esta partida.",
                    "anime": "Poniendo openings y anime hits. Despierta tu espíritu otaku.",
                }
                return respuestas.get(key, f"Reproduciendo playlist de {key}.")

        # 2. Si no es preset, buscar término en Spotify
        term = q_clean
        prefixes = [
            "pone una cancion en spotify de", "pone una canción en spotify de",
            "pone una cancion en spotify", "pone una canción en spotify",
            "pon una cancion en spotify de", "pon una canción en spotify de",
            "pon una cancion en spotify", "pon una canción en spotify",
            "pone una canción de", "pone una cancion de", "pone una canción", "pone una cancion",
            "pon una canción de", "pon una cancion de", "pon una canción", "pon una cancion",
            "reproduce una canción de", "reproduce una cancion de",
            "reproduce una canción", "reproduce una cancion",
            "pon música de", "pon musica de", "pon canciones de", "pon algo de",
            "reproduce en spotify", "pon en spotify", "pone en spotify",
            "ponme una canción", "ponme una cancion", "ponme música", "ponme musica",
            "pon temas de", "pone temas de", "pon canciones", "pone canciones",
            "pon a", "pon", "pone", "reproduce a", "reproduce"
        ]
        for prefix in prefixes:
            if term.startswith(prefix):
                term = term[len(prefix):].strip()
                break

        if term.endswith("en spotify"):
            term = term[:-10].strip()

        if not term:
            term = "lofi hip hop"

        # Si tenemos Spotipy API y dispositivo activo
        if self._sp:
            try:
                results = self._sp.search(q=term, limit=1, type="track")
                tracks = results.get("tracks", {}).get("items", [])
                if tracks:
                    track_uri = tracks[0]["uri"]
                    track_name = tracks[0]["name"]
                    artist_name = tracks[0]["artists"][0]["name"]
                    self._sp.start_playback(uris=[track_uri])
                    return f"Reproduciendo '{track_name}' de {artist_name} en Spotify."
            except Exception as e:
                logger.debug(f"[Spotify] Fallback a protocolo URI por: {e}")

        # 3. Protocolo nativo de Windows (spotify:search:...)
        encoded = urllib.parse.quote(term)
        uri = f"spotify:search:{encoded}"
        self._launch_uri(uri)
        return f"Buscando y abriendo '{term}' en Spotify."

    def _launch_uri(self, uri: str):
        try:
            import psutil
            is_running = any('spotify' in p.name().lower() for p in psutil.process_iter(['name']))
            if not is_running:
                from core.actions import lanzar_spotify
                lanzar_spotify()
                import time
                time.sleep(1.5)
            # Abrir por protocolo URI de Windows
            os.system(f'start "" "{uri}"')
            try:
                pyautogui.FAILSAFE = False
                pyautogui.sleep(1.2)
                pyautogui.press("playpause")
            except Exception:
                pass
        except Exception as e:
            logger.error(f"[Spotify] Error lanzando URI: {e}")
            webbrowser.open(f"https://open.spotify.com/search/{urllib.parse.quote(uri)}")

    def next_track(self) -> str:
        pyautogui.press("nexttrack")
        return "Siguiente pista. Esa ya me tenía con dolor de cabeza."

    def prev_track(self) -> str:
        pyautogui.press("prevtrack")
        return "Pista anterior."

    def toggle_play(self) -> str:
        pyautogui.press("playpause")
        return "Reproducción alternada."


spotify_ctl = SpotifyController()
