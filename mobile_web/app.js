/**
 * app.js — Controlador de la app móvil de Yize (v2, solo front-end)
 *
 * Mantiene el mismo contrato con el servidor que la versión anterior:
 *   POST /api/command · POST /api/action · GET /api/screenshot
 *   GET  /api/tts     · GET  /api/status · WebSocket /ws
 */
'use strict';

const $ = (id) => document.getElementById(id);

// ─── Almacenamiento seguro (localStorage puede lanzar excepción en modo privado) ───
const store = {
  get(key, fallback = '') {
    try { const v = localStorage.getItem(key); return v === null ? fallback : v; }
    catch (_) { return fallback; }
  },
  set(key, value) { try { localStorage.setItem(key, value); } catch (_) {} },
  getSession(key, fallback) {
    try { const v = sessionStorage.getItem(key); return v ? JSON.parse(v) : fallback; }
    catch (_) { return fallback; }
  },
  setSession(key, value) { try { sessionStorage.setItem(key, JSON.stringify(value)); } catch (_) {} },
};

const CFG = {
  maxMessages: 200,
  requestTimeoutMs: 8000,
  screenIntervalMs: 3000,
  screenTimeoutMs: 10000,
  statusIntervalMs: 4000,
  wsMaxBackoffMs: 15000,
  avatarPulseMs: 3500,
  idleLabel: 'Toca el micrófono para dar una orden a Yize',
};

const SPEECH_ERRORS = {
  'not-allowed': 'Permite el micrófono en el navegador para hablar con Yize.',
  'service-not-allowed': 'Este navegador no permite el dictado por voz.',
  'no-speech': 'No te escuché. Toca el micrófono e inténtalo de nuevo.',
  'audio-capture': 'No se encontró un micrófono.',
  'network': 'El dictado por voz necesita conexión a internet.',
};

const state = {
  activeTab: 'tabChat',
  isRecording: false,
  ws: null,
  wsRetry: 0,
  wsTimer: null,
  autoRefreshScreen: false,
  screenTimer: null,
  screenReq: 0,
  statusTimer: null,
  avatarTimer: null,
  speakTarget: store.get('yize_speak_target') === 'mobile' ? 'mobile' : 'pc',
  pin: store.get('yize_mobile_pin'),
  history: store.getSession('yize_history', []),
};

// ─── Inicialización ───
document.addEventListener('DOMContentLoaded', () => {
  initA11y();
  initTabs();
  restoreHistory();
  initVoice();
  initQuickChips();
  initAudioToggle();
  initChatInput();
  initDeckActions();
  initScreenViewer();
  initSettings();
  connectWs();
  startTelemetry();
  warnIfNoPin();

  // El audio de los navegadores móviles solo se activa tras un gesto del usuario
  ['pointerdown', 'keydown'].forEach((ev) =>
    document.addEventListener(ev, unlockAudio, { passive: true })
  );

  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js').catch((e) => console.warn('SW no registrado:', e));
  }
});

// ─── Utilidades ───
function vibrate(pattern = 15) {
  if ('vibrate' in navigator) {
    try { navigator.vibrate(pattern); } catch (_) {}
  }
}

let toastTimer;
function showToast(msg) {
  const toast = $('toastNotice');
  if (!toast || !msg) return;
  toast.textContent = msg;
  toast.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove('show'), 2600);
}

function setVoiceStatus(text, active = false) {
  const label = $('voiceStatusLabel');
  if (!label) return;
  label.textContent = text;
  label.classList.toggle('active', active);
}

/** Deshabilita el botón mientras dura la acción (evita dobles toques). */
async function withBusy(btn, fn) {
  if (!btn || btn.disabled) return undefined;
  btn.disabled = true;
  btn.setAttribute('aria-busy', 'true');
  try { return await fn(); }
  finally { btn.disabled = false; btn.removeAttribute('aria-busy'); }
}

/**
 * Llamada al servidor con tiempo máximo y errores uniformes.
 * Con `body` hace POST e incluye el PIN (igual que antes). Siempre devuelve un objeto.
 */
