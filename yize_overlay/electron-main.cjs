const { app, BrowserWindow, screen, ipcMain, session, desktopCapturer } = require('electron');
const path = require('path');

let mainWindow;
let animInterval = null;

function smoothMoveTo(targetX, targetY, duration = 350) {
  if (!mainWindow) return;
  if (animInterval) clearInterval(animInterval);

  const [startX, startY] = mainWindow.getPosition();
  const startTime = Date.now();

  animInterval = setInterval(() => {
    if (!mainWindow) {
      clearInterval(animInterval);
      return;
    }
    const elapsed = Date.now() - startTime;
    const progress = Math.min(elapsed / duration, 1);
    // Curva cúbica suave (ease-out)
    const ease = 1 - Math.pow(1 - progress, 3);

    const curX = Math.round(startX + (targetX - startX) * ease);
    const curY = Math.round(startY + (targetY - startY) * ease);

    mainWindow.setPosition(curX, curY);

    if (progress >= 1) {
      clearInterval(animInterval);
      animInterval = null;
    }
  }, 16);
}

function moveToPosition(posName) {
  if (!mainWindow) return;
  const primaryDisplay = screen.getPrimaryDisplay();
  const { width, height } = primaryDisplay.workAreaSize;
  const [winW, winH] = mainWindow.getSize();

  let targetX = width - winW - 20;
  let targetY = height - winH - 20;

  switch (posName) {
    case 'left':
    case 'bottom_left':
      targetX = 20;
      targetY = height - winH - 20;
      break;
    case 'top_left':
      targetX = 20;
      targetY = 20;
      break;
    case 'top_right':
      targetX = width - winW - 20;
      targetY = 20;
      break;
    case 'center':
      targetX = Math.round((width - winW) / 2);
      targetY = Math.round((height - winH) / 2);
      break;
    case 'minimize':
      mainWindow.minimize();
      return;
    case 'right':
    case 'bottom_right':
    default:
      targetX = width - winW - 20;
      targetY = height - winH - 20;
      break;
  }

  smoothMoveTo(targetX, targetY);
}

function createWindow() {
  const primaryDisplay = screen.getPrimaryDisplay();
  const { width, height } = primaryDisplay.workAreaSize;

  const winW = 380;
  const winH = 560;

  mainWindow = new BrowserWindow({
    title: 'Yize 3D Overlay',
    width: winW,
    height: winH,
    x: width - winW - 20,
    y: height - winH - 20,
    transparent: true,
    frame: false,
    alwaysOnTop: true,
    hasShadow: false,
    resizable: true,
    skipTaskbar: false,
    backgroundColor: '#00000000',
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      nodeIntegration: true,
      contextIsolation: false,
      webSecurity: false,
      autoplayPolicy: 'no-user-gesture-required'
    }
  });

  mainWindow.webContents.on('console-message', (event, level, message) => {
    console.log(`[Renderer] ${message}`);
  });
  mainWindow.webContents.on('did-fail-load', (event, errorCode, errorDescription) => {
    console.error(`[Renderer Load Fail] ${errorCode}: ${errorDescription}`);
  });

  let cursorInterval = null;
  let lastCursorPos = { x: 0, y: 0 };
  let shakeFrames = 0;
  let lastShakeTime = 0;

  const startCursorTracker = () => {
    if (cursorInterval) clearInterval(cursorInterval);
    cursorInterval = setInterval(() => {
      if (!mainWindow || mainWindow.isDestroyed()) return;
      try {
        const p = screen.getCursorScreenPoint();
        const [winX, winY] = mainWindow.getPosition();
        const [winW, winH] = mainWindow.getSize();

        const dx = p.x - lastCursorPos.x;
        const dy = p.y - lastCursorPos.y;
        const dist = Math.hypot(dx, dy);
        lastCursorPos = { x: p.x, y: p.y };

        // Detección de agitación rápida del mouse (Mouse Shake Panic)
        const now = Date.now();
        if (dist > 75) {
          shakeFrames++;
          if (shakeFrames >= 6 && (now - lastShakeTime > 10000)) {
            lastShakeTime = now;
            shakeFrames = 0;
            mainWindow.webContents.send('cursor-shake');
          }
        } else {
          shakeFrames = Math.max(0, shakeFrames - 1);
        }

        // Posición normalizada para el LookAt 3D en toda la pantalla
        const relX = p.x - winX;
        const relY = p.y - winY;
        mainWindow.webContents.send('global-cursor', {
          screenX: p.x,
          screenY: p.y,
          relX,
          relY,
          normX: (relX / winW) * 2 - 1,
          normY: -((relY / winH) * 2 - 1)
        });
      } catch (_) {}
    }, 40);
  };

  startCursorTracker();

  const distPath = path.join(__dirname, 'dist', 'index.html');
  mainWindow.loadFile(distPath);

  mainWindow.on('closed', () => {
    if (cursorInterval) clearInterval(cursorInterval);
    mainWindow = null;
  });
}

// IPC Handlers
ipcMain.on('move-window', (event, pos) => {
  moveToPosition(pos);
});

