import * as THREE from 'three';

/**
 * YizeAnimator v2 (VRM 1.0 / 0.x, huesos normalizados, el modelo mira hacia +Z)
 *
 * - Brazos con los ejes correctos (ver comentarios en APLICAR BRAZOS)
 * - Expresiones con objetivo + interpolación (sin saltos)
 * - Lip-sync por volumen real (AnalyserNode) o por energía enviada desde fuera
 * - Gestos al hablar en ráfagas, solo cuando hay voz
 * - Mirada con sacadas (vrm.lookAt), cabeza que sigue la mirada
 * - Peso corporal, respiración, dedos relajados, movimiento asimétrico
 * - Conserva acciones y poses extendidas: celebrate, yawn, poke, bored, sleepy
 *
 * Orden en el loop:  animator.update(delta);  vrm.update(delta);
 */

const clamp = (v, a, b) => Math.min(Math.max(v, a), b);
const rand = (a, b) => a + Math.random() * (b - a);
// Suavizado independiente del framerate
const damp = (cur, tgt, lambda, dt) => cur + (tgt - cur) * (1 - Math.exp(-lambda * dt));
// Ruido suave sin periodo evidente (suma de senos con frecuencias no múltiplas)
const noise = (t, seed = 0) =>
  (Math.sin(t + seed) + Math.sin(t * 2.3 + seed * 1.7) + Math.sin(t * 4.1 + seed * 0.3)) / 3;

const VOWELS = ['ih', 'ou', 'ee', 'oh'];
const EMO_NAMES = ['happy', 'sad', 'angry', 'surprised', 'relaxed'];

const EMOTION_MORPHS = {
  happy:     { happy: 0.9 },
  excited:   { happy: 1.0, surprised: 0.35 },
  thinking:  { relaxed: 0.75, surprised: 0.2 },
  surprised: { surprised: 0.95 },
  sad:       { sad: 0.75 },
  angry:     { angry: 0.85 },
  smug:      { happy: 0.55, relaxed: 0.35, angry: 0.2 },
  annoyed:   { angry: 0.7, sad: 0.25 },
  pout:      { angry: 0.6, surprised: 0.3 },
  tsundere:  { angry: 0.5, happy: 0.4 },
  bored:     { relaxed: 0.75, sad: 0.3 },
  celebrate: { happy: 1.0, surprised: 0.45 },
  yawn:      { relaxed: 0.85 },
  sleepy:    { relaxed: 0.9, sad: 0.2 },
};

const PERSISTENT_EMOTIONS = new Set(['bored', 'sleepy']);

const ALIAS = {
  excited: 'happy',
  annoyed: 'angry',
  pout: 'angry',
  tsundere: 'smug',
};

/**
 * Poses de brazo en "convención de brazo derecho"; el izquierdo se espeja solo.
 *   uz  : bajar el brazo (positivo = más abajo; 0 = horizontal, T-pose)
 *   ux  : swing adelante/atrás del brazo (negativo = adelante, igual en ambos lados)
 *   ly  : flexión del codo hacia adelante (positivo = más doblado)
 *   lz  : antebrazo en el plano frontal (negativo = hacia arriba, usado en el saludo)
 *   shz : hombro (negativo = sube)
 *   curl: cierre de los dedos (0 abierto, 1 puño)
 */
const REST_ARM = { uz: 1.2, ux: -0.05, ly: 0.2, lz: 0, shz: 0, curl: 0.3 };

const POSES = {
  neutral:   {},
  happy:     { both: { uz: 1.0, ux: -0.1, ly: 0.45, shz: -0.03 }, head: { x: 0.05 }, spine: { x: 0.02 } },
  surprised: { both: { uz: 0.95, ux: -0.15, ly: 0.6, shz: -0.05 }, head: { x: -0.05 }, spine: { x: -0.03 } },
  sad:       { both: { uz: 1.3, ux: 0.05, ly: 0.1, shz: 0.04, curl: 0.2 }, head: { x: 0.16 }, spine: { x: 0.05 } },
  angry:     { both: { uz: 1.3, ux: -0.05, ly: 0.55, shz: -0.08, curl: 0.9 }, head: { x: 0.1 }, spine: { x: 0.04 } },
  smug:      { both: { uz: 0.8, ux: 0.2, ly: 1.9, lz: 0.5, curl: 0.5 }, head: { x: -0.05, z: -0.12 }, holds: 'both' },
  thinking:  { r: { ux: -0.7, uz: 0.9, ly: 2.2, curl: 0.5 }, head: { x: -0.04, z: 0.1 }, holds: 'r' },
  wave:      { r: { uz: -0.2, ux: -0.15, ly: 0.3, lz: -1.3, shz: -0.1 }, head: { x: 0.04, z: -0.06 }, holds: 'r' },
  celebrate: { both: { uz: -0.3, ux: -0.3, ly: 0.6, lz: -0.5, shz: -0.15, curl: 0.2 }, head: { x: -0.12 }, spine: { x: -0.04 }, holds: 'both' },
  yawn:      { r: { ux: -0.6, uz: 0.7, ly: 2.3, curl: 0.4 }, head: { x: -0.15, z: 0.06 }, holds: 'r' },
  bored:     { both: { uz: 0.9, ux: 0.2, ly: 1.6, curl: 0.4 }, head: { x: 0.1, z: -0.15 }, spine: { x: 0.05 }, holds: 'both' },
  sleepy:    { both: { uz: 1.3, ux: 0.02, ly: 0.15, curl: 0.2 }, head: { x: 0.22, z: 0.08 }, spine: { x: 0.06 } },
};

