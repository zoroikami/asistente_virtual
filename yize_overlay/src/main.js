import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { VRMLoaderPlugin, VRMUtils } from '@pixiv/three-vrm';
import { YizeAnimator } from './animator.js';
import { YizeSocket } from './socket.js';
import { YizeUI } from './ui.js';
import { VoicePlayer } from './voicePlayer.js';
import { MusicListener } from './musicListener.js';
import { YizeCalibrator } from './calibrator.js';
import { VRMAPlayer } from './vrmaPlayer.js';
import { ModelSwitcher } from './modelSwitcher.js';

// ─── Estado global ────────────────────────────────────────────────────────────
let currentVRM = null;
let animator = null;
let vrmaPlayer = null;
let modelSwitcher = null;
let isPrivacyMuted = false;
let socket = null;
let voicePlayer = null;
let musicListener = null;
let calibrator = null;
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

// ─── Seguimiento global del cursor y sacudida de mouse (Mouse Shake) ────────
if (window.electronAPI?.onGlobalCursor) {
  window.electronAPI.onGlobalCursor((data) => {
    if (!dragging && !isMouseDown) {
      const cx = THREE.MathUtils.clamp(data.normX * 1.3, -2.8, 2.8);
      const cy = THREE.MathUtils.clamp(data.normY * 1.3, -2.5, 2.5);
      lookAtTarget.position.x = cx;
      lookAtTarget.position.y = cy;
    }
  });
}

