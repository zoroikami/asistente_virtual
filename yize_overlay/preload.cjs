const { ipcRenderer } = require('electron');

window.electronAPI = {
  dragWindow: (deltaX, deltaY) => ipcRenderer.send('window-drag', { deltaX, deltaY }),
  moveWindow: (position) => ipcRenderer.send('move-window', position),
  minimize: () => ipcRenderer.send('window-minimize'),
  hide: () => ipcRenderer.send('window-hide'),
};