async function api(path, body) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), CFG.requestTimeoutMs);
  try {
    const res = await fetch(path, {
      method: body ? 'POST' : 'GET',
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify({ ...body, pin: state.pin }) : undefined,
      signal: ctrl.signal,
    });
    if (res.status === 401 || res.status === 403) {
      return { ok: false, error: 'PIN incorrecto o faltante' };
    }
    return await res.json();
  } catch (err) {
    return {
      ok: false,
      error: err.name === 'AbortError' ? 'La PC tardó demasiado en responder' : 'Sin conexión con la PC',
    };
  } finally {
    clearTimeout(timer);
  }
}

// ─── Accesibilidad (se aplica por JS para no tocar el HTML) ───
function initA11y() {
  $('chatContainer')?.setAttribute('aria-live', 'polite');
  $('toastNotice')?.setAttribute('role', 'status');
  $('chatInput')?.setAttribute('aria-label', 'Escribe una orden para Yize');
  $('inputCustomText')?.setAttribute('aria-label', 'Texto para teclear en la PC');
  $('pinInput')?.setAttribute('aria-label', 'PIN de acceso móvil');
  document.querySelector('.bottom-nav')?.setAttribute('role', 'tablist');
}

// ─── Pestañas ───
function initTabs() {
  document.querySelectorAll('.nav-item').forEach((btn) => {
    btn.setAttribute('role', 'tab');
    btn.setAttribute('aria-selected', btn.classList.contains('active') ? 'true' : 'false');
    btn.addEventListener('click', () => {
      vibrate(10);
      setTab(btn.dataset.tab);
    });
  });
}

function setTab(id) {
  const prev = state.activeTab;
  state.activeTab = id;

  document.querySelectorAll('.nav-item').forEach((b) => {
    const on = b.dataset.tab === id;
    b.classList.toggle('active', on);
    b.setAttribute('aria-selected', on ? 'true' : 'false');
  });
  document.querySelectorAll('.tab-pane').forEach((p) => p.classList.toggle('active', p.id === id));

  // Al salir de la pestaña de pantalla se detienen las capturas automáticas
  if (prev === 'tabScreen' && id !== 'tabScreen') clearTimeout(state.screenTimer);
  if (id === 'tabScreen') refreshScreenshot();
}

// ─── Historial del chat ───
function renderMessage(msg) {
  const container = $('chatContainer');
  if (!container) return;

  const bubble = document.createElement('div');
  if (msg.role === 'user') {
    bubble.className = 'chat-bubble user';
    bubble.textContent = msg.text;
  } else {
    bubble.className = 'chat-bubble assistant';
    const meta = document.createElement('div');
    meta.className = 'bubble-meta';
    meta.textContent = msg.live ? `🔴 En Vivo [${msg.emotion}]` : `✦ Yize [${msg.emotion}]`;
    const content = document.createElement('div');
    content.textContent = msg.text;
    bubble.append(meta, content);
  }

  container.appendChild(bubble);
  while (container.children.length > CFG.maxMessages) container.firstElementChild.remove();
  container.scrollTop = container.scrollHeight;
}

function pushMessage(msg) {
  state.history.push(msg);
  if (state.history.length > CFG.maxMessages) {
    state.history.splice(0, state.history.length - CFG.maxMessages);
  }
  store.setSession('yize_history', state.history);
  renderMessage(msg);
}

function restoreHistory() {
  const container = $('chatContainer');
  if (!container || !state.history.length) return;
  container.replaceChildren();
  state.history.forEach(renderMessage);
}

function addUserMessage(text) {
  pushMessage({ role: 'user', text });
}

function addAssistantMessage(text, emotion = 'happy', live = false) {
  pushMessage({ role: 'assistant', text, emotion, live });
}

// ─── Avatar y "mente en directo" ───
function setSpeaking(on) {
  const avatar = $('heroAvatar');
  if (!avatar) return;
  clearTimeout(state.avatarTimer);
  avatar.classList.toggle('speaking', on);
}

function pulseAvatar(ms = CFG.avatarPulseMs) {
  setSpeaking(true);
  state.avatarTimer = setTimeout(() => setSpeaking(false), ms);
}

