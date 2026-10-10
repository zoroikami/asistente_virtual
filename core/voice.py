import os
import sys
import time
import asyncio
import tempfile
from pathlib import Path
import speech_recognition as sr
import pyttsx3
import edge_tts

# Ocultar mensaje publicitario de pygame
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
import pygame

from config import (
    STT_LANGUAGE, TTS_ENGINE, EDGE_VOICE,
    ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID,
    FISH_AUDIO_API_KEY, FISH_AUDIO_VOICE_ID
)

# Forzar codificación UTF-8 en consola de Windows para evitar errores con tildes y emojis
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Inicializar Pygame Mixer para reproducción de audio
try:
    pygame.mixer.init()
except Exception as e:
    print(f"[!] Error inicializando pygame mixer: {e}")

# Inicializar motor pyttsx3 como respaldo offline
offline_engine = None
try:
    offline_engine = pyttsx3.init()
    # Buscar voz en español
    voices = offline_engine.getProperty("voices")
    spanish_voice = None
    for voice in voices:
        if "spanish" in voice.name.lower() or "sabina" in voice.name.lower() or "helena" in voice.name.lower():
            spanish_voice = voice.id
            break
    if spanish_voice:
        offline_engine.setProperty("voice", spanish_voice)
    offline_engine.setProperty("rate", 175)  # Velocidad natural
except Exception as e:
    print(f"[!] Aviso: No se pudo inicializar pyttsx3: {e}")


def play_audio_file(file_path: str, text: str = "", emotion: str = None):
    """Reproduce audio enviándolo al frontend de Electron para análisis de volumen en tiempo real (AnalyserNode),
    o mediante pygame si el overlay no está activo."""
    vts = None
    overlay = None
    try:
        from vts_bridge import get_vts_bridge
        vts = get_vts_bridge()
        if vts and vts.is_authenticated:
            vts.start_speaking_lip_sync()
    except Exception:
        pass

    try:
        from overlay_bridge import get_bridge
        overlay = get_bridge()
    except Exception:
        pass

    played_on_overlay = False
    try:
        if overlay and getattr(overlay, "clients", None):
            # Delegar reproducción al frontend (Opción A: sincronía perfecta con Web Audio AnalyserNode)
            played_on_overlay = overlay.send_audio(file_path, text=text, emotion=emotion, timeout=25.0)

        if not played_on_overlay:
            # Fallback en caso de que el overlay no esté conectado o no responda
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(15)
            pygame.mixer.music.unload()
    except Exception as e:
        print(f"[!] Error reproduciendo audio: {e}")
    finally:
        if vts and vts.is_authenticated:
            try:
                vts.stop_speaking_lip_sync()
            except Exception:
                pass
        if overlay and not played_on_overlay:
            try:
                overlay.send_speech_end()
            except Exception:
                pass


_fish_audio_disabled = False

def _synthesize_fish_audio(text: str, output_path: str, voice_id: str, api_key: str) -> bool:
    """Sintetiza la voz oficial de Yize usando la API de Fish Audio (Millie - Helluva Boss)."""
    global _fish_audio_disabled
    if _fish_audio_disabled or not api_key or not api_key.strip():
        return False

    import requests
    try:
        url = "https://api.fish.audio/v1/tts"
        headers = {
            "Authorization": f"Bearer {api_key.strip()}",
            "Content-Type": "application/json"
        }
        data = {
            "text": text,
            "reference_id": voice_id.strip() if voice_id else "74d956ea95a54ce5814084787b09d9d8",
            "format": "mp3"
        }
        res = requests.post(url, json=data, headers=headers, timeout=12)
        if res.status_code == 200 and len(res.content) > 100:
            with open(output_path, "wb") as f:
                f.write(res.content)
            return True
        else:
            print(f"[!] Fish Audio ({res.status_code}): {res.text[:120]}")
            if res.status_code in [401, 402, 429]:
                _fish_audio_disabled = True
                print("[!] API Key de Fish Audio no válida o sin créditos. Usando voz de respaldo.")
            return False
    except Exception as e:
        print(f"[!] Error de conexión con Fish Audio: {e}")
        return False


_elevenlabs_disabled = False