/**
 * 10 Micro-comportamientos de Idle Largo para evitar bucles repetitivos:
 * Yize se estira, revisa su celular imaginario, bebe de una taza, se asoma curiosa,
 * cruza los brazos, apoya la barbilla, explora la pantalla, bosteza suavemente, etc.
 */
export const IDLE_BEHAVIORS = [
  {
    name: 'stretch',
    duration: 3.8,
    pose: {
      both: { uz: -0.15, ux: -0.2, ly: 0.3, lz: -0.4, shz: -0.12, curl: 0.1 },
      head: { x: -0.12, z: 0.05 },
      spine: { x: -0.06 }
    },
    desc: 'Estirarse con ambos brazos arriba'
  },
  {
    name: 'check_phone',
    duration: 5.2,
    pose: {
      l: { uz: 0.75, ux: -0.45, ly: 2.1, lz: 0.3, shz: -0.02, curl: 0.4 },
      r: { uz: 0.9, ux: -0.35, ly: 1.8, lz: -0.1, curl: 0.2 },
      head: { x: 0.22, y: -0.08, z: 0.05 },
      spine: { x: 0.04 }
    },
    desc: 'Mirar el celular con la cabeza inclinada'
  },
  {
    name: 'drink_tea',
    duration: 4.2,
    pose: {
      r: { uz: 0.65, ux: -0.5, ly: 2.3, lz: -0.2, shz: -0.04, curl: 0.5 },
      l: { uz: 1.25, ux: -0.05, ly: 0.2, lz: 0, curl: 0.3 },
      head: { x: -0.08, z: -0.04 },
      spine: { x: 0.02 }
    },
    desc: 'Beber de una taza imaginaria'
  },
  {
    name: 'curious_peek',
    duration: 4.5,
    pose: {
      both: { uz: 1.25, ux: 0.1, ly: 0.35, shz: 0.02, curl: 0.2 },
      head: { x: -0.08, z: -0.15 },
      spine: { x: 0.08, z: 0.04 }
    },
    desc: 'Inclinarse hacia adelante con curiosidad'
  },
  {
    name: 'cross_arms',
    duration: 5.5,
    pose: {
      both: { uz: 0.8, ux: 0.25, ly: 1.85, lz: 0.5, shz: -0.02, curl: 0.5 },
      head: { x: -0.04, z: -0.1 },
      spine: { x: -0.02 }
    },
    desc: 'Cruzar los brazos pensativa'
  },
  {
    name: 'chin_rest',
    duration: 5.0,
    pose: {
      r: { uz: 0.75, ux: -0.55, ly: 2.2, lz: -0.1, curl: 0.4 },
      l: { uz: 1.25, ux: 0.05, ly: 0.15, curl: 0.3 },
      head: { x: 0.08, z: 0.12 },
      spine: { x: 0.05 }
    },
    desc: 'Apoyar la barbilla en la mano'
  },
  {
    name: 'look_around',
    duration: 4.8,
    pose: {
      both: { uz: 1.2, ux: -0.05, ly: 0.2, lz: 0, curl: 0.3 },
      head: { x: 0.02, y: 0.35, z: 0.06 },
      spine: { y: 0.1 }
    },
    desc: 'Girar la cabeza explorando la pantalla'
  },
  {
    name: 'soft_yawn',
    duration: 3.8,
    pose: {
      r: { uz: 0.7, ux: -0.55, ly: 2.25, curl: 0.4 },
      head: { x: -0.14, z: 0.05 },
      spine: { x: -0.04 }
    },
    desc: 'Bostezo suave cubriéndose la boca'
  },
  {
    name: 'side_sway',
    duration: 4.2,
    pose: {
      both: { uz: 1.15, ux: -0.1, ly: 0.4, curl: 0.2 },
      head: { z: -0.14 },
      spine: { z: 0.08 }
    },
    desc: 'Balanceo juguetón de lado a lado'
  },
  {
    name: 'fidget_fingers',
    duration: 4.0,
    pose: {
      both: { uz: 1.05, ux: -0.2, ly: 0.8, lz: 0.1, curl: 0.1 },
      head: { x: 0.05, z: -0.04 },
      spine: { x: 0.02 }
    },
    desc: 'Juego de dedos y manos'
  }
];