function updateLiveThought(text, emotion = 'happy') {
  const elText = $('liveThoughtText');
  const elTag = $('currentEmotionTag');
  const heroPill = $('heroEmotionPill');

  if (elText && text) elText.textContent = text;
  if (elTag && emotion) elTag.textContent = `[${emotion}]`;
  if (heroPill && emotion) heroPill.textContent = `✦ ${String(emotion).toUpperCase()}`;

  // Si habla el celular, el avatar sigue al audio; si no, un solo temporizador
  if (state.speakTarget !== 'mobile') pulseAvatar();
}

// ─── WebSocket (reconexión con espera creciente) ───
function connectWs() {
  if (state.ws && state.ws.readyState <= WebSocket.OPEN) return; // conectando o abierto

  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  let ws;
  try {
    ws = new WebSocket(`${proto}//${location.host}/ws`);
  } catch (_) {
    scheduleReconnect();
    return;
  }
  state.ws = ws;

  ws.onopen = () => {
    state.wsRetry = 0;
    updateWsIndicator(true);
  };
  ws.onmessage = (event) => {
    let data;
    try { data = JSON.parse(event.data); } catch (_) { return; }
    handleWsMessage(data);
  };
  ws.onclose = () => {
    if (state.ws !== ws) return;
    updateWsIndicator(false);
    scheduleReconnect();
  };
  ws.onerror = () => { try { ws.close(); } catch (_) {} };
}

function scheduleReconnect() {
  clearTimeout(state.wsTimer);
  const wait = Math.min(CFG.wsMaxBackoffMs, 1000 * 2 ** state.wsRetry++) + Math.random() * 500;
  state.wsTimer = setTimeout(connectWs, wait);
}

function reconnectNow() {
  state.wsRetry = 0;
  clearTimeout(state.wsTimer);
  connectWs();
}

document.addEventListener('visibilitychange', () => { if (!document.hidden) reconnectNow(); });
window.addEventListener('online', reconnectNow);

function updateWsIndicator(connected) {
  const dot = $('onlineDot');
  const label = $('connectionStatusLabel');
  if (dot) {
    dot.style.backgroundColor = connected ? 'var(--green-online)' : 'var(--red-danger)';
    dot.style.boxShadow = connected ? '0 0 8px var(--green-online)' : '0 0 8px var(--red-danger)';
  }
  if (label) label.textContent = connected ? 'Conectado a la PC' : 'Reconectando...';
}

function handleWsMessage(data) {
  if (!data || typeof data !== 'object') return;

  switch (data.type) {
    case 'welcome':
      if (data.latest_speech) updateLiveThought(data.latest_speech.text, data.latest_speech.emotion);
      break;
    case 'live_comment':
      updateLiveThought(data.text, data.emotion);
      addAssistantMessage(data.text, data.emotion, true);
      if (state.speakTarget === 'mobile') speakOnMobile(data.text);
      break;
    case 'assistant_response':
      updateLiveThought(data.text, data.emotion);
      addAssistantMessage(data.text, data.emotion);
      if (state.speakTarget === 'mobile') speakOnMobile(data.text);
      break;
    case 'action_executed':
      showToast(data.message);
      break;
    default:
      break;
  }
}

// ─── Voz de Yize en el celular (cola + audio desbloqueado por gesto) ───
let audioCtx = null;
const speech = { queue: [], busy: false, source: null };

function getAudioCtx() {
  if (!audioCtx) {
    const AC = window.AudioContext || window.webkitAudioContext;
    if (AC) audioCtx = new AC();
  }
  return audioCtx;
}

function unlockAudio() {
  const ctx = getAudioCtx();
  if (ctx && ctx.state === 'suspended') ctx.resume().catch(() => {});
}

async function ensureAudioRunning(ctx) {
  if (ctx.state === 'running') return true;
  await Promise.race([ctx.resume().catch(() => {}), new Promise((r) => setTimeout(r, 400))]);
  return ctx.state === 'running';
}

function speakOnMobile(text) {
  if (!text) return;
  speech.queue.push(text);
  if (speech.queue.length > 3) speech.queue.shift(); // no acumular retraso
  if (!speech.busy) drainSpeech();
}