def _synthesize_elevenlabs(text: str, output_path: str, voice_id: str, api_key: str) -> bool:
    """Sintetiza voz hiperrealista usando la API oficial de ElevenLabs."""
    global _elevenlabs_disabled
    if _elevenlabs_disabled:
        return False

    import requests
    try:
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": api_key.strip()
        }
        data = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
                "style": 0.0,
                "use_speaker_boost": True
            }
        }
        res = requests.post(url, json=data, headers=headers, timeout=8)
        if res.status_code == 200:
            with open(output_path, "wb") as f:
                f.write(res.content)
            return True
        else:
            if res.status_code in [401, 429] or "quota" in res.text.lower():
                _elevenlabs_disabled = True
                print("[!] Cuota de ElevenLabs agotada. Usando Edge-TTS de alta definición.")
            else:
                print(f"[!] ElevenLabs error {res.status_code}: {res.text[:120]}")
            return False
    except Exception as e:
        print(f"[!] Error conectando con ElevenLabs: {e}")
        return False


async def _synthesize_edge_tts(text: str, output_path: str, voice: str, pitch: str = "+20Hz", rate: str = "+14%"):
    """Genera audio con Edge-TTS modulado en tono y ritmo para darle vida y energía a Yize."""
    communicate = edge_tts.Communicate(text, voice, pitch=pitch, rate=rate)
    await communicate.save(output_path)


def speak(text: str):
    """
    Sintetiza y reproduce voz en español.
    1. Fish Audio (Voz oficial de Yize de fish.audio/es/m/74d956ea95a54ce5814084787b09d9d8/).
    2. ElevenLabs (si está configurada).
    3. Edge-TTS (voz neuronal hiperrealista gratuita).
    4. pyttsx3 (respaldo offline).
    """
    # Extraer etiqueta de emoción si viene en formato [emotion]
    emotion = "happy"
    clean_text = text
    import re
    m = re.match(r"^\[([a-zA-Z_]+)\]\s*", text.strip())
    if m:
        emotion = m.group(1).lower()
        clean_text = text.strip()[m.end():].strip()

    print(f"🗣️ Asistente: {clean_text}")
    try:
        from overlay_bridge import get_bridge
        get_bridge().send_speech(clean_text, emotion)
    except Exception:
        pass

    text = clean_text  # Limpiar el texto para que el sintetizador de voz no lea "[smug]" en voz alta

    # 1. Intentar con Fish Audio (Voz oficial seleccionada para Yize)
    if (
        TTS_ENGINE.lower() == "fish"
        and not _fish_audio_disabled
        and FISH_AUDIO_API_KEY
        and FISH_AUDIO_API_KEY.strip() not in ["", "tu_api_key_aqui"]
    ):
        try:
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                temp_filename = tmp.name

            exito = _synthesize_fish_audio(text, temp_filename, FISH_AUDIO_VOICE_ID, FISH_AUDIO_API_KEY)
            if exito:
                play_audio_file(temp_filename, text=clean_text, emotion=emotion)
                try:
                    if os.path.exists(temp_filename):
                        os.remove(temp_filename)
                except Exception:
                    pass
                return
        except Exception as e:
            print(f"[!] Fallo en Fish Audio: {e}")

    # 2. Intentar con ElevenLabs si está configurado
    if (
        TTS_ENGINE.lower() == "elevenlabs"
        and not _elevenlabs_disabled
        and ELEVENLABS_API_KEY
        and ELEVENLABS_API_KEY.strip() not in ["", "tu_api_key_aqui"]
    ):
        try:
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                temp_filename = tmp.name

            exito = _synthesize_elevenlabs(text, temp_filename, ELEVENLABS_VOICE_ID, ELEVENLABS_API_KEY)
            if exito:
                play_audio_file(temp_filename, text=clean_text, emotion=emotion)
                try:
                    if os.path.exists(temp_filename):
                        os.remove(temp_filename)
                except Exception:
                    pass
                return
        except Exception as e:
            print(f"[!] ElevenLabs no disponible, cambiando a voz de respaldo: {e}")

    # 2. Respaldo gratuito con Edge-TTS (alta calidad neuronal de Microsoft)
    try:
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            temp_filename = tmp.name

        asyncio.run(_synthesize_edge_tts(text, temp_filename, EDGE_VOICE))
        play_audio_file(temp_filename, text=clean_text, emotion=emotion)

        try:
            if os.path.exists(temp_filename):
                os.remove(temp_filename)
        except Exception:
            pass
        return
    except Exception as e:
        pass

    # Fallback Offline
    if offline_engine:
        vts = None
        try:
            from vts_bridge import get_vts_bridge
            vts = get_vts_bridge()
            if vts and vts.is_authenticated:
                vts.start_speaking_lip_sync()
        except Exception:
            pass

        try:
            offline_engine.say(text)
            offline_engine.runAndWait()
        except Exception as e:
            print(f"[!] Error en pyttsx3: {e}")
        finally:
            if vts and vts.is_authenticated:
                try:
                    vts.stop_speaking_lip_sync()
                except Exception:
                    pass

