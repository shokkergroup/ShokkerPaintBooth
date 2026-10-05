'use strict';

const electron = require('electron');
const { app, BrowserWindow, dialog, ipcMain, Menu, shell } = electron;
const { spawn } = require('child_process');
const crypto = require('crypto');
const fs = require('fs');
const http = require('http');
const os = require('os');
const path = require('path');

const APP_ID = 'com.shokker.paintbooth.shokkdemo';
const PRODUCT_NAME = 'Shokker Paint Booth - SHOKK DEMO';
const SINGLE_INSTANCE_ID = 'com.shokker.paintbooth.shokkdemo.single-instance';
const SERVER_HOST = '127.0.0.1';
const SERVER_PORT = 59886;
const APP_ORIGIN = `http://${SERVER_HOST}:${SERVER_PORT}`;
const HEALTH_URL = `${APP_ORIGIN}/api/demo/health`;
const EXTERNAL_URLS = Object.freeze({
  payhip: 'https://payhip.com/b/AHgpV',
  discord: 'https://discord.gg/GwXxyhwtDu',
  shokker: 'https://shokkergroup.com',
});
const ALLOWED_EXTERNAL_URLS = new Set(Object.values(EXTERNAL_URLS));

// These locations are intentionally unrelated to the full product. Setting
// them before app readiness also gives Chromium and the instance lock their own
// identity, so the demo can run beside Shokker Paint Booth.
const roamingRoot = app.getPath('appData');
const localRoot = process.env.LOCALAPPDATA || roamingRoot;
const USER_DATA_DIR = path.join(roamingRoot, 'Shokker Paint Booth - SHOKK DEMO');
const CACHE_DIR = path.join(localRoot, 'Shokker Paint Booth - SHOKK DEMO', 'Cache');
const LOG_DIR = path.join(localRoot, 'Shokker Paint Booth - SHOKK DEMO', 'Logs');
const CRASH_DIR = path.join(localRoot, 'Shokker Paint Booth - SHOKK DEMO', 'Crashpad');
const LOG_FILE = path.join(LOG_DIR, 'shokk-demo.log');

for (const directory of [USER_DATA_DIR, CACHE_DIR, LOG_DIR, CRASH_DIR]) {
  fs.mkdirSync(directory, { recursive: true });
}
app.setName(PRODUCT_NAME);
app.setPath('userData', USER_DATA_DIR);
app.setPath('sessionData', CACHE_DIR);
app.setPath('crashDumps', CRASH_DIR);
app.setAppLogsPath(LOG_DIR);
app.commandLine.appendSwitch('disk-cache-dir', CACHE_DIR);
app.commandLine.appendSwitch('autoplay-policy', 'no-user-gesture-required');

function rotateLog() {
  try {
    if (fs.existsSync(LOG_FILE) && fs.statSync(LOG_FILE).size > 5 * 1024 * 1024) {
      const previous = `${LOG_FILE}.previous`;
      if (fs.existsSync(previous)) fs.unlinkSync(previous);
      fs.renameSync(LOG_FILE, previous);
    }
  } catch (_) {
    // Logging must never block startup.
  }
}

function log(message) {
  const line = `${new Date().toISOString()} ${String(message)}${os.EOL}`;
  try { fs.appendFileSync(LOG_FILE, line, 'utf8'); } catch (_) {}
}

rotateLog();
log(`[boot] ${PRODUCT_NAME} ${app.getVersion()} instance=${SINGLE_INSTANCE_ID}`);

let mainWindow = null;
let serverProcess = null;
let serverStartError = null;
let serverLaunchToken = '';
let quitting = false;
const approvedSourceFiles = new Set();
const approvedRevealRoots = new Set();

const gotInstanceLock = app.requestSingleInstanceLock({ identity: SINGLE_INSTANCE_ID });
if (!gotInstanceLock) {
  app.quit();
} else {
  app.on('second-instance', () => {
    if (!mainWindow || mainWindow.isDestroyed()) return;
    if (mainWindow.isMinimized()) mainWindow.restore();
    mainWindow.show();
    mainWindow.focus();
  });
}