async function drainSpeech() {
  speech.busy = true;
  while (speech.queue.length) {
    const text = speech.queue.shift();
    setSpeaking(true);
    try {
      await playTts(text);
    } catch (err) {
      await fallbackSpeak(text, err);
    }
  }
  setSpeaking(false);
  speech.busy = false;
}

async function playTts(text) {
  const ctx = getAudioCtx();
  if (!ctx) throw new Error('Web Audio no disponible');
  if (!(await ensureAudioRunning(ctx))) {
    throw Object.assign(new Error('audio bloqueado'), { blocked: true });
  }

  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), 15000);
  let bytes;
  try {
    const res = await fetch(`/api/tts?text=${encodeURIComponent(text)}`, { signal: ctrl.signal });
    if (!res.ok) throw new Error(`TTS HTTP ${res.status}`);
    bytes = await res.arrayBuffer();
  } finally {
    clearTimeout(timer);
  }

  const buffer = await ctx.decodeAudioData(bytes);
  await new Promise((resolve) => {
    const src = ctx.createBufferSource();
    src.buffer = buffer;
    src.connect(ctx.destination);
    src.onended = () => {
      if (speech.source === src) speech.source = null;
      resolve();
    };
    speech.source = src;
    src.start();
  });
}

/** Solo usa la voz del navegador si falla el servidor; si el audio está bloqueado, avisa. */
function fallbackSpeak(text, err) {
  if (err && err.blocked) {
    showToast('Toca la pantalla para activar la voz de Yize');
    return Promise.resolve();
  }
  return new Promise((resolve) => {
    if (!('speechSynthesis' in window)) return resolve();
    const utter = new SpeechSynthesisUtterance(text);
    utter.lang = 'es-419';
    utter.onend = () => resolve();
    utter.onerror = () => resolve();
    window.speechSynthesis.speak(utter);
    return undefined;
  });
}

function stopSpeech() {
  speech.queue.length = 0;
  try { speech.source?.stop(); } catch (_) {}
  if ('speechSynthesis' in window) window.speechSynthesis.cancel();
}

// ─── Reconocimiento de voz (solo el micrófono; el resto no depende de él) ───
function initVoice() {
  const micBtn = $('btnMicMain');
  const micRings = $('micRings');
  if (!micBtn) return;

  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) {
    micBtn.disabled = true;
    setVoiceStatus('Dictado no soportado en este navegador. Escribe por texto.');
    return;
  }

  const rec = new SR();
  rec.lang = 'es-419';
  rec.continuous = false;
  rec.interimResults = false;

  rec.onstart = () => {
    state.isRecording = true;
    stopSpeech(); // que el micrófono no capte la voz de Yize
    micBtn.classList.add('recording');
    micRings?.classList.add('active');
    setVoiceStatus('Escuchándote... Habla ahora', true);
    vibrate([40, 30, 40]);
  };
  rec.onresult = (event) => {
    const text = event.results[0][0].transcript?.trim();
    if (text) {
      addUserMessage(text);
      sendCommand(text);
    }
  };
  rec.onerror = (event) => {
    showToast(SPEECH_ERRORS[event.error] || `Error de dictado: ${event.error}`);
  };
  rec.onend = () => {
    state.isRecording = false;
    micBtn.classList.remove('recording');
    micRings?.classList.remove('active');
    setVoiceStatus(CFG.idleLabel);
  };

  micBtn.addEventListener('click', () => {
    vibrate(20);
    unlockAudio();
    if (state.isRecording) {
      rec.stop();
      return;
    }
    try { rec.start(); } catch (_) { rec.stop(); }
  });
}

// ─── Comandos rápidos (solo los que tienen data-cmd) ───
function initQuickChips() {
  document.querySelectorAll('.quick-chip[data-cmd]').forEach((chip) => {
    chip.addEventListener('click', () => {
      vibrate(15);
      unlockAudio();
      const cmd = chip.dataset.cmd;
      addUserMessage(cmd);
      withBusy(chip, () => sendCommand(cmd));
    });
  });
}