let lastShakeClientTime = 0;
if (window.electronAPI?.onCursorShake) {
  window.electronAPI.onCursorShake(() => {
    const now = Date.now();
    if (now - lastShakeClientTime < 12000) return;
    lastShakeClientTime = now;
    if (animator && !animator.isTalking) {
      animator.poke();
      animator.setEmotion('surprised');
      YizeUI.showBubble('¡Oye! ¡No sacudas el mouse así que me mareo! 😵💫', 'surprised');
      if (socket) socket.send({ type: 'command', cmd: 'shake' });
    }
  });
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

  // Inercia física de pelo y ropa (Three-VRM Spring Bones):
  // Desplazar la escena en sentido inverso para que la física elástica sienta aceleración
  if (currentVRM && currentVRM.scene) {
    currentVRM.scene.position.x = THREE.MathUtils.clamp(
      currentVRM.scene.position.x - pendingDragX * 0.0025,
      -0.25,
      0.25
    );
    currentVRM.scene.position.y = THREE.MathUtils.clamp(
      currentVRM.scene.position.y + pendingDragY * 0.0025,
      -0.25,
      0.25
    );
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

function loadVRMModel(url, modelName = 'Yize.vrm') {
  if (currentVRM) {
    scene.remove(currentVRM.scene);
    VRMUtils.deepDispose(currentVRM.scene);
    currentVRM = null;
  }

  loader.load(
    url,
    (gltf) => {
      const vrm = gltf.userData.vrm;
      VRMUtils.removeUnnecessaryVertices(gltf.scene);
      VRMUtils.combineSkeletons(gltf.scene);
      VRMUtils.rotateVRM0(vrm);

      currentVRM = vrm;
      scene.add(vrm.scene);

      if (vrm.lookAt) {
        vrm.lookAt.target = lookAtTarget;
        vrm.lookAt.autoUpdate = true;
      }

      animator = new YizeAnimator(vrm);
      vrmaPlayer = new VRMAPlayer(vrm);
      calibrator = new YizeCalibrator(animator);
      if (!musicListener) musicListener = new MusicListener(animator);
      else musicListener.animator = animator;
      musicListener.init().catch(() => {});

      if (voicePlayer) {
        voicePlayer.setAnimator(animator);
      } else {
        voicePlayer = new VoicePlayer(animator);
        voicePlayer.onEnded = () => {
          if (socket) socket.send({ type: 'audio_done' });
        };
      }

      console.log(`✨ Modelo '${modelName}' cargado exitosamente.`);
      YizeUI.showBubble(`¡Avatar ${modelName} listo! 💜`, 'happy');
    },
    (progress) => {
      if (progress.total) {
        console.log(`Cargando VRM: ${Math.round((progress.loaded / progress.total) * 100)}%`);
      }
    },
    (error) => {
      console.error('Error cargando VRM:', error);
      YizeUI.showBubble(`Error al cargar ${modelName} 😢`, 'annoyed');
    }
  );
}

// Cargar modelo inicial
const initialVrmUrl = new URL('./assets/Yize.vrm', window.location.href).href;
loadVRMModel(initialVrmUrl, 'Yize.vrm');

// Inicializar ModelSwitcher (F3 / Ctrl+Shift+M)
modelSwitcher = new ModelSwitcher(
  (newUrl, name) => loadVRMModel(newUrl, name),
  () => {
    if (socket) socket.send({ type: 'command', cmd: 'switch_to_vts' });
    YizeUI.showBubble('Conectando con Live2D (VTube Studio)... 🎭', 'happy');
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

  if (musicListener) musicListener.update(delta);

  if (currentVRM) {
    // Restaurar el desplazamiento con amortiguación elástica (inercia de spring bones)
    if (currentVRM.scene) {
      currentVRM.scene.position.x += (0 - currentVRM.scene.position.x) * (1 - Math.exp(-7 * delta));
      currentVRM.scene.position.y += (0 - currentVRM.scene.position.y) * (1 - Math.exp(-7 * delta));
    }

    // El animator va primero: así sus huesos y morphs se aplican en este mismo frame
    if (animator) animator.update(delta);
    if (vrmaPlayer && vrmaPlayer.isPlaying) vrmaPlayer.update(delta);
    currentVRM.update(delta);
  }

  renderer.render(scene, camera);
}
animate();

// ─── Botón de Privacidad / Mute Total ───────────────────────────────────────
const muteBtn = document.getElementById('privacy-mute-btn');
if (muteBtn) {
  muteBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    isPrivacyMuted = !isPrivacyMuted;
    muteBtn.classList.toggle('active', isPrivacyMuted);
    if (isPrivacyMuted) {
      YizeUI.setPrivacy('muted');
      if (voicePlayer) voicePlayer.stop();
      if (animator) animator.stopTalking();
      if (socket) socket.send({ type: 'privacy_mute', active: true });
    } else {
      YizeUI.setPrivacy('idle');
      if (socket) socket.send({ type: 'privacy_mute', active: false });
    }
  });
}

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
    if (data.type === 'privacy_status') {
      if (!isPrivacyMuted) YizeUI.setPrivacy(data.mode || 'idle');
    }
    if (data.type === 'listen_start') {
      if (!isPrivacyMuted) YizeUI.setPrivacy('mic');
      YizeUI.setStatus('escuchando', false);
      if (animator) animator.startListeningPose();
    }
    if (data.type === 'listen_end' || data.type === 'listen_stop') {
      if (!isPrivacyMuted) YizeUI.setPrivacy('idle');
      if (animator) animator.stopListeningPose();
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
    if (data.type === 'window_dnd') {
      if (data.active) {
        if (window.electronAPI?.moveWindow) window.electronAPI.moveWindow('minimize');
      } else {
        if (window.electronAPI?.moveWindow) window.electronAPI.moveWindow('bottom_right');
        if (animator) animator.wave();
      }
    }
    if (data.type === 'idle_thought') {
      YizeUI.showBubble(data.text, 'thinking');
      if (animator) animator.setEmotion('thinking');
    }
    if (data.type === 'dance') {
      if (animator) {
        if (data.action === 'start') {
          if (musicListener) {
            musicListener.init().then(() => animator.startDancing()).catch(() => animator.startDancing());
          } else {
            animator.startDancing();
          }
        } else if (data.action === 'stop') {
          animator.stopDancing();
        } else {
          if (animator.isDancing) {
            animator.stopDancing();
          } else {
            if (musicListener) {
              musicListener.init().then(() => animator.startDancing()).catch(() => animator.startDancing());
            } else {
              animator.startDancing();
            }
          }
        }
      }
    }
    if (data.type === 'wave') {
      if (animator) animator.wave();
    }
    if (data.type === 'show_screen_target') {
      if (window.electronAPI?.showScreenGuide) {
        window.electronAPI.showScreenGuide({
          x: data.x,
          y: data.y,
          label: data.label || 'Elemento'
        });
      }
      if (animator) {
        animator.setEmotion('surprised');
      }
      YizeUI.showBubble(`🎯 ¡Aquí está: ${data.label}!`, 'happy');
    }
  }
});
socket.connect();