function normalizedKey(candidate) {
  const resolved = path.resolve(String(candidate || ''));
  return process.platform === 'win32' ? resolved.toLowerCase() : resolved;
}

function isInside(candidate, root) {
  const relative = path.relative(path.resolve(root), path.resolve(candidate));
  return relative === '' || (!relative.startsWith('..') && !path.isAbsolute(relative));
}

function standardIRacingRoots() {
  const roots = [
    path.join(app.getPath('documents'), 'iRacing', 'paint'),
    path.join(os.homedir(), 'OneDrive', 'Documents', 'iRacing', 'paint'),
  ];
  try {
    for (const entry of fs.readdirSync(os.homedir(), { withFileTypes: true })) {
      if (entry.isDirectory() && entry.name.startsWith('OneDrive -')) {
        roots.push(path.join(os.homedir(), entry.name, 'Documents', 'iRacing', 'paint'));
      }
    }
  } catch (_) {}
  return roots.map((item) => path.resolve(item));
}

function senderIsTrusted(event) {
  try {
    return new URL(event.senderFrame.url).origin === APP_ORIGIN;
  } catch (_) {
    return false;
  }
}

function requireTrustedSender(event) {
  if (!senderIsTrusted(event)) throw new Error('Untrusted renderer request blocked.');
}

function registerIpc() {
  ipcMain.handle('shokk-demo:runtime-info', (event) => {
    requireTrustedSender(event);
    return {
      product: 'shokk-demo',
      version: app.getVersion(),
      host: SERVER_HOST,
      port: SERVER_PORT,
      origin: APP_ORIGIN,
      externalUrls: EXTERNAL_URLS,
    };
  });

  ipcMain.handle('shokk-demo:select-source-file', async (event) => {
    requireTrustedSender(event);
    const result = await dialog.showOpenDialog(mainWindow, {
      title: 'Choose a paint source',
      properties: ['openFile'],
      filters: [
        { name: 'Paint sources', extensions: ['psd', 'psb', 'tga', 'png', 'jpg', 'jpeg'] },
      ],
    });
    if (result.canceled || result.filePaths.length !== 1) return null;
    const selected = path.resolve(result.filePaths[0]);
    approvedSourceFiles.add(normalizedKey(selected));
    return selected;
  });

  ipcMain.handle('shokk-demo:select-iracing-folder', async (event) => {
    requireTrustedSender(event);
    const suggested = standardIRacingRoots().find((item) => fs.existsSync(item));
    const options = {
      title: 'Choose your iRacing paint folder',
      properties: ['openDirectory', 'createDirectory'],
    };
    if (suggested) options.defaultPath = suggested;
    const result = await dialog.showOpenDialog(mainWindow, options);
    if (result.canceled || result.filePaths.length !== 1) return null;
    const selected = path.resolve(result.filePaths[0]);
    approvedRevealRoots.add(selected);
    return selected;
  });

  ipcMain.handle('shokk-demo:open-external', async (event, requestedUrl) => {
    requireTrustedSender(event);
    const url = String(requestedUrl || '');
    if (!ALLOWED_EXTERNAL_URLS.has(url)) return false;
    await shell.openExternal(url);
    return true;
  });

  ipcMain.handle('shokk-demo:reveal-path', async (event, requestedPath) => {
    requireTrustedSender(event);
    if (typeof requestedPath !== 'string' || !requestedPath.trim() || requestedPath.length > 4096) return false;
    const target = path.resolve(requestedPath);
    const sourceApproved = approvedSourceFiles.has(normalizedKey(target));
    const revealRoots = [...standardIRacingRoots(), ...approvedRevealRoots];
    const outputApproved = revealRoots.some((root) => isInside(target, root));
    if (!sourceApproved && !outputApproved) return false;
    if (!fs.existsSync(target)) return false;
    if (fs.statSync(target).isDirectory()) {
      return (await shell.openPath(target)) === '';
    }
    shell.showItemInFolder(target);
    return true;
  });
}

function serverDirectory() {
  return app.isPackaged
    ? path.join(process.resourcesPath, 'shokk-demo-server')
    : path.resolve(__dirname, '..', 'server');
}