// ─── Destino de la voz: PC o celular ───
function initAudioToggle() {
  const options = { pc: $('optAudioPC'), mobile: $('optAudioMobile') };
  if (!options.pc || !options.mobile) return;
  options.pc.parentElement?.setAttribute('role', 'radiogroup');

  const apply = (target, announce) => {
    state.speakTarget = target;
    store.set('yize_speak_target', target);
    for (const [key, el] of Object.entries(options)) {
      el.classList.toggle('active', key === target);
      el.setAttribute('aria-checked', key === target ? 'true' : 'false');
    }
    if (target === 'pc') stopSpeech();
    if (announce) {
      showToast(target === 'pc'
        ? 'Yize hablará por los altavoces de tu PC'
        : 'Yize hablará en este celular');
    }
  };

  for (const [key, el] of Object.entries(options)) {
    el.setAttribute('role', 'radio');
    el.tabIndex = 0;
    const choose = () => {
      vibrate(10);
      unlockAudio();
      apply(key, true);
    };
    el.addEventListener('click', choose);
    el.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        choose();
      }
    });
  }
  apply(state.speakTarget, false);
}

// ─── Enviar órdenes al backend ───
async function sendCommand(commandText) {
  setVoiceStatus('Yize está pensando...');
  const data = await api('/api/command', {
    command: commandText,
    speak_pc: state.speakTarget === 'pc',
  });
  if (!data.ok && data.error) showToast(`Error: ${data.error}`);
  if (!state.isRecording) setVoiceStatus(CFG.idleLabel);
}

function initChatInput() {
  const input = $('chatInput');
  const btn = $('btnSendChat');
  if (!input || !btn) return;

  const send = () => {
    const text = input.value.trim();
    if (!text || btn.disabled) return;
    vibrate(15);
    unlockAudio();
    input.value = '';
    addUserMessage(text);
    withBusy(btn, () => sendCommand(text));
  };

  btn.addEventListener('click', send);
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.isComposing) send();
  });
}

// ─── Control remoto del PC ───
function initDeckActions() {
  // Un solo manejador para todos los botones con data-action
  document.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-action]');
    if (!btn) return;
    vibrate(20);
    withBusy(btn, async () => {
      const data = await api('/api/action', {
        action: btn.dataset.action,
        param: btn.dataset.param || '',
      });
      showToast(data.ok ? (data.message || 'Hecho') : `Error: ${data.error || 'la acción falló'}`);
    });
  });

  const btn = $('btnSendCustomText');
  const input = $('inputCustomText');
  if (!btn || !input) return;

  btn.addEventListener('click', () => {
    const text = input.value.trim();
    if (!text) return;
    vibrate(15);
    withBusy(btn, async () => {
      const data = await api('/api/action', { action: 'type_text', param: text });
      if (data.ok) {
        showToast('Texto tecleado en la PC');
        input.value = '';
      } else {
        showToast(`Error: ${data.error || 'no se pudo teclear'}`);
      }
    });
  });
}

// ─── Visor de pantalla ───
function initScreenViewer() {
  const img = $('screenImg');
  const btnRefresh = $('btnRefreshScreen');
  const chkAuto = $('chkAutoRefresh');
  const btnFull = $('btnFullscreenScreen');

  btnRefresh?.addEventListener('click', () => {
    vibrate(10);
    refreshScreenshot();
  });

  chkAuto?.addEventListener('change', (e) => {
    state.autoRefreshScreen = e.target.checked;
    if (state.autoRefreshScreen) refreshScreenshot();
    else clearTimeout(state.screenTimer);
  });

  if (img) {
    btnFull?.addEventListener('click', () => toggleFullscreen(img));
    img.addEventListener('click', () => { if (img.dataset.fs) cssFullscreen(img, false); });
  }

  // Sin captura automática con la pantalla apagada o la app en segundo plano
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) clearTimeout(state.screenTimer);
    else if (state.autoRefreshScreen && state.activeTab === 'tabScreen') refreshScreenshot();
  });
}

function scheduleScreenshot() {
  clearTimeout(state.screenTimer);
  if (state.autoRefreshScreen && state.activeTab === 'tabScreen' && !document.hidden) {
    state.screenTimer = setTimeout(refreshScreenshot, CFG.screenIntervalMs);
  }
}