export class YizeAnimator {
  constructor(vrm) {
    this.vrm = vrm;
    this.expressions = vrm.expressionManager;
    this.time = 0;

    // Habla
    this.isTalking = false;
    this.analyser = null;
    this._td = null;
    this.energyRaw = 0;      // se puede alimentar desde fuera con setEnergy()
    this.energy = 0;
    this.energySlow = 0;
    this.nod = 0;
    this.vowel = 'ih';
    this.vowelTimer = 0;
    this.vowelW = { ih: 0, ou: 0, ee: 0, oh: 0 };

    // Gestos en ráfagas
    this.gestureTimer = 0;
    this.gestureLife = 0;
    this.gestureDur = 0;
    this.gesture = 0;
    this.gestureArm = 'r';

    // Emoción
    this.currentEmotion = 'neutral';
    this.emotionTimer = 0;
    this.exprTarget = {};
    this.exprCurrent = {};

    // Animaciones especiales
    this.isWaving = false;
    this.waveTime = 0;
    this.wavePhase = 0;
    this.waveEnv = 0;

    this.isCelebrating = false;
    this.celebrateTimer = 0;

    this.isYawning = false;
    this.yawnTimer = 0;

    this.isPoked = false;
    this.pokeTimer = 0;
    this.pokeOffset = { x: 0, z: 0 };

    // Baile y ritmo musical
    this.isDancing = false;
    this.dance = 0;
    this.beatTracker = null;

    // Escucha activa
    this.isListeningActive = false;

    // Inactividad y micro-comportamientos de idle largo (10 estados orgánicos)
    this.idleSeconds = 0;
    this.idleRoutineTimer = rand(10, 18);
    this.activeIdleBehavior = null;
    this.activeIdleTime = 0;
    this.activeIdleDuration = 0;
    this.lastIdleIndex = -1;

    // Parpadeo
    this._blinkingActive = true;
    this.blinkTimer = this._nextBlinkTime();
    this.blinkState = 'open';
    this.blinkProgress = 0;
    this.lid = 0; // Párpado suavizado continuo (evita ojos atascados)

    // Peso corporal y fidgets
    this.sway = 0;
    this.swayTarget = 0;
    this.swayTimer = 6;
    this.fidgetTimer = 5;
    this.fidget = { x: 0, z: 0 };

    // Huesos
    this.bones = this._resolveBones();
    const hips = this.bones.hips;
    this.initialHips = hips
      ? { x: hips.position.x, y: hips.position.y, z: hips.position.z }
      : { x: 0, y: 0.9168, z: 0 };

    // Mirada (con altura dinámica de ojos: cabeza + 6 cm de margen en VRM)
    this.headHeight = 1.45;
    this.lookTarget = new THREE.Object3D();
    this.gazeGoal = new THREE.Vector3(0, 1.45, 1.0);
    this.gazeTimer = 1.5;
    this.recomputeHeadHeight();
    if (vrm.lookAt) vrm.lookAt.target = this.lookTarget;

    this.poseOverride = null; // para calibrar desde DevTools
  }

  /** Recalcula la altura de la mirada si el modelo es escalado o reposicionado */
  recomputeHeadHeight() {
    this.headHeight = 1.45;
    if (this.bones && this.bones.head) {
      const hp = new THREE.Vector3();
      this.bones.head.getWorldPosition(hp);
      // Los ojos se sitúan ~6 cm sobre el origen del hueso head en VRM
      if (hp.y > 0.5) this.headHeight = hp.y + 0.06;
    }
    if (this.lookTarget) this.lookTarget.position.y = this.headHeight;
    if (this.gazeGoal) this.gazeGoal.y = this.headHeight;
  }

  // ─── Huesos ────────────────────────────────────────────────────────────────
  _resolveBones() {
    if (!this.vrm || !this.vrm.humanoid) return {};
    const h = this.vrm.humanoid;
    const get = (n) => h.getNormalizedBoneNode(n);

    const fingerNames = ['Index', 'Middle', 'Ring', 'Little'];
    const fingers = { l: [], r: [] };
    for (const [k, side] of [['l', 'left'], ['r', 'right']]) {
      for (const f of fingerNames) {
        fingers[k].push([
          get(`${side}${f}Proximal`),
          get(`${side}${f}Intermediate`),
          get(`${side}${f}Distal`),
        ]);
      }
    }
    this.fingers = fingers;

    // Pulgares (metacarpal, proximal, distal)
    const thumbs = { l: [], r: [] };
    for (const [k, side] of [['l', 'left'], ['r', 'right']]) {
      thumbs[k] = [
        get(`${side}ThumbMetacarpal`),
        get(`${side}ThumbProximal`),
        get(`${side}ThumbDistal`),
      ];
    }
    this.thumbs = thumbs;

    this.arms = [
      { k: 'l', s: -1, shoulder: get('leftShoulder'),  upper: get('leftUpperArm'),  lower: get('leftLowerArm'),  hand: get('leftHand') },
      { k: 'r', s:  1, shoulder: get('rightShoulder'), upper: get('rightUpperArm'), lower: get('rightLowerArm'), hand: get('rightHand') },
    ];

    return {
      hips: get('hips'),
      spine: get('spine'),
      chest: get('chest') || get('upperChest'),
      neck: get('neck'),
      head: get('head'),
    };
  }

  // ─── API pública ───────────────────────────────────────────────────────────
  setAnalyser(analyser) {
    this.analyser = analyser;
    this._td = analyser ? new Uint8Array(analyser.fftSize) : null;
    this._freq = analyser ? new Uint8Array(analyser.frequencyBinCount) : null;
  }

  /** Alternativa si no hay AnalyserNode: energía 0..1 enviada desde fuera. */
  setEnergy(e) {
    this.energyRaw = clamp(e, 0, 1);
  }

  resetIdleTimer() {
    this.idleSeconds = 0;
    if (PERSISTENT_EMOTIONS.has(this.currentEmotion)) {
      this.setEmotion('neutral');
    }
  }

  startTalking() {
    this.resetIdleTimer();
    this.isTalking = true;
    this.isYawning = false;
    this.yawnTimer = 0;
    this.gestureTimer = 0.3;
  }

  stopTalking() {
    this.isTalking = false;
    this.energyRaw = 0;
  }

  wave() {
    this.resetIdleTimer();
    this.isWaving = true;
    this.waveTime = 0;
    this.wavePhase = 0;
  }