function pythonLaunch(serverDir) {
  const bundled = path.join(serverDir, 'python', 'python.exe');
  if (fs.existsSync(bundled)) return { command: bundled, prefixArgs: [] };
  if (app.isPackaged) {
    throw new Error(`Bundled demo Python is missing: ${bundled}`);
  }
  const configured = String(process.env.SPB_DEMO_PYTHON || '').trim();
  if (configured) return { command: configured, prefixArgs: [] };
  return process.platform === 'win32'
    ? { command: 'py', prefixArgs: ['-3'] }
    : { command: 'python3', prefixArgs: [] };
}

function startDemoServer() {
  const serverDir = serverDirectory();
  const script = path.join(serverDir, 'demo_server.py');
  if (!fs.existsSync(script)) throw new Error(`Demo server is missing: ${script}`);
  const python = pythonLaunch(serverDir);
  const launchToken = crypto.randomBytes(32).toString('hex');
  serverLaunchToken = launchToken;
  serverStartError = null;
  serverProcess = spawn(
    python.command,
    [...python.prefixArgs, script, '--host', SERVER_HOST, '--port', String(SERVER_PORT)],
    {
      cwd: serverDir,
      detached: false,
      windowsHide: true,
      shell: false,
      stdio: ['ignore', 'pipe', 'pipe'],
      env: {
        ...process.env,
        PYTHONNOUSERSITE: '1',
        PYTHONDONTWRITEBYTECODE: '1',
        PYTHONUNBUFFERED: '1',
        SPB_DEMO: '1',
        SPB_DEMO_HOST: SERVER_HOST,
        SPB_DEMO_PORT: String(SERVER_PORT),
        SPB_DEMO_USER_DATA: USER_DATA_DIR,
        SPB_DEMO_CACHE_DIR: CACHE_DIR,
        SPB_DEMO_LOG_DIR: LOG_DIR,
        SPB_DEMO_LAUNCH_TOKEN: launchToken,
      },
    },
  );
  serverProcess.stdout.on('data', (chunk) => log(`[server] ${String(chunk).trimEnd()}`));
  serverProcess.stderr.on('data', (chunk) => log(`[server:stderr] ${String(chunk).trimEnd()}`));
  serverProcess.once('error', (error) => {
    serverStartError = error;
    log(`[server:error] ${error.message}`);
  });
  serverProcess.on('exit', (code, signal) => {
    log(`[server:exit] code=${code} signal=${signal || ''}`);
    serverProcess = null;
    if (!quitting && mainWindow && !mainWindow.isDestroyed()) {
      dialog.showErrorBox(PRODUCT_NAME, 'The local demo engine stopped. Please restart SHOKK DEMO.');
      app.quit();
    }
  });
}

function readHealth() {
  return new Promise((resolve) => {
    const request = http.get(HEALTH_URL, {
      timeout: 900,
      headers: { 'X-SPB-Demo-Token': serverLaunchToken },
    }, (response) => {
      let body = '';
      response.setEncoding('utf8');
      response.on('data', (chunk) => {
        if (body.length < 65536) body += chunk;
      });
      response.on('end', () => {
        if (response.statusCode !== 200) return resolve(false);
        try {
          const payload = JSON.parse(body);
          resolve(payload.ok === true && payload.product === 'shokk-demo');
        } catch (_) {
          resolve(false);
        }
      });
    });
    request.on('timeout', () => {
      request.destroy();
      resolve(false);
    });
    request.on('error', () => resolve(false));
  });
}

function delay(milliseconds) {
  return new Promise((resolve) => setTimeout(resolve, milliseconds));
}

async function waitForDemoServer(timeoutMs = 45000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (serverStartError) throw serverStartError;
    if (!serverProcess || serverProcess.exitCode !== null) {
      throw new Error('Demo server exited before it became ready.');
    }
    if (await readHealth()) return;
    await delay(250);
  }
  throw new Error(`Demo server did not become ready at ${HEALTH_URL}.`);
}

function isLocalRuntimeUrl(rawUrl) {
  try {
    const parsed = new URL(rawUrl);
    return (parsed.protocol === 'http:' || parsed.protocol === 'ws:') &&
      parsed.hostname === SERVER_HOST && parsed.port === String(SERVER_PORT);
  } catch (_) {
    return false;
  }
}

