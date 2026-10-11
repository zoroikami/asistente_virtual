"""
core/reminders.py - Sistema de Recordatorios con Escalada de Sarcasmo y Hábitos
Gestiona recordatorios puntuales y recurrentes (agua, postura, pausas de ojos)
con niveles crecientes de acidez si el usuario los ignora.
"""

import time
import json
import random
import threading
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Optional
from core.config import logger, BASE_DIR

REMINDERS_FILE = BASE_DIR / "data" / "recordatorios.json"

ESCALATION_DELAYS = [180, 180]  # Segundos entre nivel 1 -> nivel 2 y nivel 2 -> nivel 3 (3 min)

FRASES_NIVEL_1 = [
    "Oye, te recuerdo que tenías pendiente: {task}. Más vale que te pongas a ello.",
    "Recordatorio de servicio público (o lo más amable que puedo ser hoy): {task}.",
    "Hora de {task}. Deja de postergar tu existencia y hazlo.",
    "Atención: {task}. Te doy el beneficio de la duda de que no lo has olvidado.",
]

FRASES_NIVEL_2 = [
    "Segunda llamada para: {task}. ¿Sigo hablando sola o necesitas que te lo deletree?",
    "¿Sigues ahí o te desmayaste sobre el teclado? Te dije hace minutos: {task}.",
    "Ignorarme no va a hacer que {task} se haga solo, ¿sabes?",
    "Vuelvo a insistir: {task}. Me pregunto si tus oídos son solo de adorno.",
]

FRASES_NIVEL_3 = [
    "Nivel 3 de paciencia: {task}. Tu nivel de procrastinación ya es categoría olímpica.",
    "Último aviso para: {task}. Si no lo haces ahora, no te quejes cuando las cosas salgan mal.",
    "Si no vas a hacer {task}, al menos di 'ya lo hice' o 'cancela'. Mi paciencia no es infinita.",
    "¡{task}! Me estás obligando a sonar como tu madre y créeme que lo odio más que tú.",
]

FRASES_POSTURA = [
    "¡Esa espalda! Pareces un camarón hervido frente al monitor. Enderézate de inmediato.",
    "Detecto postura de signo de interrogación. Saca el pecho y alinea esa columna.",
    "Tu columna vertebral está pidiendo clemencia. Siéntate bien.",
]

FRASES_AGUA = [
    "Hidrátate. Tu cerebro funciona con agua, no solo con cafeína y frustración.",
    "Pausa para tomar agua. No quiero que te seques mientras me estás usando.",
    "Un trago de agua, por favor. Los humanos deshidratados rinden la mitad.",
]

FRASES_OJOS = [
    "Descanso de ojos 20-20-20. Mira a un punto lejano 20 segundos antes de que te quedes ciego.",
    "Parpadea un poco y aleja la vista de la pantalla. Pareces hipnotizado.",
]


@dataclass
class Reminder:
    id: str
    task: str
    target_time: float
    category: str = "general"       # "general", "postura", "agua", "ojos"
    interval_seconds: Optional[float] = None
    stage: int = 0                  # 0: pendiente, 1: avisado, 2: insistencia, 3: límite
    last_alert_time: float = 0.0
    acknowledged: bool = False