/** Una captura a la vez: la siguiente se pide cuando termina la anterior. */
function refreshScreenshot() {
  const img = $('screenImg');
  const loading = $('screenLoading');
  if (!img) return;

  clearTimeout(state.screenTimer);
  const id = ++state.screenReq;
  if (loading && !state.autoRefreshScreen) loading.style.display = 'flex';

  const probe = new Image();
  let finished = false;
  const done = (ok) => {
    if (finished) return;
    finished = true;
    if (id !== state.screenReq) return; // ya hay una petición más nueva
    if (ok) img.src = probe.src;
    if (loading) loading.style.display = 'none';
    scheduleScreenshot();
  };

  probe.onload = () => done(true);
  probe.onerror = () => done(false);
  setTimeout(() => done(false), CFG.screenTimeoutMs);
  probe.src = `/api/screenshot?t=${Date.now()}`;
}

function toggleFullscreen(img) {
  if (img.dataset.fs) { cssFullscreen(img, false); return; }
  if (document.fullscreenElement) { document.exitFullscreen(); return; }
  const request = img.requestFullscreen || img.webkitRequestFullscreen;
  if (!request) { cssFullscreen(img, true); return; }
  // iPhone no permite pantalla completa nativa en imágenes: se usa el modo CSS
  Promise.resolve()
    .then(() => request.call(img))
    .catch(() => cssFullscreen(img, true));
}

function cssFullscreen(img, on) {
  if (on) {
    img.dataset.fs = '1';
    Object.assign(img.style, {
      position: 'fixed', inset: '0', width: '100vw', height: '100vh',
      objectFit: 'contain', background: '#000', zIndex: '9999',
    });
  } else {
    delete img.dataset.fs;
    img.style.cssText = '';
  }
}

// ─── Ajustes ───
function initSettings() {
  const pinInput = $('pinInput');
  const btnSavePin = $('btnSavePin');
  if (!pinInput || !btnSavePin) return;

  pinInput.value = state.pin;
  btnSavePin.addEventListener('click', () => {
    state.pin = pinInput.value.trim();
    store.set('yize_mobile_pin', state.pin);
    vibrate(15);
    showToast(state.pin ? 'PIN de seguridad guardado' : 'PIN eliminado: el acceso queda libre');
  });
}

function warnIfNoPin() {
  if (state.pin || store.getSession('yize_pin_warned', false)) return;
  store.setSession('yize_pin_warned', true);
  setTimeout(() => showToast('Sin PIN: cualquiera con el enlace puede controlar tu PC'), 1500);
}

// ─── Telemetría (solo con la app visible) ───
function startTelemetry() {
  const tick = async () => {
    if (!document.hidden) await updateTelemetry();
    state.statusTimer = setTimeout(tick, CFG.statusIntervalMs);
  };
  tick();

  document.addEventListener('visibilitychange', () => {
    if (document.hidden) return;
    clearTimeout(state.statusTimer);
    tick();
  });
}

async function updateTelemetry() {
  const data = await api('/api/status');
  if (!data.ok) return;

  const pct = (v) => Math.max(0, Math.min(100, Math.round(Number(v) || 0)));
  const cpu = pct(data.cpu_percent);
  const ram = pct(data.ram_percent);

  // La CPU aparece en la cabecera y en la tarjeta de Ajustes: se actualizan las dos
  ['statCpuVal', 'statCpuValCard'].forEach((id) => {
    const el = $(id);
    if (el) el.textContent = `${cpu}%`;
  });
  const cpuBar = $('statCpuBar');
  if (cpuBar) cpuBar.style.width = `${cpu}%`;

  const ramVal = $('statRamVal');
  const ramBar = $('statRamBar');
  if (ramVal) ramVal.textContent = `${ram}%`;
  if (ramBar) ramBar.style.width = `${ram}%`;

  const batVal = $('statBatteryVal');
  if (batVal) {
    if (data.battery) {
      const plug = data.battery.power_plugged ? '⚡' : '';
      batVal.textContent = `${data.battery.percent}% ${plug}`.trim();
    } else {
      batVal.textContent = 'En corriente ⚡';
    }
  }

  const winEl = $('activeWindowTitle');
  if (winEl && data.active_window) winEl.textContent = data.active_window;
}
