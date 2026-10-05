'use strict';

const { contextBridge, ipcRenderer } = require('electron');

const INVOKE_CHANNELS = new Set([
  'shokk-demo:runtime-info',
  'shokk-demo:select-source-file',
  'shokk-demo:select-iracing-folder',
  'shokk-demo:open-external',
  'shokk-demo:reveal-path',
]);

function invoke(channel, value) {
  if (!INVOKE_CHANNELS.has(channel)) {
    return Promise.reject(new Error('Blocked SHOKK DEMO bridge request.'));
  }
  return typeof value === 'undefined'
    ? ipcRenderer.invoke(channel)
    : ipcRenderer.invoke(channel, value);
}

contextBridge.exposeInMainWorld('shokkDemo', Object.freeze({
  getRuntimeInfo: () => invoke('shokk-demo:runtime-info'),
  selectSourceFile: () => invoke('shokk-demo:select-source-file'),
  selectIRacingFolder: () => invoke('shokk-demo:select-iracing-folder'),
  openExternal: (url) => invoke('shokk-demo:open-external', String(url || '')),
  revealPath: (requestedPath) => invoke('shokk-demo:reveal-path', String(requestedPath || '')),
}));
