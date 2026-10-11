const { ipcRenderer } = require('electron');

window.electronAPI = {
  dragWindow: (deltaX, deltaY) => ipcRenderer.send('window-drag', { deltaX, deltaY }),
  moveWindow: (position) => ipcRenderer.send('move-window', position),
  minimize: () => ipcRenderer.send('window-minimize'),
  hide: () => ipcRenderer.send('window-hide'),
  onGlobalCursor: (cb) => ipcRenderer.on('global-cursor', (event, data) => cb(data)),
  onCursorShake: (cb) => ipcRenderer.on('cursor-shake', () => cb()),
  showScreenGuide: (data) => ipcRenderer.send('show-screen-guide', data),
};