// Exponer para los botones de UI y depuración
window.yizeSocket = socket;
window.yizeAnimator = () => animator;
window.yizeVoice = () => voicePlayer;
window.yizeMusic = () => musicListener;
window.yizeCalibrator = () => calibrator;
window.toggleCalibrator = () => calibrator?.toggle();
window.toggleDance = () => {
  if (animator) {
    if (animator.isDancing) {
      animator.stopDancing();
    } else {
      if (musicListener) musicListener.init().then(() => animator.startDancing()).catch(() => animator.startDancing());
      else animator.startDancing();
    }
  }
};

// ─── Atajo de teclado: F2 para abrir el Calibrador ──────────────────────────
window.addEventListener('keydown', (e) => {
  if (e.key === 'F2' || (e.ctrlKey && e.shiftKey && e.key.toLowerCase() === 'c')) {
    e.preventDefault();
    if (calibrator) calibrator.toggle();
  }
});

// ─── Arrastrar y soltar archivos sobre Yize (Drag & Drop) ────────────────────
window.addEventListener('dragover', (e) => {
  e.preventDefault();
  e.stopPropagation();
  if (animator && !animator.isTalking) animator.setEmotion('surprised');
});

window.addEventListener('dragleave', (e) => {
  e.preventDefault();
  e.stopPropagation();
  if (animator && !animator.isTalking) animator.setEmotion('neutral');
});

window.addEventListener('drop', async (e) => {
  e.preventDefault();
  e.stopPropagation();
  const files = e.dataTransfer?.files;
  if (!files || files.length === 0) return;

  const file = files[0];
  console.log(`📁 [DragDrop] Archivo recibido: ${file.name}`);

  // 1. Si es una animación .vrma: reproducir directamente en Yize
  if (file.name.toLowerCase().endsWith('.vrma')) {
    if (!vrmaPlayer) {
      YizeUI.showBubble('El reproductor VRMA aún se está inicializando.', 'thinking');
      return;
    }
    const blobUrl = URL.createObjectURL(file);
    vrmaPlayer.loadVRMA(file.name, blobUrl).then(() => {
      vrmaPlayer.play(file.name, { loop: false, crossFade: 0.5 });
      if (animator) animator.setEmotion('celebrate');
      YizeUI.showBubble(`¡Reproduciendo animación VRMA: ${file.name}! ✨`, 'celebrate');
    }).catch((err) => {
      console.error(err);
      YizeUI.showBubble('No pude interpretar este archivo .vrma 😢', 'annoyed');
    });
    return;
  }

  // 2. Si es un nuevo modelo .vrm: cambiar avatar en caliente
  if (file.name.toLowerCase().endsWith('.vrm')) {
    const vrmBlobUrl = URL.createObjectURL(file);
    loadVRMModel(vrmBlobUrl, file.name);
    return;
  }

  // 3. Si es imagen o documento de código/texto: análisis con IA
  const isImage = file.type.startsWith('image/');
  const reader = new FileReader();

  if (isImage) {
    reader.onload = () => {
      const base64 = reader.result.split(',')[1];
      if (socket) {
        socket.send({
          type: 'file_drop',
          filename: file.name,
          is_image: true,
          data: base64,
        });
      }
      if (animator) animator.setEmotion('thinking');
      YizeUI.showBubble(`Examinando imagen: ${file.name}... 🖼️`, 'thinking');
    };
    reader.readAsDataURL(file);
  } else {
    reader.onload = () => {
      const text = reader.result;
      if (socket) {
        socket.send({
          type: 'file_drop',
          filename: file.name,
          is_image: false,
          text: String(text).slice(0, 40000),
        });
      }
      if (animator) animator.setEmotion('thinking');
      YizeUI.showBubble(`Analizando archivo: ${file.name}... 📄`, 'thinking');
    };
    reader.readAsText(file);
  }
});