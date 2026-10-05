// preload.js — minimal, hardened API surface bridged into the renderer.
// Goals: contextIsolation safe (no Node primitives leaked), small/typed API,
// and pre-validated channels (no arbitrary IPC invoke).
const { contextBridge, ipcRenderer, webFrame } = require('electron');

// ----- Channel allowlists (defense-in-depth) -----
const INVOKE_CHANNELS = new Set([
  'list-dir',
  'get-quick-navs',
  'show-folder-dialog',
  'select-source-paint',
  'select-iracing-car-folder',
  'app-version',
  'get-server-port',
  'forge-import-psd',
  'gpu-status',
  'open-external',
  'show-about',
  'show-error',
  'set-unsaved-state',
  'get-recent-files',
  'add-recent-file',
  'request-reload',
  'request-hard-reload',
  'request-toggle-devtools',
  'log-renderer',
  'iracing-native-status',
  'iracing-native-attach',
  'iracing-native-create',
  'iracing-native-resize',
  'iracing-native-load',
  'iracing-native-paint',
  'iracing-native-shutdown',
  'start-update-download',
  'install-update',
]);
const SEND_CHANNELS = new Set([
  'renderer-ready',
  'renderer-crash-report',
  // 2026-06-08: real restart so downloaded Finish Packs load (page reload alone leaves the old server running)
  'spb-restart-app',
]);
const ON_CHANNELS = new Set([
  'server-status',
  'splash-status',
  'deep-link',
  'menu-action',
  'before-quit',
  'theme-changed',
  'update-banner',
  'update-progress',
  'update-ready',
]);

function safeInvoke(channel, ...args) {
  if (!INVOKE_CHANNELS.has(channel)) {
    return Promise.reject(new Error(`Blocked invoke channel: ${channel}`));
  }
  return ipcRenderer.invoke(channel, ...args);
}

function safeSend(channel, ...args) {
  if (!SEND_CHANNELS.has(channel)) return false;
  ipcRenderer.send(channel, ...args);
  return true;
}

function safeOn(channel, listener) {
  if (!ON_CHANNELS.has(channel)) return () => {};
  const wrapped = (_event, ...args) => {
    try { listener(...args); } catch (_) { /* swallow renderer errors */ }
  };
  ipcRenderer.on(channel, wrapped);
  // Return an unsubscribe handle so the renderer can clean up if needed.
  return () => ipcRenderer.removeListener(channel, wrapped);
}

function boundedDialogPath(value) {
  if (typeof value !== 'string') return '';
  const pathValue = value.trim();
  return pathValue.length <= 4096 && !pathValue.includes('\0') ? pathValue : '';
}

function sourcePaintKind(value) {
  return value === 'layered' || value === 'all' ? value : 'flat';
}

// Disable the renderer's built-in zoom shortcuts (Ctrl+0/+/-) by pinning
// the zoom factor; the main process menu also disables the accelerators.
try {
  webFrame.setVisualZoomLevelLimits(1, 1);
  webFrame.setZoomFactor(1);
} catch (_) { /* older electron */ }

