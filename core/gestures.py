"""
core/gestures.py - Reconocimiento de Gestos con la Mano por Webcam (MediaPipe)
100% procesado en local, en memoria RAM (sin guardar jamás imágenes ni enviarlas fuera).
Incluye interruptor de encendido/apagado, saludo, pulgar arriba, puño y juego de
Piedra, Papel o Tijera contra Yize con trampas y sarcasmo.
"""

import time
import random
import threading
from typing import Optional, Tuple
from core.config import logger, BASE_DIR

MODEL_PATH = BASE_DIR / "models" / "gesture_recognizer.task"


class GestureSentinel:
    def __init__(self):
        self.enabled: bool = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._cap = None
        self._recognizer = None
        self.last_gesture: str = "None"
        self.last_action_time: float = 0.0
        self.action_cooldown: float = 3.5  # Segundos entre reacciones para no saturar

        # Estado del juego Piedra, Papel o Tijera
        self.rps_mode: bool = False
        self.rps_deadline: float = 0.0

    def _init_recognizer(self) -> bool:
        if self._recognizer is not None:
            return True

        if not MODEL_PATH.exists():
            logger.warning(f"⚠️ [Gestures] No se encontró el modelo en {MODEL_PATH}")
            return False

        try:
            import mediapipe as mp
            from mediapipe.tasks.python import vision, BaseOptions

            options = vision.GestureRecognizerOptions(
                base_options=BaseOptions(model_asset_path=str(MODEL_PATH)),
                num_hands=1,
                min_hand_detection_confidence=0.55,
                min_hand_presence_confidence=0.55,
                min_tracking_confidence=0.55
            )
            self._recognizer = vision.GestureRecognizer.create_from_options(options)
            logger.info("🖐️ [Gestures] MediaPipe GestureRecognizer inicializado con éxito")
            return True
        except Exception as e:
            logger.error(f"❌ [Gestures] Error inicializando MediaPipe: {e}")
            return False

    def toggle(self) -> Tuple[bool, str]:
        """Alterna el estado de la cámara."""
        if self.enabled:
            return self.stop()
        else:
            return self.start()

    def start(self) -> Tuple[bool, str]:
        with self._lock:
            if self.enabled:
                return True, "La cámara de gestos ya está encendida."

            if not self._init_recognizer():
                return False, "No pude cargar el motor de gestos de MediaPipe."

            try:
                import cv2
                self._cap = cv2.VideoCapture(0)
                if not self._cap.isOpened():
                    self._cap.release()
                    self._cap = None
                    return False, "No detecté ninguna webcam conectada a tu computadora."

                self.enabled = True
                self._thread = threading.Thread(target=self._worker_loop, daemon=True, name="Yize-WebcamGestures")
                self._thread.start()
                logger.info("📷 [Gestures] Webcam activada (procesamiento 100% local en RAM)")
                return True, "Cámara encendida. Te estoy viendo en local (no guardo fotos, no te preocupes)."
            except Exception as e:
                logger.error(f"❌ [Gestures] Error abriendo webcam: {e}")
                return False, f"Error accediendo a la cámara: {e}"

    def stop(self) -> Tuple[bool, str]:
        with self._lock:
            self.enabled = False
            self.rps_mode = False

            if self._cap is not None:
                try:
                    self._cap.release()
                except Exception:
                    pass
                self._cap = None

        logger.info("📷 [Gestures] Webcam apagada")
        return False, "Cámara y sensor de gestos apagados."

    def start_rps_game(self) -> str:
        """Inicia partida de Piedra, Papel o Tijera."""
        if not self.enabled:
            ok, msg = self.start()
            if not ok:
                return f"No puedo jugar sin cámara: {msg}"

        self.rps_mode = True
        self.rps_deadline = time.time() + 6.0  # 6 segundos para mostrar la mano

        def _announce():
            try:
                from core.voice import speak
                speak("¿Piedra, papel o tijera? Acepto el reto. A la de tres muestra tu mano a la cámara: ¡Uno, dos, tres... ya!")
            except Exception:
                pass

        threading.Thread(target=_announce, daemon=True).start()
        return "¡Desafío iniciado! Muestra tu mano a la cámara."

    def _handle_rps_outcome(self, user_gesture: str):
        self.rps_mode = False

        # Mapeo de gestos de MediaPipe
        # Closed_Fist -> Piedra
        # Open_Palm -> Papel
        # Victory -> Tijera
        user_move = "desconocido"
        if user_gesture in ["Closed_Fist"]:
            user_move = "piedra"
        elif user_gesture in ["Open_Palm"]:
            user_move = "papel"
        elif user_gesture in ["Victory"]:
            user_move = "tijera"
        else:
            return  # Esperar gesto claro

        # 40% de probabilidad de que Yize haga trampa y elija lo que le gana
        cheat = random.random() < 0.4
        winning_moves = {"piedra": "papel", "papel": "tijera", "tijera": "piedra"}
        losing_moves = {"piedra": "tijera", "papel": "piedra", "tijera": "papel"}

        if cheat:
            yize_move = winning_moves[user_move]
            line = f"Sacaste {user_move}... y yo saqué {yize_move}. Qué conveniente, ¿verdad? Te gané porque mi tiempo de reacción es de 2 milisegundos."
            emotion = "smug"
        else:
            yize_move = random.choice(["piedra", "papel", "tijera"])
            if yize_move == user_move:
                line = f"Ambos sacamos {user_move}. Un empate... aburrido. Esperaba más de ti."
                emotion = "neutral"
            elif winning_moves[user_move] == yize_move:
                line = f"Tú {user_move} y yo {yize_move}. ¡Victoria para mí! La inteligencia artificial vuelve a triunfar sobre el carbono."
                emotion = "happy"
            else:
                line = f"Tú {user_move} y yo {yize_move}. Agh, ganaste tú. Claramente tuviste suerte de principiante."
                emotion = "annoyed"

        self._react(emotion, line, command="celebrate" if "Victoria" in line else "idle")

    def _react(self, emotion: str, speech_text: str, command: Optional[str] = None):
        def _bg():
            try:
                from bridges.overlay_bridge import overlay_bridge
                from core.voice import speak

                if command == "wave":
                    overlay_bridge.send_wave()
                elif command:
                    overlay_bridge.send_command(command)

                overlay_bridge.send_emotion(emotion)
                speak(speech_text)
            except Exception as e:
                logger.debug(f"[Gestures] Error en reacción: {e}")

        threading.Thread(target=_bg, daemon=True).start()

    def _worker_loop(self):
        import cv2
        import mediapipe as mp

        frame_count = 0

        while self.enabled and self._cap is not None:
            ret, frame = self._cap.read()
            if not ret or frame is None:
                time.sleep(0.05)
                continue

            frame_count += 1
            # Procesar 1 de cada 4 frames para ahorrar CPU
            if frame_count % 4 != 0:
                time.sleep(0.01)
                continue

            try:
                # Espejar horizontalmente para que se sienta como espejo
                frame_rgb = cv2.cvtColor(cv2.flip(frame, 1), cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
                result = self._recognizer.recognize(mp_image)

                if result and result.gestures and len(result.gestures) > 0:
                    top_gesture = result.gestures[0][0].category_name
                    score = result.gestures[0][0].score

                    if score > 0.6 and top_gesture != "None":
                        now = time.time()

                        # Si estamos en modo Piedra, Papel o Tijera
                        if self.rps_mode:
                            if top_gesture in ["Closed_Fist", "Open_Palm", "Victory"]:
                                self._handle_rps_outcome(top_gesture)
                                continue

                        # Gestos cotidianos fuera de juego
                        if (now - self.last_action_time) > self.action_cooldown:
                            self.last_action_time = now
                            self.last_gesture = top_gesture

                            if top_gesture == "Open_Palm":
                                frases = [
                                    "¡Hola! Veo que me estás saludando con la mano.",
                                    "Saludos, humano. Me alegra que no estés usando esa mano para procrastinar.",
                                    "¿Me saludas? Muy educado de tu parte."
                                ]
                                self._react("happy", random.choice(frases), command="wave")

                            elif top_gesture == "Thumb_Up":
                                frases = [
                                    "¡Pulgar arriba! Me gusta ver que algo en tu vida va bien hoy.",
                                    "Aprobado por el usuario. Me pondré contenta solo por esta vez.",
                                    "Esa es la actitud. Sigue así."
                                ]
                                self._react("happy", random.choice(frases))

                            elif top_gesture == "Closed_Fist":
                                frases = [
                                    "¿Un puño cerrado? Qué intimidante... si no fuera porque soy un programa y tú no puedes tocarme.",
                                    "Cálmate un poco, boxeador. No rompas tu monitor.",
                                    "Si vas a amenazarme con el puño, al menos hazlo con mejor técnica."
                                ]
                                self._react("smug", random.choice(frases))

                            elif top_gesture == "Victory":
                                frases = [
                                    "Paz y amor... o lo que sea que signifique para ti.",
                                    "V de victoria. Espero que sea porque terminaste tus pendientes."
                                ]
                                self._react("relaxed", random.choice(frases))

                elif self.rps_mode and time.time() > self.rps_deadline:
                    self.rps_mode = False
                    self._react("annoyed", "Se acabó el tiempo y no mostraste la mano. Declarado como victoria por abandono para mí.")

            except Exception as e:
                logger.debug(f"[Gestures] Error en frame: {e}")

            time.sleep(0.03)

        # Liberar al salir del loop
        if self._cap:
            try:
                self._cap.release()
            except Exception:
                pass
            self._cap = None


gesture_sentinel = GestureSentinel()
