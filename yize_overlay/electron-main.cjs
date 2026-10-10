const { app, BrowserWindow, screen, ipcMain } = require('electron');
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

  const distPath = path.join(__dirname, 'dist', 'index.html');
  mainWindow.loadFile(distPath);

  mainWindow.on('closed', () => {
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

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