// ----- Public API surface -----
contextBridge.exposeInMainWorld('electronAPI', {
  // File browsing (existing)
  listDir: (dirPath, filter) => safeInvoke('list-dir', dirPath, filter),
  getQuickNavs: () => safeInvoke('get-quick-navs'),
  showFolderDialog: () => safeInvoke('show-folder-dialog'),
  selectSourcePaint: (kind, defaultPath) => safeInvoke('select-source-paint', {
    kind: sourcePaintKind(kind),
    defaultPath: boundedDialogPath(defaultPath),
  }),
  selectIRacingCarFolder: (defaultPath) => safeInvoke('select-iracing-car-folder', {
    defaultPath: boundedDialogPath(defaultPath),
  }),

  // App / environment metadata
  getVersion: () => safeInvoke('app-version'),
  getServerPort: () => safeInvoke('get-server-port'),
  importForgePSD: (psdPath) => safeInvoke('forge-import-psd', psdPath),
  getGpuStatus: () => safeInvoke('gpu-status'),
  platform: process.platform,

  // External links open via main (default browser, never inside Electron)
  openExternal: (url) => safeInvoke('open-external', url),

  // Auto-update: renderer triggers download/install; progress + ready arrive
  // via the on('update-progress')/on('update-ready') subscriptions below.
  startUpdateDownload: () => safeInvoke('start-update-download'),
  installUpdate: () => safeInvoke('install-update'),

  // Dialogs
  showAbout: () => safeInvoke('show-about'),
  showError: (title, message) => safeInvoke('show-error', title, message),

  // Unsaved-work tracking — used by the quit-confirmation prompt
  setUnsaved: (hasUnsaved) => safeInvoke('set-unsaved-state', !!hasUnsaved),

  // Recent files (Windows Jump List integration on the main process)
  getRecentFiles: () => safeInvoke('get-recent-files'),
  addRecentFile: (filePath) => safeInvoke('add-recent-file', filePath),

  // Renderer-driven dev shortcuts (work even if the menu is hidden)
  reload: () => safeInvoke('request-reload'),
  hardReload: () => safeInvoke('request-hard-reload'),
  toggleDevTools: () => safeInvoke('request-toggle-devtools'),

  // 2026-06-08: full app restart (kills Python server + relaunches) so a freshly
  // downloaded Finish Pack actually registers — a page reload alone does NOT.
  restartApp: () => safeSend('spb-restart-app'),

  // Renderer log forwarding -> %APPDATA%/spb/logs/
  log: (level, ...parts) => safeInvoke('log-renderer', String(level || 'info'), parts.map(String).join(' ')),

  // Experimental iRacing native preview bridge (local installed iRacing only)
  iracingNativeStatus: () => safeInvoke('iracing-native-status'),
  iracingNativeAttach: (payload) => safeInvoke('iracing-native-attach', payload || {}),
  iracingNativeCreate: (payload) => safeInvoke('iracing-native-create', payload || {}),
  iracingNativeResize: (payload) => safeInvoke('iracing-native-resize', payload || {}),
  iracingNativeLoad: (payload) => safeInvoke('iracing-native-load', payload || {}),
  iracingNativePaint: (payload) => safeInvoke('iracing-native-paint', payload || {}),
  iracingNativeShutdown: () => safeInvoke('iracing-native-shutdown'),

  // Event subscriptions
  on: safeOn,
  send: safeSend,
});

// 2026-06-08: convenience global so the Finish Packs code can trigger a real
// restart without knowing the electronAPI shape. No-op outside Electron.
contextBridge.exposeInMainWorld('spbRestartApp', () => safeSend('spb-restart-app'));

// Backwards-compat alias used by license.html
contextBridge.exposeInMainWorld('electronLicense', {
  ipcRenderer: {
    send: (channel, ...args) => {
      // license dialog uses its own channels; allow the small known set here
      if (channel === 'license-submit' || channel === 'license-buy' || channel === 'license-quit') {
        ipcRenderer.send(channel, ...args);
      }
    },
    on: (channel, listener) => {
      if (channel === 'license-error' || channel === 'license-status') {
        ipcRenderer.on(channel, listener);
      }
    },
  },
});

// Forward uncaught renderer errors to the main process for centralized logging.
window.addEventListener('error', (e) => {
  try {
    ipcRenderer.send('renderer-crash-report', {
      kind: 'error',
      message: e.message,
      filename: e.filename,
      lineno: e.lineno,
      colno: e.colno,
      stack: e.error && e.error.stack ? String(e.error.stack) : '',
    });
  } catch (_) { /* ignore */ }
});

window.addEventListener('unhandledrejection', (e) => {
  try {
    ipcRenderer.send('renderer-crash-report', {
      kind: 'unhandledrejection',
      reason: e.reason ? String(e.reason) : '',
    });
  } catch (_) { /* ignore */ }
});

// Tell main we are alive (used to time first-paint)
window.addEventListener('DOMContentLoaded', () => {
  try { ipcRenderer.send('renderer-ready'); } catch (_) {}
});