def speak_async(text: str):
    """Sintetiza y reproduce voz en un hilo en segundo plano sin bloquear el llamador."""
    import threading
    t = threading.Thread(target=speak, args=(text,), daemon=True)
    t.start()
    return t


class VoiceRecognizer:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 450
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.dynamic_energy_adjustment_damping = 0.15
        self.recognizer.dynamic_energy_ratio = 1.4
        self.recognizer.pause_threshold = 0.5
        self.recognizer.phrase_threshold = 0.2
        self.recognizer.non_speaking_duration = 0.4
        self.microphone = None
        self.has_microphone = False

        # 1. Intentar el micrófono por defecto del sistema
        try:
            candidate = sr.Microphone()
            with candidate as source:
                pass
            self.microphone = candidate
            self.has_microphone = True
        except Exception:
            self.microphone = None

        # 2. Si falló el micrófono por defecto, escanear dispositivos de entrada
        if not self.has_microphone:
            try:
                import pyaudio
                p = pyaudio.PyAudio()
                input_indices = []
                for i in range(p.get_device_count()):
                    try:
                        dev_info = p.get_device_info_by_index(i)
                        if dev_info.get("maxInputChannels", 0) > 0:
                            name = dev_info.get("name", "").lower()
                            is_mic = any(k in name for k in ["mic", "micro", "headset", "auricular"])
                            input_indices.append((0 if is_mic else 1, i))
                    except Exception:
                        pass
                p.terminate()

                input_indices.sort(key=lambda x: x[0])
                for _, idx in input_indices:
                    try:
                        candidate = sr.Microphone(device_index=idx)
                        with candidate as source:
                            pass
                        self.microphone = candidate
                        self.has_microphone = True
                        break
                    except Exception:
                        continue
            except Exception as e:
                print(f"[!] Error buscando dispositivos de entrada: {e}")

        # Calibrar ruido ambiente inicial si hay micrófono disponible
        if self.has_microphone and self.microphone:
            print("🎙️ Calibrando micrófono con el ruido ambiente... (un segundo)")
            try:
                with self.microphone as source:
                    self.recognizer.adjust_for_ambient_noise(source, duration=0.8)
                # Limitar el umbral máximo para evitar ensordecer el micrófono
                if self.recognizer.energy_threshold > 750:
                    self.recognizer.energy_threshold = 550
                print(f"✅ Micrófono calibrado y listo (umbral: {int(self.recognizer.energy_threshold)}).")
            except Exception as e:
                print(f"[!] Advertencia al calibrar micrófono: {e}")
        else:
            self.microphone = None
            self.has_microphone = False
            print("[!] Aviso: No se detectó un micrófono de entrada activo.")
            print("    El asistente funcionará normalmente a través de texto y visión de pantalla.")

    def listen(self, timeout=None, phrase_time_limit=8) -> str:
        """
        Escucha el micrófono y convierte voz a texto en español.
        Retorna el texto en minúsculas o cadena vacía si no detecta nada.
        """
        if not self.has_microphone or not self.microphone:
            return ""

        try:
            with self.microphone as source:
                audio = self.recognizer.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=phrase_time_limit
                )
            
            # Reconocer texto mediante Google Speech Recognition (gratuito)
            texto = self.recognizer.recognize_google(audio, language=STT_LANGUAGE)
            return texto.strip().lower()

        except sr.WaitTimeoutError:
            return ""
        except sr.UnknownValueError:
            return ""
        except sr.RequestError as e:
            print(f"[!] Error de conexión con el servicio de reconocimiento: {e}")
            return ""
        except Exception as e:
            return ""