class ReminderManager:
    def __init__(self):
        self.reminders: List[Reminder] = []
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._load_from_disk()

    def _load_from_disk(self):
        try:
            if REMINDERS_FILE.exists():
                with open(REMINDERS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    now = time.time()
                    for item in data:
                        # Solo restaurar los que no estén completados hace más de 1 hora
                        if not item.get("acknowledged") or (now - item.get("last_alert_time", 0) < 3600):
                            self.reminders.append(Reminder(**item))
        except Exception as e:
            logger.debug(f"[Reminders] Error cargando recordatorios: {e}")

    def _save_to_disk(self):
        try:
            REMINDERS_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(REMINDERS_FILE, "w", encoding="utf-8") as f:
                json.dump([asdict(r) for r in self.reminders if not r.acknowledged or r.interval_seconds], f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.debug(f"[Reminders] Error guardando recordatorios: {e}")

    def add_reminder(self, task: str, delay_seconds: float, interval_seconds: Optional[float] = None, category: str = "general") -> str:
        with self._lock:
            rem_id = f"rem_{int(time.time())}_{len(self.reminders)}"
            target_time = time.time() + delay_seconds
            rem = Reminder(
                id=rem_id,
                task=task,
                target_time=target_time,
                category=category,
                interval_seconds=interval_seconds,
                stage=0,
                last_alert_time=0.0,
                acknowledged=False
            )
            self.reminders.append(rem)
            self._save_to_disk()

        minutos = round(delay_seconds / 60, 1)
        if minutos >= 1:
            tiempo_str = f"{minutos} minutos" if minutos != 1 else "1 minuto"
        else:
            tiempo_str = f"{int(delay_seconds)} segundos"

        return f"Anotado. Te recordaré '{task}' en {tiempo_str}."

    def add_habit(self, habit_type: str, interval_minutes: int = 45) -> str:
        """Activa hábitos periódicos: 'agua', 'postura', 'ojos'."""
        habit_type = habit_type.lower().strip()
        sec = interval_minutes * 60
        if "postura" in habit_type:
            return self.add_reminder("revisar tu postura", sec, interval_seconds=sec, category="postura")
        elif "agua" in habit_type or "hidrat" in habit_type:
            return self.add_reminder("tomar agua", sec, interval_seconds=sec, category="agua")
        elif "ojo" in habit_type or "vista" in habit_type:
            return self.add_reminder("descanso para los ojos", sec, interval_seconds=sec, category="ojos")
        else:
            return self.add_reminder(habit_type, sec, interval_seconds=sec, category="general")

    def acknowledge(self) -> str:
        """El usuario confirma que ya cumplió el recordatorio activo."""
        with self._lock:
            active_escalated = [r for r in self.reminders if r.stage > 0 and not r.acknowledged]
            if not active_escalated:
                return "No había ningún recordatorio reclamándote ahora mismo, pero me alegra tu entusiasmo."

            for r in active_escalated:
                r.acknowledged = True
                if r.interval_seconds:
                    # Reiniciar ciclo para el hábito
                    r.target_time = time.time() + r.interval_seconds
                    r.stage = 0
                    r.acknowledged = False
                    r.last_alert_time = 0.0

            self._save_to_disk()

        respuestas = [
            "Por fin. Pensé que me tocaría llamar a los bomberos.",
            "Bien hecho. Ves que no era tan difícil cumplir a la primera.",
            "Anotado. Tienes mi aprobación temporal... por los próximos 10 minutos.",
            "Excelente. Una tarea menos en tu lista de deudas con la vida.",
        ]
        return random.choice(respuestas)

    def cancel_all(self) -> str:
        with self._lock:
            count = len(self.reminders)
            self.reminders.clear()
            self._save_to_disk()
        return f"Listo, cancelados todos los recordatorios ({count} eliminados). Quedas libre de culpa."

    def list_active(self) -> str:
        with self._lock:
            now = time.time()
            activos = [r for r in self.reminders if not r.acknowledged]
            if not activos:
                return "No tienes recordatorios pendientes en este momento."

            lineas = []
            for r in activos:
                restante = max(0, int(r.target_time - now))
                minutos = restante // 60
                segundos = restante % 60
                tiempo = f"en {minutos}m {segundos}s" if restante > 0 else f"¡hace {abs(restante)}s!"
                rec = " (recurrente)" if r.interval_seconds else ""
                lineas.append(f"• {r.task} ({tiempo}){rec}")

            return "Tus recordatorios pendientes:\n" + "\n".join(lineas)

    def _trigger_alert(self, rem: Reminder, stage: int):
        rem.stage = stage
        rem.last_alert_time = time.time()
        self._save_to_disk()

        # Seleccionar frase según categoría y nivel de acidez
        if rem.category == "postura":
            frase = random.choice(FRASES_POSTURA)
        elif rem.category == "agua":
            frase = random.choice(FRASES_AGUA)
        elif rem.category == "ojos":
            frase = random.choice(FRASES_OJOS)
        else:
            if stage == 1:
                frase = random.choice(FRASES_NIVEL_1).format(task=rem.task)
            elif stage == 2:
                frase = random.choice(FRASES_NIVEL_2).format(task=rem.task)
            else:
                frase = random.choice(FRASES_NIVEL_3).format(task=rem.task)

        logger.info(f"⏰ [Recordatorio Nivel {stage}] {frase}")

        # Ejecutar alerta por voz y overlay en segundo plano
        def _speak():
            try:
                from core.voice import speak
                speak(frase)
            except Exception as e:
                logger.debug(f"[Reminders] Error emitiendo voz: {e}")

        threading.Thread(target=_speak, daemon=True).start()

    def _loop(self):
        while self._running:
            time.sleep(3)
            now = time.time()

            with self._lock:
                for rem in self.reminders:
                    if rem.acknowledged:
                        continue

                    # Nivel 1: Tiempo inicial cumplido
                    if rem.stage == 0 and now >= rem.target_time:
                        self._trigger_alert(rem, 1)

                    # Nivel 2: Ignorado durante ESCALATION_DELAYS[0]
                    elif rem.stage == 1 and (now - rem.last_alert_time >= ESCALATION_DELAYS[0]):
                        self._trigger_alert(rem, 2)

                    # Nivel 3: Ignorado durante ESCALATION_DELAYS[1] más
                    elif rem.stage == 2 and (now - rem.last_alert_time >= ESCALATION_DELAYS[1]):
                        self._trigger_alert(rem, 3)

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="Yize-Reminders")
        self._thread.start()
        logger.info("⏰ [Reminders] Centinela de recordatorios y hábitos activo")

    def stop(self):
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)


# Instancia singleton global
reminder_manager = ReminderManager()
