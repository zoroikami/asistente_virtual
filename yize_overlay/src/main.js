import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { VRMLoaderPlugin, VRMUtils } from '@pixiv/three-vrm';
import { YizeAnimator } from './animator.js';
import { YizeSocket } from './socket.js';
import { YizeUI } from './ui.js';
import { VoicePlayer } from './voicePlayer.js';

// ─── Estado global ────────────────────────────────────────────────────────────
let currentVRM = null;
let animator = null;
let socket = null;
let voicePlayer = null;
const clock = new THREE.Clock();

// ─── Escena Three.js ─────────────────────────────────────────────────────────
const canvas = document.getElementById('vrm-canvas');
const renderer = new THREE.WebGLRenderer({
  canvas,
  alpha: true,
  antialias: true,
});
renderer.setPixelRatio(window.devicePixelRatio);
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setClearColor(0x000000, 0); // Transparente

const scene = new THREE.Scene();

const camera = new THREE.PerspectiveCamera(
  30,
  window.innerWidth / window.innerHeight,
  0.1,
  20
);
// Posición de cámara: encuadre de busto/cintura para arriba (estilo VTuber)
camera.position.set(0, 1.25, 1.55);
camera.lookAt(0, 1.25, 0);
scene.add(camera);

// Target de mirada para seguimiento del cursor (LookAt suave)
const lookAtTarget = new THREE.Object3D();
camera.add(lookAtTarget);
lookAtTarget.position.set(0, 0, -2);

/**
 * Actualiza el target de mirada a partir de coordenadas de ventana (px).
 * Si más adelante quieres seguir el cursor en toda la pantalla, envía desde
 * Electron la posición del cursor (screen.getCursorScreenPoint()) convertida
 * a coordenadas de ventana y llama a esta función.
 */
function setLookFromClient(clientX, clientY) {
  const normX = (clientX / window.innerWidth) * 2 - 1;
  const normY = -(clientY / window.innerHeight) * 2 + 1;
  lookAtTarget.position.x = normX * 1.25;
  lookAtTarget.position.y = normY * 1.25;
}

// ─── Zoom con la rueda del ratón (Scroll Wheel) ─────────────────────────────
window.addEventListener('wheel', (event) => {
  event.preventDefault();
  const delta = event.deltaY * -0.0015;
  // Limitar acercamiento / alejamiento
  camera.position.z = THREE.MathUtils.clamp(camera.position.z - delta, 0.9, 2.6);
}, { passive: false });

// ─── Arrastre de ventana (Drag) y toques (Poke) ──────────────────────────────
const DRAG_THRESHOLD = 5;      // px antes de considerar que es un arrastre
const POKE_DELAY_MS = 250;     // espera para distinguir clic simple de doble clic

let isMouseDown = false;
let dragging = false;
let originX = 0;
let originY = 0;
let pendingDragX = 0;
let pendingDragY = 0;
let dragFlushScheduled = false;
let pokeTimeout = null;

// Envía el delta acumulado de arrastre una sola vez por frame
function flushDrag() {
  dragFlushScheduled = false;
  if (pendingDragX === 0 && pendingDragY === 0) return;
  if (window.electronAPI?.dragWindow) {
    window.electronAPI.dragWindow(pendingDragX, pendingDragY);
  }
  pendingDragX = 0;
  pendingDragY = 0;
}

function scheduleDragFlush() {
  if (dragFlushScheduled) return;
  dragFlushScheduled = true;
  requestAnimationFrame(flushDrag);
}

function endPointerGesture() {
  isMouseDown = false;
  dragging = false;
  pendingDragX = 0;
  pendingDragY = 0;
}

window.addEventListener('pointerdown', (event) => {
  if (event.button !== 0) return; // Solo botón izquierdo
  isMouseDown = true;
  dragging = false;
  originX = event.screenX;
  originY = event.screenY;

  // Mantiene los eventos aunque el puntero salga de la ventana durante el arrastre
  try { canvas.setPointerCapture(event.pointerId); } catch (_) { }
});

// Un único listener de pointermove: mirada + arrastre
window.addEventListener('pointermove', (event) => {
  setLookFromClient(event.clientX, event.clientY);

  if (!isMouseDown) return;

  const dx = event.screenX - originX;
  const dy = event.screenY - originY;

  if (!dragging && Math.abs(dx) + Math.abs(dy) > DRAG_THRESHOLD) {
    dragging = true;
  }

  if (dragging) {
    pendingDragX += dx;
    pendingDragY += dy;
    originX = event.screenX;
    originY = event.screenY;
    scheduleDragFlush();
  }
});

window.addEventListener('pointerup', (event) => {
  if (!isMouseDown) return;
  const wasDrag = dragging;
  try { canvas.releasePointerCapture(event.pointerId); } catch (_) { }
  endPointerGesture();
  if (wasDrag) return;

  // Clic simple sin arrastrar -> Poke (con retraso para no chocar con el doble clic)
  clearTimeout(pokeTimeout);
  pokeTimeout = setTimeout(() => {
    if (animator) {
      animator.poke();
      YizeUI.showEmotion('surprised');
    }
    if (socket) socket.send({ type: 'poke' });
  }, POKE_DELAY_MS);
});

// Si el sistema cancela el gesto, no dejamos el drag pegado
window.addEventListener('pointercancel', endPointerGesture);

// Doble clic: saludar alegremente (cancela el poke pendiente)
window.addEventListener('dblclick', () => {
  clearTimeout(pokeTimeout);
  if (animator) animator.wave();
  if (socket) socket.send({ type: 'command', cmd: 'wave' });
});

// ─── Iluminación nítida y brillante estilo anime ─────────────────────────────
const ambientLight = new THREE.AmbientLight(0xffffff, 1.4);
scene.add(ambientLight);