  celebrate() {
    this.resetIdleTimer();
    this.isCelebrating = true;
    this.celebrateTimer = 3.6;
    this.setEmotion('celebrate');
    this.emotionTimer = 3.6; // Sincronizado con la animación
  }

  yawn() {
    this.resetIdleTimer();
    this.isYawning = true;
    this.yawnTimer = 3.8;
    this.setEmotion('yawn');
    this.emotionTimer = 3.8; // Sincronizado con la animación
  }

  poke() {
    this.resetIdleTimer();
    this.isPoked = true;
    this.pokeTimer = 1.4;
    this.pokeOffset.x = 0.16;
    this.pokeOffset.z = (Math.random() - 0.5) * 0.25;
    this.setEmotion('surprised');
    this.emotionTimer = 1.4; // Sorpresa breve adecuada al toque
  }

  setBeatTracker(tracker) {
    this.beatTracker = tracker;
  }

  startDancing() {
    this.resetIdleTimer();
    this.isDancing = true;
    this.setEmotion('happy');
    this.emotionTimer = 999999;
  }

  stopDancing() {
    this.isDancing = false;
    this.dance = 0;
    if (this.currentEmotion === 'happy') {
      this.setEmotion('neutral');
    }
  }

  toggleDancing() {
    if (this.isDancing) this.stopDancing();
    else this.startDancing();
    return this.isDancing;
  }

  startListeningPose() {
    this.resetIdleTimer();
    this.isListeningActive = true;
    this.setEmotion('relaxed');
  }

  stopListeningPose() {
    this.isListeningActive = false;
    if (this.currentEmotion === 'relaxed') {
      this.setEmotion('neutral');
    }
  }

  setBored() {
    this.setEmotion('bored');
  }

  setEmotion(emotion) {
    this.currentEmotion = emotion || 'neutral';
    // Emoción desconocida o 'neutral' => cara neutra (no 'happy')
    this.exprTarget = { ...(EMOTION_MORPHS[this.currentEmotion] || {}) };
    this.emotionTimer =
      this.currentEmotion === 'neutral' || PERSISTENT_EMOTIONS.has(this.currentEmotion)
        ? 0
        : 5.5;
  }

  /** Calibración: animator.setPoseOverride({ r: { ux: -0.6 }, head: { x: 0.1 } }) */
  setPoseOverride(o) {
    this.poseOverride = o;
  }

  // Compatibilidad
  startBreathing() {}
  startBlinking() {}
  setupNaturalPose() {}

  // ─── Utilidades ────────────────────────────────────────────────────────────
  _set(name, v) {
    if (!this.expressions) return;
    try { this.expressions.setValue(name, v); } catch (_) {}
  }

  _nextBlinkTime() {
    return 2.5 + Math.random() * 4.0;
  }

  _readEnergy() {
    if (this.analyser && this._td) {
      this.analyser.getByteTimeDomainData(this._td);
      let sum = 0;
      for (let i = 0; i < this._td.length; i++) {
        const v = (this._td[i] - 128) / 128;
        sum += v * v;
      }
      const rms = Math.sqrt(sum / this._td.length);
      return clamp((rms - 0.02) * 4.5, 0, 1); // puerta de ruido + ganancia
    }
    return this.energyRaw;
  }

  // ─── Parpadeo ──────────────────────────────────────────────────────────────
  _updateBlink(dt) {
    if (!this._blinkingActive || !this.expressions) return;
    this.blinkTimer -= dt;

    if (this.blinkState === 'open' && this.blinkTimer <= 0) {
      this.blinkState = 'closing';
      this.blinkProgress = 0;
    }

    // Párpado base si está aburrida o con sueño
    const baseLid = this.currentEmotion === 'sleepy' ? 0.75 : (this.currentEmotion === 'bored' ? 0.35 : 0);

    // Con emociones fuertes el ojo no cierra del todo (evita peleas con happy/angry)
    const maxV = Math.max(0, 1 - 0.4 * Math.max(this.exprCurrent.happy || 0, this.exprCurrent.angry || 0) - baseLid);

    if (this.blinkState === 'closing') {
      this.blinkProgress += dt * 14;
      const v = Math.min(this.blinkProgress, 1);
      this.lid = baseLid + v * maxV;
      this._set('blink', this.lid);
      if (v >= 1) { this.blinkState = 'opening'; this.blinkProgress = 0; }
    } else if (this.blinkState === 'opening') {
      this.blinkProgress += dt * 10;
      const v = Math.max(1 - this.blinkProgress, 0);
      this.lid = baseLid + v * maxV;
      this._set('blink', this.lid);
      if (v <= 0) {
        this.blinkState = 'open';
        // 15% de las veces, doble parpadeo
        this.blinkTimer = Math.random() < 0.15 ? 0.15 : this._nextBlinkTime();
      }
    } else {
      // Suavizado continuo de párpados hacia baseLid (evita que queden atascados al salir de sleepy/bored)
      this.lid = damp(this.lid, baseLid, 5, dt);
      this._set('blink', this.lid);
    }
  }

