const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  listDir: (dirPath, filter) => ipcRenderer.invoke('list-dir', dirPath, filter),
  getQuickNavs: () => ipcRenderer.invoke('get-quick-navs'),
  showFolderDialog: () => ipcRenderer.invoke('show-folder-dialog'),
});