function openAllowlistedExternal(rawUrl) {
  if (!ALLOWED_EXTERNAL_URLS.has(String(rawUrl || ''))) return false;
  shell.openExternal(rawUrl).catch((error) => log(`[external:error] ${error.message}`));
  return true;
}

function hardenSession(browserSession) {
  browserSession.setPermissionRequestHandler((_webContents, _permission, callback) => callback(false));
  browserSession.setPermissionCheckHandler(() => false);
  browserSession.webRequest.onBeforeRequest((details, callback) => {
    let cancel = false;
    try {
      const protocol = new URL(details.url).protocol;
      if (['http:', 'https:', 'ws:', 'wss:'].includes(protocol)) {
        cancel = !isLocalRuntimeUrl(details.url);
      }
    } catch (_) {
      cancel = true;
    }
    callback({ cancel });
  });
  browserSession.webRequest.onBeforeSendHeaders(
    { urls: [`${APP_ORIGIN}/*`] },
    (details, callback) => {
      details.requestHeaders['X-SPB-Demo-Token'] = serverLaunchToken;
      callback({ requestHeaders: details.requestHeaders });
    },
  );
}

async function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1720,
    height: 1000,
    minWidth: 1100,
    minHeight: 720,
    show: false,
    title: PRODUCT_NAME,
    backgroundColor: '#080d18',
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      webSecurity: true,
      allowRunningInsecureContent: false,
      webviewTag: false,
      safeDialogs: true,
      navigateOnDragDrop: false,
      devTools: false,
      spellcheck: false,
      partition: 'persist:shokk-demo-v1',
    },
  });

  hardenSession(mainWindow.webContents.session);
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    openAllowlistedExternal(url);
    return { action: 'deny' };
  });
  mainWindow.webContents.on('will-navigate', (event, url) => {
    if (isLocalRuntimeUrl(url)) return;
    event.preventDefault();
    openAllowlistedExternal(url);
  });
  mainWindow.webContents.on('will-attach-webview', (event) => event.preventDefault());
  mainWindow.once('ready-to-show', () => {
    if (mainWindow && !mainWindow.isDestroyed()) mainWindow.show();
  });
  mainWindow.on('closed', () => { mainWindow = null; });
  await mainWindow.loadURL(`${APP_ORIGIN}/`);
}

function configureUpdater() {
  if (!app.isPackaged) return;
  try {
    const { autoUpdater } = require('electron-updater');
    autoUpdater.autoDownload = true;
    autoUpdater.autoInstallOnAppQuit = true;
    autoUpdater.channel = 'shokk-demo';
    autoUpdater.logger = {
      info: (message) => log(`[update] ${message}`),
      warn: (message) => log(`[update:warn] ${message}`),
      error: (message) => log(`[update:error] ${message}`),
      debug: (message) => log(`[update:debug] ${message}`),
    };
    autoUpdater.on('error', (error) => log(`[update:error] ${error.message}`));
    setTimeout(() => {
      autoUpdater.checkForUpdatesAndNotify().catch((error) => log(`[update:error] ${error.message}`));
    }, 2500);
  } catch (error) {
    log(`[update:init-error] ${error.message}`);
  }
}

function stopDemoServer() {
  if (!serverProcess) return;
  const child = serverProcess;
  serverProcess = null;
  try { child.kill(); } catch (_) {}
}

app.on('before-quit', () => {
  quitting = true;
  stopDemoServer();
});

app.on('window-all-closed', () => app.quit());

if (gotInstanceLock) {
  app.whenReady().then(async () => {
    app.setAppUserModelId(APP_ID);
    Menu.setApplicationMenu(null);
    registerIpc();
    startDemoServer();
    await waitForDemoServer();
    await createWindow();
    configureUpdater();
  }).catch((error) => {
    log(`[fatal] ${error && error.stack ? error.stack : error}`);
    dialog.showErrorBox(PRODUCT_NAME, `SHOKK DEMO could not start.\n\n${error.message || error}`);
    app.quit();
  });
}
