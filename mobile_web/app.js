/**
 * app.js — Controlador de la Aplicación Móvil de Yize
 * Manejo de voz, chat, WebSocket en tiempo real, deck de control y captura de pantalla.
 */

// ─── ESTADO GLOBAL ───
const state = {
  isRecording: false,
  recognition: null,
  ws: null,
  wsConnected: false,
  autoRefreshScreen: false,
  screenInterval: null,
  speakTarget: localStorage.getItem('yize_speak_target') || 'pc', // 'pc' | 'mobile'
  pin: localStorage.getItem('yize_mobile_pin') || '',
  currentAudio: null
};

// ─── INICIALIZACIÓN AL CARGAR ───
document.addEventListener('DOMContentLoaded', () => {
  initTabs();
  initVoice();
  initWebSocket();
  initChatInput();
  initDeckActions();
  initScreenViewer();
  initSettings();
  startTelemetryPoller();

  // Registrar Service Worker para PWA
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js').catch(() => {});
  }
});

// ─── VIBRACIÓN HÁPTICA ───
function vibrate(ms = 15) {
  if ('vibrate' in navigator) {
    try { navigator.vibrate(ms); } catch (_) {}
  }
}

// ─── TOAST NOTICES ───
function showToast(msg) {
  const toast = document.getElementById('toastNotice');
  if (!toast) return;
  toast.textContent = msg;
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), 2400);
}

// ─── TABS NAVIGATION ───
function initTabs() {
  const navBtns = document.querySelectorAll('.nav-item');
  const panes = document.querySelectorAll('.tab-pane');

  navBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const targetId = btn.dataset.tab;
      vibrate(10);

      navBtns.forEach(b => b.classList.remove('active'));
      panes.forEach(p => p.classList.remove('active'));

      btn.classList.add('active');
      const targetPane = document.getElementById(targetId);
      if (targetPane) targetPane.classList.add('active');

      // Si entra a la pestaña pantalla y no hay imagen cargada, cargar una
      if (targetId === 'tabScreen') {
        refreshScreenshot();
      }
    });
  });
}