ipcMain.on('window-drag', (event, { deltaX, deltaY }) => {
  if (!mainWindow) return;
  const [x, y] = mainWindow.getPosition();
  mainWindow.setPosition(x + deltaX, y + deltaY);
});

ipcMain.on('window-minimize', () => {
  if (mainWindow) mainWindow.minimize();
});

ipcMain.on('window-hide', () => {
  if (mainWindow) {
    if (mainWindow.isVisible()) mainWindow.hide();
    else mainWindow.show();
  }
});

let guideWindow = null;

function showScreenGuide(targetX, targetY, label = 'Elemento') {
  if (guideWindow && !guideWindow.isDestroyed()) {
    try { guideWindow.close(); } catch (_) {}
  }

  const primaryDisplay = screen.getPrimaryDisplay();
  const { width, height } = primaryDisplay.bounds;

  guideWindow = new BrowserWindow({
    x: 0,
    y: 0,
    width,
    height,
    transparent: true,
    frame: false,
    alwaysOnTop: true,
    hasShadow: false,
    focusable: false,
    resizable: false,
    skipTaskbar: true,
    backgroundColor: '#00000000',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true
    }
  });

  guideWindow.setIgnoreMouseEvents(true, { forward: true });

  const html = `<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * { margin:0; padding:0; box-sizing:border-box; overflow:hidden; }
  body { width:100vw; height:100vh; background:transparent; position:relative; font-family:'Segoe UI', system-ui, sans-serif; }
  .pointer-container {
    position:absolute;
    left:${targetX}px;
    top:${targetY}px;
    transform:translate(-50%, -50%);
    display:flex;
    flex-direction:column;
    align-items:center;
    pointer-events:none;
    animation:appear 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
  }
  .reticle {
    width:84px; height:84px;
    border:3px solid #b55fe6;
    border-radius:50%;
    box-shadow:0 0 30px #b55fe6, inset 0 0 20px #00f3ff;
    position:relative;
    animation:spinGlow 2.5s infinite linear;
  }
  .reticle::before {
    content:'';
    position:absolute;
    top:-6px; left:50%; transform:translateX(-50%);
    width:12px; height:12px;
    background:#00f3ff;
    border-radius:50%;
    box-shadow:0 0 12px #00f3ff;
  }
  .reticle::after {
    content:'';
    position:absolute;
    inset:14px;
    border:2px dashed #00f3ff;
    border-radius:50%;
  }
  .center-dot {
    position:absolute;
    top:50%; left:50%; transform:translate(-50%, -50%);
    width:8px; height:8px;
    background:#fff;
    border-radius:50%;
    box-shadow:0 0 10px #fff;
  }
  .arrow-down {
    width: 0; 
    height: 0; 
    border-left: 10px solid transparent;
    border-right: 10px solid transparent;
    border-top: 14px solid #00f3ff;
    margin-top: -6px;
    filter: drop-shadow(0 0 6px #00f3ff);
    animation: bounce 1s infinite alternate ease-in-out;
  }
  .badge {
    margin-top:8px;
    background:rgba(15, 10, 28, 0.92);
    border:1px solid #b55fe6;
    box-shadow:0 6px 25px rgba(181, 95, 230, 0.6);
    color:#fff;
    padding:6px 14px;
    border-radius:20px;
    font-size:13px;
    font-weight:bold;
    letter-spacing:0.5px;
    white-space:nowrap;
  }
  @keyframes spinGlow {
    0% { transform:scale(0.96) rotate(0deg); }
    50% { transform:scale(1.08) rotate(180deg); }
    100% { transform:scale(0.96) rotate(360deg); }
  }
  @keyframes bounce {
    0% { transform: translateY(0); }
    100% { transform: translateY(6px); }
  }
  @keyframes appear {
    0% { opacity:0; transform:translate(-50%, -50%) scale(0.3); }
    100% { opacity:1; transform:translate(-50%, -50%) scale(1); }
  }
</style>
</head>
<body>
  <div class="pointer-container">
    <div class="reticle">
      <div class="center-dot"></div>
    </div>
    <div class="arrow-down"></div>
    <div class="badge">🎯 ${label}</div>
  </div>
</body>
</html>`;

  guideWindow.loadURL('data:text/html;charset=utf-8,' + encodeURIComponent(html));

  setTimeout(() => {
    if (guideWindow && !guideWindow.isDestroyed()) {
      guideWindow.close();
      guideWindow = null;
    }
  }, 6500);
}

ipcMain.on('show-screen-guide', (event, { x, y, label }) => {
  showScreenGuide(x, y, label);
});

app.whenReady().then(() => {
  if (session?.defaultSession?.setDisplayMediaRequestHandler) {
    session.defaultSession.setDisplayMediaRequestHandler((request, callback) => {
      desktopCapturer.getSources({ types: ['screen'] })
        .then((sources) => {
          callback({ video: sources[0], audio: 'loopback' });
        })
        .catch((err) => {
          console.error('[Electron] Error capturando audio loopback:', err);
        });
    });
  }
  createWindow();
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