  // ─── Expresiones ───────────────────────────────────────────────────────────
  _updateEmotion(dt) {
    if (this.currentEmotion !== 'neutral' && !PERSISTENT_EMOTIONS.has(this.currentEmotion) && this.emotionTimer > 0) {
      this.emotionTimer -= dt;
      if (this.emotionTimer <= 0) {
        this.currentEmotion = 'neutral';
        this.exprTarget = {};
      }
    }

    // Micro-expresión: la cara nunca queda completamente congelada
    const idle = 0.04 + 0.04 * (noise(this.time * 0.4, 7) + 1) * 0.5;

    for (const n of EMO_NAMES) {
      const prev = this.exprCurrent[n] ?? 0;
      const tgt = this.exprTarget[n] ?? 0;
      const cur = damp(prev, tgt, tgt > prev ? 8 : 4, dt); // entra rápido, sale lento
      this.exprCurrent[n] = cur;
      this._set(n, n === 'relaxed' ? clamp(cur + idle * (1 - cur), 0, 1) : cur);
    }
  }

  // ─── Mirada ────────────────────────────────────────────────────────────────
  _updateGaze(dt) {
    this.gazeTimer -= dt;
    const baseH = this.headHeight;
    if (this.gazeTimer <= 0) {
      this.gazeTimer = rand(1.2, 3.2);
      if (this.currentEmotion === 'thinking') {
        this.gazeGoal.set(rand(-0.6, -0.2), baseH + rand(0.2, 0.4), 1.0);
      } else if (this.currentEmotion === 'sleepy') {
        this.gazeGoal.set(rand(-0.1, 0.1), baseH - 0.15, 1.0);
      } else if (Math.random() < 0.75) {
        this.gazeGoal.set(rand(-0.15, 0.15), baseH + rand(-0.07, 0.07), 1.0); // hacia la cámara
      } else {
        this.gazeGoal.set(rand(-0.6, 0.6), baseH + rand(-0.2, 0.1), 1.0);     // aparta la vista
      }
    }
    const p = this.lookTarget.position;
    p.x = damp(p.x, this.gazeGoal.x, 14, dt);
    p.y = damp(p.y, this.gazeGoal.y, 14, dt);
    p.z = damp(p.z, this.gazeGoal.z, 14, dt);
  }

  // ─── Habla: boca, acentos y ráfagas de gesto ───────────────────────────────
  _updateSpeech(dt) {
    const raw = this.isTalking ? this._readEnergy() : 0;
    // ataque rápido, caída más lenta
    this.energy = damp(this.energy, raw, raw > this.energy ? 30 : 14, dt);
    this.energySlow = damp(this.energySlow, this.energy, 3, dt);

    // Boca: apertura por volumen, vocal secundaria por bandas espectrales o rotación
    const open = clamp(this.energy * 1.4, 0, 1);
    this.vowelTimer -= dt;
    if (this.vowelTimer <= 0) {
      this.vowelTimer = rand(0.07, 0.16);

      // Si tenemos datos espectrales de frecuencia (FFT), seleccionamos vocales por formantes
      if (this.analyser && this._freq && this.energy > 0.04) {
        this.analyser.getByteFrequencyData(this._freq);
        const sr = (this.analyser.context && this.analyser.context.sampleRate) || 48000;
        const binHz = sr / this.analyser.fftSize;
        const toBin = (hz) => clamp(Math.round(hz / binHz), 0, this._freq.length - 1);

        const b100 = toBin(100);
        const b500 = toBin(500);
        const b1500 = toBin(1500);
        const b3500 = toBin(3500);

        let low = 0, mid = 0, high = 0;
        for (let i = b100; i < b500; i++) low += this._freq[i];
        for (let i = b500; i < b1500; i++) mid += this._freq[i];
        for (let i = b1500; i < b3500; i++) high += this._freq[i];

        low /= Math.max(1, b500 - b100);
        mid /= Math.max(1, b1500 - b500);
        high /= Math.max(1, b3500 - b1500);

        if (high > mid && high > low) {
          this.vowel = Math.random() < 0.5 ? 'ee' : 'ih';
        } else if (low > mid && low > high) {
          this.vowel = Math.random() < 0.5 ? 'ou' : 'oh';
        } else {
          this.vowel = 'aa';
        }
      } else {
        this.vowel = VOWELS[(Math.random() * VOWELS.length) | 0];
      }
    }
    for (const v of VOWELS) {
      this.vowelW[v] = damp(this.vowelW[v], v === this.vowel ? 1 : 0, 18, dt);
    }

    if (this.isYawning) {
      // Apertura y cierre suave de la boca con envolvente senoidal
      const y = Math.sin(clamp(1 - this.yawnTimer / 3.8, 0, 1) * Math.PI);
      this._set('aa', y * 0.85);
      this._set('ih', 0);
      this._set('ee', 0);
      this._set('oh', 0);
      this._set('ou', 0);
    } else {
      // Síntesis fonética realista de visemas VRM:
      // Cada vocal tiene su propia morfología (labios estirados 'ih'/'ee', redondeados 'ou'/'oh', apertura 'aa')
      // evitando que 'aa' sature y borre las formas reales de boca.
      const aaWeight = (this.vowel === 'aa') ? 0.95 : (this.vowel === 'oh' ? 0.3 : (this.vowel === 'ee' ? 0.25 : 0.05));
      this._set('aa', open * aaWeight * (0.3 + 0.7 * (this.vowelW['aa'] || 0)));
      this._set('ih', open * 0.85 * (this.vowelW['ih'] || 0));
      this._set('ee', open * 0.85 * (this.vowelW['ee'] || 0));
      this._set('oh', open * 0.92 * (this.vowelW['oh'] || 0));
      this._set('ou', open * 0.92 * (this.vowelW['ou'] || 0));
    }

    // Acento de cabeza: golpe corto cuando el volumen sube de golpe
    const accent = clamp((this.energy - this.energySlow) * 2.5, 0, 1);
    this.nod = damp(this.nod, accent, 16, dt);

    // Ráfagas de gesto: solo mientras hay voz, con pausas entre una y otra
    this.gestureTimer -= dt;
    if (this.isTalking && this.gestureTimer <= 0 && this.energy > 0.1) {
      this.gestureTimer = rand(1.4, 3.5);
      this.gestureLife = 0;
      this.gestureDur = rand(0.8, 1.3);
      this.gestureArm = Math.random() < 0.7 ? 'r' : 'l';
    }
    if (this.gestureDur > 0) {
      this.gestureLife += dt;
      const p = this.gestureLife / this.gestureDur;
      if (p >= 1) { this.gestureDur = 0; this.gesture = 0; }
      else this.gesture = Math.sin(p * Math.PI); // 0 -> 1 -> 0
    }
  }