const dirLight = new THREE.DirectionalLight(0xfff8f0, 1.5);
dirLight.position.set(0.5, 2, 2);
scene.add(dirLight);

const rimLight = new THREE.DirectionalLight(0xd4bbff, 0.7);
rimLight.position.set(-2, 2, -1);
scene.add(rimLight);

// ─── Cargar VRM ───────────────────────────────────────────────────────────────
const loader = new GLTFLoader();
loader.register((parser) => new VRMLoaderPlugin(parser));

const vrmUrl = new URL('./assets/Yize.vrm', window.location.href).href;
loader.load(
  vrmUrl,
  (gltf) => {
    const vrm = gltf.userData.vrm;
    VRMUtils.removeUnnecessaryVertices(gltf.scene);
    VRMUtils.combineSkeletons(gltf.scene);

    // Orientar hacia el frente: solo rota los modelos VRM 0.x (los 1.0 ya miran a +Z)
    VRMUtils.rotateVRM0(vrm);

    currentVRM = vrm;
    scene.add(vrm.scene);

    // Conectar seguimiento de ojos y mirada al cursor
    if (vrm.lookAt) {
      vrm.lookAt.target = lookAtTarget;
      vrm.lookAt.autoUpdate = true;
    }

    // Crear el animador procedural
    animator = new YizeAnimator(vrm);
    if (voicePlayer) {
      voicePlayer.setAnimator(animator);
    } else {
      voicePlayer = new VoicePlayer(animator);
      voicePlayer.onEnded = () => {
        if (socket) socket.send({ type: 'audio_done' });
      };
    }

    console.log('✨ Yize cargada correctamente con motor de gestos vivos');
    YizeUI.showBubble('¡Hola! Estoy aquí~ 💜', 'happy');
  },
  (progress) => {
    if (progress.total) {
      console.log(`Cargando Yize: ${Math.round((progress.loaded / progress.total) * 100)}%`);
    } else {
      console.log(`Cargando Yize: ${(progress.loaded / 1048576).toFixed(1)} MB`);
    }
  },
  (error) => {
    console.error('Error cargando VRM:', error);
    YizeUI.showBubble('Error al cargar mi modelo 😢 Verifica Yize.vrm');
  }
);

// ─── Resize handler ───────────────────────────────────────────────────────────
window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});

// ─── Loop de render ───────────────────────────────────────────────────────────
function animate() {
  requestAnimationFrame(animate);
  const delta = clock.getDelta();

  if (currentVRM) {
    // El animator va primero: así sus huesos y morphs se aplican en este mismo frame
    if (animator) animator.update(delta);
    currentVRM.update(delta);
  }

  renderer.render(scene, camera);
}
animate();

// ─── Seguridad: evitar que Yize se quede hablando para siempre ───────────────
const SPEECH_WATCHDOG_MS = 30000;
let speechWatchdog = null;

function armSpeechWatchdog() {
  clearTimeout(speechWatchdog);
  speechWatchdog = setTimeout(() => {
    if (voicePlayer) voicePlayer.stop();
    if (animator) animator.stopTalking();
  }, SPEECH_WATCHDOG_MS);
}

function stopSpeech() {
  clearTimeout(speechWatchdog);
  if (voicePlayer) voicePlayer.stop();
  if (animator) animator.stopTalking();
}

// ─── WebSocket con el backend Python ─────────────────────────────────────────
socket = new YizeSocket('ws://localhost:8765', {
  onClose: () => stopSpeech(),
  onMessage: (data) => {
    if (data.type === 'audio') {
      if (data.text) YizeUI.showBubble(data.text, data.emotion);
      if (data.emotion) {
        if (animator) animator.setEmotion(data.emotion);
        YizeUI.showEmotion(data.emotion);
      }
      if (!voicePlayer && animator) {
        voicePlayer = new VoicePlayer(animator);
        voicePlayer.onEnded = () => {
          if (socket) socket.send({ type: 'audio_done' });
        };
      }
      if (voicePlayer) {
        voicePlayer.play(data.data);
      }
      armSpeechWatchdog();
    }
    if (data.type === 'audio_stop') {
      stopSpeech();
    }
    if (data.type === 'speech') {
      YizeUI.showBubble(data.text, data.emotion);
      if (animator) {
        animator.startTalking();
        if (data.emotion) {
          animator.setEmotion(data.emotion);
          YizeUI.showEmotion(data.emotion);
        }
      }
      armSpeechWatchdog();
    }
    if (data.type === 'speech_end') {
      stopSpeech();
    }
    if (data.type === 'listen_start') {
      YizeUI.setStatus('escuchando', false);
    }
    if (data.type === 'emotion') {
      if (animator) animator.setEmotion(data.emotion);
      YizeUI.showEmotion(data.emotion);
    }
    if (data.type === 'set_pose') {
      if (animator) {
        if (data.pose === 'bored') animator.setBored();
        else if (data.pose === 'celebrate') animator.celebrate();
        else if (data.pose === 'yawn') animator.yawn();
        else if (data.pose === 'poke') animator.poke();
        else if (data.pose === 'wave') animator.wave();
        else animator.setEmotion(data.pose);
      }
    }
    if (data.type === 'move_window') {
      if (window.electronAPI?.moveWindow) {
        window.electronAPI.moveWindow(data.position);
      }
    }
    if (data.type === 'idle_thought') {
      YizeUI.showBubble(data.text, 'thinking');
      if (animator) animator.setEmotion('thinking');
    }
    if (data.type === 'wave') {
      if (animator) animator.wave();
    }
  }
});
socket.connect();

// Exponer para los botones de UI y depuración
window.yizeSocket = socket;
window.yizeAnimator = () => animator;
window.yizeVoice = () => voicePlayer;