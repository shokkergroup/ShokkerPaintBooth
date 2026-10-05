const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronLicense', {
  ipcRenderer: {
    send: (channel, ...args) => {
      const allowed = ['license-submit', 'license-quit', 'license-buy', 'license-bypass-submit'];
      if (allowed.includes(channel)) {
        ipcRenderer.send(channel, ...args);
      }
    },
    on: (channel, callback) => {
      const allowed = ['license-error', 'license-status', 'bypass-result'];
      if (allowed.includes(channel)) {
        ipcRenderer.on(channel, callback);
      }
    }
  }
});

// Splash status bridge — the boot splash window reuses this preload. Under
// contextIsolation:true / nodeIntegration:false the splash HTML cannot call
// require('electron'), so expose a tiny typed subscription for 'splash-status'.
contextBridge.exposeInMainWorld('splashAPI', {
  onStatus: (listener) => {
    if (typeof listener !== 'function') return;
    ipcRenderer.on('splash-status', (_event, msg) => {
      try { listener(msg); } catch (_) { /* ignore splash render errors */ }
    });
  }
});