  // ─── Pose objetivo según emoción / saludo / acciones ───────────────────────
  _targetPose() {
    let key = 'neutral';
    if (this.isWaving) key = 'wave';
    else if (this.isCelebrating) key = 'celebrate';
    else if (this.isYawning) key = 'yawn';
    else key = ALIAS[this.currentEmotion] || this.currentEmotion;

    const P = POSES[key] || POSES.neutral;
    const l = { ...REST_ARM, ...(P.both || {}), ...(P.l || {}) };
    const r = { ...REST_ARM, ...(P.both || {}), ...(P.r || {}) };
    if (this.isWaving) r.lz += Math.sin(this.wavePhase) * 0.3 * this.waveEnv;

    const pose = {
      l, r,
      head: { x: 0, y: 0, z: 0, ...(P.head || {}) },
      spine: { x: 0, z: 0, ...(P.spine || {}) },
      holds: P.holds || null,
    };

    const o = this.poseOverride;
    if (o) {
      if (o.l) Object.assign(pose.l, o.l);
      if (o.r) Object.assign(pose.r, o.r);
      if (o.head) Object.assign(pose.head, o.head);
      if (o.spine) Object.assign(pose.spine, o.spine);
    }

    // ── Transición suave de micro-comportamiento de idle largo ──
    if (this.activeIdleBehavior) {
      const p = clamp(this.activeIdleTime / this.activeIdleDuration, 0, 1);
      const w = Math.sin(p * Math.PI); // Envolvente suave 0 -> 1 -> 0
      const ip = this.activeIdleBehavior.pose;
      if (ip.both) {
        for (const k in ip.both) {
          l[k] = (l[k] ?? REST_ARM[k]) * (1 - w) + ip.both[k] * w;
          r[k] = (r[k] ?? REST_ARM[k]) * (1 - w) + ip.both[k] * w;
        }
      }
      if (ip.l) {
        for (const k in ip.l) l[k] = (l[k] ?? REST_ARM[k]) * (1 - w) + ip.l[k] * w;
      }
      if (ip.r) {
        for (const k in ip.r) r[k] = (r[k] ?? REST_ARM[k]) * (1 - w) + ip.r[k] * w;
      }
      if (ip.head) {
        if (ip.head.x !== undefined) pose.head.x += ip.head.x * w;
        if (ip.head.y !== undefined) pose.head.y += ip.head.y * w;
        if (ip.head.z !== undefined) pose.head.z += ip.head.z * w;
      }
      if (ip.spine) {
        if (ip.spine.x !== undefined) pose.spine.x += ip.spine.x * w;
        if (ip.spine.y !== undefined) pose.spine.y += ip.spine.y * w;
        if (ip.spine.z !== undefined) pose.spine.z += ip.spine.z * w;
      }
    }

    return pose;
  }

  _holds(pose, k) {
    return pose.holds === 'both' || pose.holds === k;
  }

