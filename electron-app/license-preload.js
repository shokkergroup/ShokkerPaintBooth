const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronLicense', {
  ipcRenderer: {
    send: (channel, ...args) => {
      const allowed = ['license-submit', 'license-quit', 'license-buy'];
      if (allowed.includes(channel)) {
        ipcRenderer.send(channel, ...args);
      }
    },
    on: (channel, callback) => {
      const allowed = ['license-error', 'license-status'];
      if (allowed.includes(channel)) {
        ipcRenderer.on(channel, callback);
      }
    }
  }
});