// ─── WEBSOCKET & TIEMPO REAL ───
function initWebSocket() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${window.location.host}/ws`;

  function connect() {
    try {
      state.ws = new WebSocket(wsUrl);

      state.ws.onopen = () => {
        state.wsConnected = true;
        updateWsIndicator(true);
      };

      state.ws.onmessage = (event) => {
        try {
          const data = jsonParse(event.data);
          handleWsMessage(data);
        } catch (e) {
          console.warn('Error parseando WS:', e);
        }
      };

      state.ws.onclose = () => {
        state.wsConnected = false;
        updateWsIndicator(false);
        setTimeout(connect, 3000);
      };

      state.ws.onerror = () => {
        state.wsConnected = false;
        updateWsIndicator(false);
      };
    } catch (e) {
      setTimeout(connect, 4000);
    }
  }

  connect();
}

function updateWsIndicator(connected) {
  const dot = document.getElementById('onlineDot');
  const statusLabel = document.getElementById('connectionStatusLabel');
  if (dot) {
    dot.style.backgroundColor = connected ? 'var(--green-online)' : 'var(--red-danger)';
    dot.style.boxShadow = connected ? '0 0 8px var(--green-online)' : '0 0 8px var(--red-danger)';
  }
  if (statusLabel) {
    statusLabel.textContent = connected ? 'Conectado a la PC' : 'Reconectando...';
  }
}

function handleWsMessage(data) {
  if (!data) return;

  if (data.type === 'welcome') {
    if (data.latest_speech) {
      updateLiveThought(data.latest_speech.text, data.latest_speech.emotion);
    }
  } else if (data.type === 'live_comment') {
    updateLiveThought(data.text, data.emotion);
    addAssistantMessage(data.text, data.emotion, true);
    if (state.speakTarget === 'mobile') {
      playTtsMobile(data.text);
    }
  } else if (data.type === 'assistant_response') {
    updateLiveThought(data.text, data.emotion);
    addAssistantMessage(data.text, data.emotion);
    if (state.speakTarget === 'mobile') {
      playTtsMobile(data.text);
    }
  } else if (data.type === 'action_executed') {
    showToast(data.message);
  }
}

function updateLiveThought(text, emotion = 'happy') {
  const elText = document.getElementById('liveThoughtText');
  const elTag = document.getElementById('currentEmotionTag');
  if (elText && text) elText.textContent = text;
  if (elTag && emotion) elTag.textContent = `[${emotion}]`;
}

// ─── RECONOCIMIENTO DE VOZ ───
function initVoice() {
  const micBtn = document.getElementById('btnMicMain');
  const micRings = document.getElementById('micRings');
  const statusLabel = document.getElementById('voiceStatusLabel');

  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

  if (!SpeechRecognition) {
    if (statusLabel) {
      statusLabel.textContent = 'Dictado nativo no soportado en este navegador. Escribe por texto.';
    }
    return;
  }

  const rec = new SpeechRecognition();
  rec.lang = 'es-419';
  rec.continuous = false;
  rec.interimResults = false;

  rec.onstart = () => {
    state.isRecording = true;
    micBtn.classList.add('recording');
    micRings.classList.add('active');
    statusLabel.textContent = 'Escuchándote... Habla ahora';
    statusLabel.classList.add('active');
    vibrate([40, 30, 40]);
  };

  rec.onresult = (event) => {
    const text = event.results[0][0].transcript;
    if (text && text.trim()) {
      addUserMessage(text);
      sendCommand(text);
    }
  };

  rec.onerror = (event) => {
    console.warn('SpeechRecognition error:', event.error);
    statusLabel.textContent = `Error: ${event.error}. Toca para reintentar.`;
  };

  rec.onend = () => {
    state.isRecording = false;
    micBtn.classList.remove('recording');
    micRings.classList.remove('active');
    statusLabel.textContent = 'Toca el micrófono para dar una orden a Yize';
    statusLabel.classList.remove('active');
  };

  state.recognition = rec;

  micBtn.addEventListener('click', () => {
    vibrate(20);
    if (state.isRecording) {
      rec.stop();
    } else {
      try {
        rec.start();
      } catch (e) {
        rec.stop();
      }
    }
  });

  // Configurar chips de comando rápido
  document.querySelectorAll('.quick-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      const cmd = chip.dataset.cmd || chip.textContent.trim();
      vibrate(15);
      addUserMessage(cmd);
      sendCommand(cmd);
    });
  });

  // Selector de destino de voz (PC vs Celular)
  const togglePC = document.getElementById('optAudioPC');
  const toggleMobile = document.getElementById('optAudioMobile');

  if (togglePC && toggleMobile) {
    if (state.speakTarget === 'mobile') {
      toggleMobile.classList.add('active');
      togglePC.classList.remove('active');
    } else {
      togglePC.classList.add('active');
      toggleMobile.classList.remove('active');
    }

    togglePC.addEventListener('click', () => {
      state.speakTarget = 'pc';
      localStorage.setItem('yize_speak_target', 'pc');
      togglePC.classList.add('active');
      toggleMobile.classList.remove('active');
      vibrate(10);
      showToast('Yize hablará por los altavoces de tu PC');
    });

    toggleMobile.addEventListener('click', () => {
      state.speakTarget = 'mobile';
      localStorage.setItem('yize_speak_target', 'mobile');
      toggleMobile.classList.add('active');
      togglePC.classList.remove('active');
      vibrate(10);
      showToast('Yize hablará en este celular');
    });
  }
}

// ─── REPRODUCCIÓN DE VOZ EN EL CELULAR (TTS) ───
function playTtsMobile(text) {
  if (!text) return;

  if (state.currentAudio) {
    state.currentAudio.pause();
    state.currentAudio = null;
  }

  const url = `/api/tts?text=${encodeURIComponent(text)}`;
  const audio = new Audio(url);
  state.currentAudio = audio;
  audio.play().catch(e => {
    // Si el navegador bloquea autoplay, usar síntesis nativa
    if ('speechSynthesis' in window) {
      const utter = new SpeechSynthesisUtterance(text);
      utter.lang = 'es-LA';
      window.speechSynthesis.speak(utter);
    }
  });
}

// ─── ENVIAR COMANDOS AL BACKEND ───
async function sendCommand(commandText) {
  const statusLabel = document.getElementById('voiceStatusLabel');
  if (statusLabel) statusLabel.textContent = 'Yize está pensando...';

  try {
    const res = await fetch('/api/command', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        command: commandText,
        speak_pc: state.speakTarget === 'pc',
        pin: state.pin
      })
    });
    const data = await res.json();
    if (!data.ok && data.error) {
      showToast(`Error: ${data.error}`);
    }
  } catch (err) {
    showToast('Error de conexión con la PC');
  } finally {
    if (statusLabel) statusLabel.textContent = 'Toca el micrófono para dar una orden a Yize';
  }
}

// ─── CHAT MESSAGES ───
function initChatInput() {
  const input = document.getElementById('chatInput');
  const btn = document.getElementById('btnSendChat');

  function send() {
    const val = input.value.trim();
    if (!val) return;
    vibrate(15);
    addUserMessage(val);
    sendCommand(val);
    input.value = '';
  }

  if (btn) btn.addEventListener('click', send);
  if (input) {
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') send();
    });
  }
}

function addUserMessage(text) {
  const container = document.getElementById('chatContainer');
  if (!container) return;

  const b = document.createElement('div');
  b.className = 'chat-bubble user';
  b.textContent = text;
  container.appendChild(b);
  container.scrollTop = container.scrollHeight;
}

function addAssistantMessage(text, emotion = 'happy', isLive = false) {
  const container = document.getElementById('chatContainer');
  if (!container) return;

  const b = document.createElement('div');
  b.className = 'chat-bubble assistant';

  const meta = document.createElement('div');
  meta.className = 'bubble-meta';
  meta.textContent = isLive ? `🔴 En Vivo [${emotion}]` : `✦ Yize [${emotion}]`;

  const content = document.createElement('div');
  content.textContent = text;

  b.appendChild(meta);
  b.appendChild(content);
  container.appendChild(b);
  container.scrollTop = container.scrollHeight;
}

// ─── TAB 2: DECK PC (CONTROL REMOTO) ───
function initDeckActions() {
  // Botones de acción directa
  document.querySelectorAll('[data-action]').forEach(btn => {
    btn.addEventListener('click', async () => {
      const action = btn.dataset.action;
      const param = btn.dataset.param || '';
      vibrate(20);

      try {
        const res = await fetch('/api/action', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action, param, pin: state.pin })
        });
        const data = await res.json();
        if (data.ok) {
          showToast(data.message);
        } else {
          showToast(`Error: ${data.error}`);
        }
      } catch (e) {
        showToast('Error comunicando con la PC');
      }
    });
  });

  // Escribir texto en PC
  const btnSendText = document.getElementById('btnSendCustomText');
  const inputCustomText = document.getElementById('inputCustomText');
  if (btnSendText && inputCustomText) {
    btnSendText.addEventListener('click', async () => {
      const txt = inputCustomText.value.trim();
      if (!txt) return;
      vibrate(15);
      await fetch('/api/action', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'type_text', param: txt, pin: state.pin })
      });
      showToast('Texto tecleado en la PC');
      inputCustomText.value = '';
    });
  }
}

// ─── TAB 3: VISOR DE PANTALLA ───
function initScreenViewer() {
  const img = document.getElementById('screenImg');
  const btnRefresh = document.getElementById('btnRefreshScreen');
  const chkAuto = document.getElementById('chkAutoRefresh');
  const btnFull = document.getElementById('btnFullscreenScreen');

  if (btnRefresh) {
    btnRefresh.addEventListener('click', () => {
      vibrate(10);
      refreshScreenshot();
    });
  }

  if (chkAuto) {
    chkAuto.addEventListener('change', (e) => {
      state.autoRefreshScreen = e.target.checked;
      if (state.autoRefreshScreen) {
        state.screenInterval = setInterval(refreshScreenshot, 3000);
      } else {
        clearInterval(state.screenInterval);
      }
    });
  }

  if (btnFull && img) {
    btnFull.addEventListener('click', () => {
      if (img.requestFullscreen) {
        img.requestFullscreen();
      } else if (img.webkitRequestFullscreen) {
        img.webkitRequestFullscreen();
      }
    });
  }
}

async function refreshScreenshot() {
  const img = document.getElementById('screenImg');
  const loading = document.getElementById('screenLoading');
  if (!img) return;

  if (loading && !state.autoRefreshScreen) loading.style.display = 'flex';

  const cacheBuster = `t=${Date.now()}`;
  const newImg = new Image();
  newImg.src = `/api/screenshot?${cacheBuster}`;
  newImg.onload = () => {
    img.src = newImg.src;
    if (loading) loading.style.display = 'none';
  };
  newImg.onerror = () => {
    if (loading) loading.style.display = 'none';
  };
}

// ─── TAB 4: AJUSTES & TELEMETRÍA ───
function initSettings() {
  const pinInput = document.getElementById('pinInput');
  const btnSavePin = document.getElementById('btnSavePin');

  if (pinInput) pinInput.value = state.pin;

  if (btnSavePin && pinInput) {
    btnSavePin.addEventListener('click', () => {
      state.pin = pinInput.value.trim();
      localStorage.setItem('yize_mobile_pin', state.pin);
      vibrate(15);
      showToast('PIN de seguridad guardado');
    });
  }
}

function startTelemetryPoller() {
  async function fetchStatus() {
    try {
      const res = await fetch('/api/status');
      const data = await res.json();
      if (!data.ok) return;

      // Actualizar medidores
      const cpuVal = document.getElementById('statCpuVal');
      const cpuBar = document.getElementById('statCpuBar');
      if (cpuVal) cpuVal.textContent = `${Math.round(data.cpu_percent)}%`;
      if (cpuBar) cpuBar.style.width = `${data.cpu_percent}%`;

      const ramVal = document.getElementById('statRamVal');
      const ramBar = document.getElementById('statRamBar');
      if (ramVal) ramVal.textContent = `${Math.round(data.ram_percent)}%`;
      if (ramBar) ramBar.style.width = `${data.ram_percent}%`;

      // Batería
      const batVal = document.getElementById('statBatteryVal');
      if (batVal) {
        if (data.battery) {
          const plug = data.battery.power_plugged ? '⚡' : '';
          batVal.textContent = `${data.battery.percent}% ${plug}`;
        } else {
          batVal.textContent = 'En corriente ⚡';
        }
      }

      // Ventana activa
      const winEl = document.getElementById('activeWindowTitle');
      if (winEl && data.active_window) {
        winEl.textContent = data.active_window;
      }
    } catch (_) {}
  }

  fetchStatus();
  setInterval(fetchStatus, 4000);
}

function jsonParse(str) {
  try { return JSON.parse(str); } catch (_) { return null; }
}