  // ─── Bucle principal ───────────────────────────────────────────────────────
  update(delta) {
    const dt = Math.min(delta, 0.1); // evita saltos al volver de una pestaña en pausa
    this.time += dt;

    if (this.isTalking || this.isDancing || this.isWaving || this.isCelebrating || this.isPoked || this.isListeningActive) {
      this.idleSeconds = 0; // Mientras interactúa se reinicia la inactividad
      this.activeIdleBehavior = null;
      this.idleRoutineTimer = rand(10, 18);
    } else {
      this.idleSeconds += dt;
      if (!this.activeIdleBehavior) {
        this.idleRoutineTimer -= dt;
        if (this.idleRoutineTimer <= 0) {
          let idx;
          do {
            idx = (Math.random() * IDLE_BEHAVIORS.length) | 0;
          } while (idx === this.lastIdleIndex && IDLE_BEHAVIORS.length > 1);
          this.lastIdleIndex = idx;
          this.activeIdleBehavior = IDLE_BEHAVIORS[idx];
          this.activeIdleTime = 0;
          this.activeIdleDuration = this.activeIdleBehavior.duration;
          this.idleRoutineTimer = rand(14, 25);
        }
      } else {
        this.activeIdleTime += dt;
        if (this.activeIdleTime >= this.activeIdleDuration) {
          this.activeIdleBehavior = null;
        }
      }

      // Inactividad natural secundaria tras mucho tiempo inactiva
      if (!this.isWaving && !this.isCelebrating && !this.isYawning) {
        if (this.idleSeconds > 80 && this.currentEmotion !== 'sleepy') {
          this.setEmotion('sleepy');
        } else if (this.idleSeconds > 35 && this.currentEmotion === 'neutral') {
          this.setEmotion('bored');
        }
      }
    }

    if (this.isWaving) {
      this.waveTime += dt;
      this.wavePhase += dt * 11;
      this.waveEnv = clamp(Math.min(this.waveTime / 0.3, (2.8 - this.waveTime) / 0.3), 0, 1);
      if (this.waveTime >= 2.8) this.isWaving = false;
    }

    if (this.isCelebrating) {
      this.celebrateTimer -= dt;
      if (this.celebrateTimer <= 0) this.isCelebrating = false;
    }

    if (this.isYawning) {
      this.yawnTimer -= dt;
      if (this.yawnTimer <= 0) this.isYawning = false;
    }

    if (this.isPoked) {
      this.pokeTimer -= dt;
      if (this.pokeTimer <= 0) this.isPoked = false;
    }
    this.pokeOffset.x = damp(this.pokeOffset.x, 0, 6, dt);
    this.pokeOffset.z = damp(this.pokeOffset.z, 0, 6, dt);

    this._updateBlink(dt);
    this._updateEmotion(dt);
    this._updateGaze(dt);
    this._updateSpeech(dt);
    this._updateBody(dt);
  }

  _updateBody(dt) {
    const b = this.bones;
    if (!b || !b.head) return;
    const t = this.time;
    const talking = this.isTalking;
    const breath = Math.sin(t * 1.3);

    // Cambio de peso cada 6-10 s
    this.swayTimer -= dt;
    if (this.swayTimer <= 0) {
      this.swayTimer = rand(6, 10);
      this.swayTarget = (Math.random() * 2 - 1) * 0.8;
    }
    this.sway = damp(this.sway, this.swayTarget, 1.2, dt);

    // Fidget de cabeza
    this.fidgetTimer -= dt;
    if (this.fidgetTimer <= 0) {
      this.fidgetTimer = rand(4, 9);
      this.fidget.x = rand(-0.04, 0.04);
      this.fidget.z = rand(-0.05, 0.05);
    }

    const pose = this._targetPose();

    // ── Baile sincronizado con el tempo de la música ──
    const beat = this.beatTracker;
    const canDance = this.isDancing && beat && beat.active && !talking;
    const targetDance = canDance ? clamp(0.4 + (beat.level || 0) * 2, 0, 1) : 0;
    this.dance = damp(this.dance, targetDance, 3, dt);
    const d = this.dance;

    let danceHeadX = 0;
    let danceHipsY = 0;
    let danceHipsZ = 0;
    let dancePh = 0;
    let danceHit = 0;

    if (d > 0.01 && beat) {
      dancePh = (beat.phase || 0) * Math.PI * 2;
      danceHit = Math.pow(0.5 + 0.5 * Math.cos(dancePh), 2); // pico en el beat
      const side = Math.sin(dancePh / 2);                   // un ciclo cada 2 beats

      danceHeadX = d * (0.06 * danceHit + 0.03 * (beat.pulse || 0)); // cabeceo: baja en el golpe
      danceHipsY = -d * 0.02 * danceHit;                             // rebote de caderas
      danceHipsZ = d * 0.06 * side;                                  // balanceo lateral
    }

    // ── Cabeza y cuello (la cabeza sigue la mirada + offset de poke + baile + escucha activa) ──
    const gaze = this.lookTarget.position;
    const gazeYaw = clamp(gaze.x * 0.25, -0.3, 0.3);          // +x del modelo = su izquierda
    const gazePitch = -(gaze.y - this.headHeight) * 0.5;       // relativo a la altura real de la cabeza

    // Escucha activa: ladeo y micro-asentimientos curiosos
    const listenHeadX = (this.isListeningActive && !talking) ? (0.04 + Math.sin(t * 3.2) * 0.02) : 0;
    const listenHeadZ = (this.isListeningActive && !talking) ? -0.06 : 0;

    const headX = pose.head.x + this.fidget.x + this.pokeOffset.x + gazePitch + this.nod * 0.12
      + (talking ? noise(t * 3, 1) * 0.03 : 0) + breath * 0.01 + danceHeadX + listenHeadX;
    const headY = pose.head.y + gazeYaw + (talking ? noise(t * 2.2, 5) * 0.05 : 0);
    const headZ = pose.head.z + this.fidget.z + this.pokeOffset.z - this.sway * 0.02
      + (talking ? noise(t * 1.7, 9) * 0.04 : 0) + listenHeadZ;

    b.head.rotation.x = damp(b.head.rotation.x, headX, 7, dt);
    b.head.rotation.y = damp(b.head.rotation.y, headY, 7, dt);
    b.head.rotation.z = damp(b.head.rotation.z, headZ, 7, dt);

    if (b.neck) { // el cuello llega un poco después que la cabeza (follow-through)
      b.neck.rotation.x = damp(b.neck.rotation.x, headX * 0.4, 5, dt);
      b.neck.rotation.y = damp(b.neck.rotation.y, headY * 0.4, 5, dt);
      b.neck.rotation.z = damp(b.neck.rotation.z, headZ * 0.4, 5, dt);
    }

    // ── Columna, pecho, caderas ──
    const celebrateBounce = this.isCelebrating ? Math.sin(t * 12) * 0.02 : 0;
    if (b.spine) {
      const sx = pose.spine.x + (talking ? 0.03 : 0) + breath * 0.015;
      const sy = noise(t * 0.3, 3) * 0.03 + headY * 0.15;
      const sz = pose.spine.z + noise(t * 0.35, 2) * 0.02 - this.sway * 0.02;
      b.spine.rotation.x = damp(b.spine.rotation.x, sx, 4, dt);
      b.spine.rotation.y = damp(b.spine.rotation.y, sy, 4, dt);
      b.spine.rotation.z = damp(b.spine.rotation.z, sz, 4, dt);
    }
    if (b.chest) {
      b.chest.rotation.x = damp(b.chest.rotation.x, breath * 0.025, 3.5, dt);
    }
    if (b.hips) {
      b.hips.position.y = damp(b.hips.position.y, this.initialHips.y + breath * 0.004 + celebrateBounce + danceHipsY, 4, dt);
      b.hips.position.x = damp(b.hips.position.x, this.initialHips.x + this.sway * 0.015, 3, dt);
      b.hips.rotation.z = damp(b.hips.rotation.z, this.sway * 0.03 + danceHipsZ, 3, dt);
    }

    // ── Brazos ──
    // APLICAR BRAZOS:
    //   upper.z  baja/sube el brazo      (izq. negativo, der. positivo para bajarlo)
    //   upper.x  lo balancea adelante (negativo) o atrás (positivo)
    //   lower.y  dobla el codo hacia adelante (izq. negativo, der. positivo)
    //   lower.z  mueve el antebrazo en el plano frontal (saludo)
    const gest = this.gesture;
    const lHolds = this._holds(pose, 'l');
    const rHolds = this._holds(pose, 'r');

    for (const arm of this.arms) {
      const A = pose[arm.k];
      const s = arm.s;
      const seed = s > 0 ? 0 : 1.9; // desfase para que no sean idénticos

      // Gesto al hablar
      if (talking && gest > 0 && !this._holds(pose, arm.k)) {
        const otherHolds = arm.k === 'l' ? rHolds : lHolds;
        const amt = (this.gestureArm === arm.k || otherHolds) ? gest : gest * 0.25;
        A.ux -= 0.35 * amt;
        A.uz -= 0.3 * amt;
        A.ly += 0.9 * amt;
      }

      // Micro-movimiento y respiración
      A.uz += breath * 0.015 + noise(t * 0.5, seed) * 0.03;
      A.ux += noise(t * 0.4, seed + 4) * 0.02;
      A.ly += noise(t * 0.45, seed + 8) * 0.04;

      // Modificador de baile rítmico en brazos
      if (d > 0.01) {
        A.uz -= d * 0.25;                                     // brazos algo levantados
        A.ux += d * 0.3 * Math.sin(dancePh / 2 + (arm.k === 'l' ? Math.PI : 0)); // se alternan
        A.ly += d * 0.5 * danceHit;                           // codos doblados al ritmo
      }
      // El hombro acompaña cuando el brazo sube
      A.shz -= Math.max(0, REST_ARM.uz - A.uz) * 0.12;

      if (arm.shoulder) {
        arm.shoulder.rotation.z = damp(arm.shoulder.rotation.z, s * A.shz, 5, dt);
      }
      if (arm.upper) {
        arm.upper.rotation.z = damp(arm.upper.rotation.z, s * A.uz, 5, dt);
        arm.upper.rotation.x = damp(arm.upper.rotation.x, A.ux, 5, dt);
      }
      if (arm.lower) {
        arm.lower.rotation.y = damp(arm.lower.rotation.y, s * A.ly, 6, dt);
        arm.lower.rotation.z = damp(arm.lower.rotation.z, s * A.lz, 6, dt);
      }

      // Dedos relajados (curvatura creciente hacia el meñique)
      const fk = [0.7, 0.9, 1.0, 1.1];
      const f = this.fingers[arm.k];
      for (let i = 0; i < f.length; i++) {
        const [p, m, d] = f[i];
        const c = A.curl * fk[i];
        if (p) p.rotation.z = damp(p.rotation.z, s * c * 0.7, 6, dt);
        if (m) m.rotation.z = damp(m.rotation.z, s * c * 0.9, 6, dt);
        if (d) d.rotation.z = damp(d.rotation.z, s * c * 0.6, 6, dt);
      }

      // Pulgar acompañando la curvatura y pose (aducción en Y y flexión en Z suave)
      const th = this.thumbs ? this.thumbs[arm.k] : null;
      if (th) {
        const [m, p, d] = th;
        const tc = A.curl * 0.45; // Curvatura moderada para no distorsionar la malla
        if (m) {
          m.rotation.y = damp(m.rotation.y, s * tc * 0.4, 6, dt);
          m.rotation.z = damp(m.rotation.z, s * tc * 0.2, 6, dt);
        }
        if (p) {
          p.rotation.y = damp(p.rotation.y, s * tc * 0.45, 6, dt);
          p.rotation.z = damp(p.rotation.z, s * tc * 0.25, 6, dt);
        }
        if (d) {
          d.rotation.y = damp(d.rotation.y, s * tc * 0.4, 6, dt);
          d.rotation.z = damp(d.rotation.z, s * tc * 0.2, 6, dt);
        }
      }
    }
  }
}