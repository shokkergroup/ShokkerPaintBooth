// main.js — Shokker Paint Booth Electron host.
// Improvements layered on top of the existing license + bundled-Python flow.
// PRESERVED: license/Payhip flow, bundled Python preference, zombie cleanup,
//            graceful shutdown, NSIS-friendly app behavior.

// ===== Memory budget for the main process (helps Chromium GC under load) =====
// Must be set before V8 initializes anything heavy (see app.commandLine below).

const electron = require('electron');
const { app, BrowserWindow, dialog, ipcMain, Menu, Tray, shell, session, nativeImage, crashReporter, powerSaveBlocker, screen } = electron;
const { spawn } = require('child_process');
const path = require('path');
const net = require('net');
const fs = require('fs');
const os = require('os');
const https = require('https');
const http = require('http');
const crypto = require('crypto');
const { autoUpdater } = require('electron-updater');

// ----- IMPROVEMENT #19: Bigger old-space for the main process under load -----
app.commandLine.appendSwitch('js-flags', '--max-old-space-size=4096');

// ----- IMPROVEMENT #33: Accessibility flags (screen-reader hints) -----
try { app.setAccessibilitySupportEnabled(true); } catch (_) { /* older electron */ }

// ----- IMPROVEMENT #34: GPU / hardware acceleration tuning -----
// On Windows, ANGLE D3D11 is the most stable backend for Chromium today.
app.commandLine.appendSwitch('use-angle', 'd3d11');
app.commandLine.appendSwitch('enable-features', 'CanvasOopRasterization,UseSkiaRenderer');
// Some integrated GPUs choke on hardware acceleration. The user can disable
// it by creating an empty file at %APPDATA%/ShokkerPaintBooth/disable-gpu.flag
try {
  const flagPath = path.join(process.env.APPDATA || os.homedir(), 'ShokkerPaintBooth', 'disable-gpu.flag');
  if (fs.existsSync(flagPath)) {
    app.disableHardwareAcceleration();
    console.log('[GPU] Hardware acceleration disabled via flag file');
  }
} catch (_) { /* ignore */ }

// ----- IMPROVEMENT #15: Single-instance lock — prevent two SPB windows -----
// DEV ESCAPE HATCH: side-by-side dev sessions (e.g. alternate port, debug build)
// can bypass the lock with any of:
//   --allow-multiple-instances  CLI flag
//   SPB_ALLOW_MULTIPLE_INSTANCES=1  env var
//   SPB_DEV_PORT=<port>  env var (implies dev mode)
//   a sentinel file at %APPDATA%/ShokkerPaintBooth/allow-multiple-instances.flag
// The escape hatch is LOGGED so it is obvious in shipping/packaged bug reports
// when a second instance slipped through.
const _allowMultiByArg = Array.isArray(process.argv) && process.argv.some(a =>
  a === '--allow-multiple-instances' || a === '--allow-multiple' || a === '--multi-instance'
);
const _allowMultiByEnv = (process.env.SPB_ALLOW_MULTIPLE_INSTANCES === '1'
  || !!process.env.SPB_DEV_PORT
  || process.env.SPB_DEV_MODE === '1');
let _allowMultiByFlagFile = false;
try {
  const _multiFlagPath = path.join(process.env.APPDATA || os.homedir(), 'ShokkerPaintBooth', 'allow-multiple-instances.flag');
  _allowMultiByFlagFile = fs.existsSync(_multiFlagPath);
} catch (_) { /* ignore */ }
const DEV_ALLOW_MULTIPLE = _allowMultiByArg || _allowMultiByEnv || _allowMultiByFlagFile;

if (DEV_ALLOW_MULTIPLE) {
  console.log('[Lifecycle] Single-instance lock BYPASSED (dev mode) —',
    'arg=' + _allowMultiByArg, 'env=' + _allowMultiByEnv, 'flag=' + _allowMultiByFlagFile);
} else {
  const gotInstanceLock = app.requestSingleInstanceLock();
  if (!gotInstanceLock) {
    console.log('[Lifecycle] Another SPB instance is already running — quitting.');
    console.log('[Lifecycle] To allow multiple instances for development, use one of:');
    console.log('[Lifecycle]   --allow-multiple-instances  (CLI flag)');
    console.log('[Lifecycle]   SPB_ALLOW_MULTIPLE_INSTANCES=1  (env var)');
    console.log('[Lifecycle]   SPB_DEV_PORT=<port>  (env var, also implies alt port)');
    console.log('[Lifecycle]   touch %APPDATA%/ShokkerPaintBooth/allow-multiple-instances.flag');
    app.quit();
    process.exit(0);
  }
}

let mainWindow = null;
let serverProcess = null;
let serverPort = 59876;
let tray = null;
let splashWindow = null;
let serverReady = false;
let unsavedWork = false;
let quitInProgress = false;
let serverRestartCount = 0;
let watchdogTimer = null;
let powerSaveBlockerId = null;

// ===== IMPROVEMENT #20: Logs in %APPDATA%/spb/logs/ (rotating) =====
const APP_DATA_DIR = path.join(process.env.APPDATA || os.homedir(), 'ShokkerPaintBooth');
const LOG_DIR = path.join(APP_DATA_DIR, 'logs');
const WINDOW_STATE_FILE = path.join(APP_DATA_DIR, 'window-state.json');
const RECENT_FILES_FILE = path.join(APP_DATA_DIR, 'recent-files.json');
try { if (!fs.existsSync(LOG_DIR)) fs.mkdirSync(LOG_DIR, { recursive: true }); } catch (_) {}

const LOG_FILE = path.join(LOG_DIR, `spb-${new Date().toISOString().substring(0, 10)}.log`);
// Legacy debug log path kept for the existing TIMEOUT dialog message
const DEBUG_LOG = path.join(os.tmpdir(), 'shokker-debug.log');

// Rotate: keep at most 10 daily logs.
function rotateLogs() {
  try {
    const files = fs.readdirSync(LOG_DIR)
      .filter((f) => f.startsWith('spb-') && f.endsWith('.log'))
      .sort()
      .reverse();
    for (let i = 10; i < files.length; i++) {
      try { fs.unlinkSync(path.join(LOG_DIR, files[i])); } catch (_) {}
    }
  } catch (_) {}
}
rotateLogs();

function debugLog(msg) {
  const ts = new Date().toISOString().substring(11, 23);
  const line = `[${ts}] ${msg}\n`;
  try { fs.appendFileSync(LOG_FILE, line); } catch (_) {}
  try { fs.appendFileSync(DEBUG_LOG, line); } catch (_) {}
  console.log(msg);
}
try { fs.writeFileSync(DEBUG_LOG, ''); } catch (_) {}
debugLog(`[Boot] SPB v${app.getVersion()} on ${process.platform} ${os.release()} (Electron ${process.versions.electron})`);

// ===== IMPROVEMENT #21: Crash reporter for renderer/GPU process crashes =====
try {
  crashReporter.start({
    productName: 'ShokkerPaintBooth',
    companyName: 'Shokker Group',
    submitURL: 'https://localhost/_no_upload', // local-only; we just want dumps on disk
    uploadToServer: false,
    ignoreSystemCrashHandler: false,
    extra: { version: app.getVersion() },
  });
  debugLog(`[Crash] Reporter active. Dumps: ${app.getPath('crashDumps')}`);
} catch (e) {
  debugLog(`[Crash] Reporter init failed: ${e.message}`);
}

// ===== LICENSE KEY SYSTEM (preserved) =====
const LICENSE_DIR = APP_DATA_DIR;
const LICENSE_FILE = path.join(LICENSE_DIR, 'license.dat');
const ENCRYPTION_KEY = 'ShokkerPaintBooth2026AlphaKeyXX!'; // 32 bytes for AES-256
const PAYHIP_PRODUCT_SECRET = 'prod_sk_AHgpV_96ce6d7689c295ed34e27dea31906d74171de8c1';

function encryptData(data) {
  const iv = crypto.randomBytes(16);
  const cipher = crypto.createCipheriv('aes-256-cbc', Buffer.from(ENCRYPTION_KEY, 'utf8'), iv);
  let encrypted = cipher.update(JSON.stringify(data), 'utf8', 'hex');
  encrypted += cipher.final('hex');
  return iv.toString('hex') + ':' + encrypted;
}

function decryptData(raw) {
  try {
    const [ivHex, encrypted] = raw.split(':');
    const iv = Buffer.from(ivHex, 'hex');
    const decipher = crypto.createDecipheriv('aes-256-cbc', Buffer.from(ENCRYPTION_KEY, 'utf8'), iv);
    let decrypted = decipher.update(encrypted, 'hex', 'utf8');
    decrypted += decipher.final('utf8');
    return JSON.parse(decrypted);
  } catch (e) {
    return null;
  }
}

function getMachineId() {
  return crypto.createHash('sha256')
    .update(os.hostname() + os.userInfo().username + os.homedir())
    .digest('hex').substring(0, 16);
}

function readLocalLicense() {
  try {
    if (!fs.existsSync(LICENSE_FILE)) return null;
    const raw = fs.readFileSync(LICENSE_FILE, 'utf8');
    const data = decryptData(raw);
    if (!data) return null;
    if (data.machineId !== getMachineId()) {
      console.log('[License] Machine ID mismatch - activation invalid on this device');
      return null;
    }
    return data;
  } catch (e) {
    console.log('[License] Failed to read local license:', e.message);
    return null;
  }
}

function saveLocalLicense(licenseKey, email) {
  try {
    if (!fs.existsSync(LICENSE_DIR)) fs.mkdirSync(LICENSE_DIR, { recursive: true });
    const data = {
      licenseKey,
      email: email || '',
      machineId: getMachineId(),
      activatedAt: new Date().toISOString(),
      lastVerified: new Date().toISOString()
    };
    fs.writeFileSync(LICENSE_FILE, encryptData(data), 'utf8');
    console.log('[License] Activation saved locally');
    return true;
  } catch (e) {
    console.log('[License] Failed to save license:', e.message);
    return false;
  }
}

function verifyWithPayhip(licenseKey) {
  return new Promise((resolve) => {
    const url = `https://payhip.com/api/v2/license/verify?license_key=${encodeURIComponent(licenseKey)}`;
    const req = https.request(url, {
      method: 'GET',
      headers: { 'product-secret-key': PAYHIP_PRODUCT_SECRET }
    }, (res) => {
      let body = '';
      res.on('data', (chunk) => body += chunk);
      res.on('end', () => {
        try {
          const json = JSON.parse(body);
          if (json.data && json.data.enabled) {
            resolve({
              valid: true,
              email: json.data.buyer_email || '',
              uses: json.data.uses || 0,
              productName: json.data.product_name || ''
            });
          } else {
            resolve({ valid: false, reason: 'License key is disabled or invalid' });
          }
        } catch (e) {
          resolve({ valid: false, reason: 'Invalid response from license server' });
        }
      });
    });
    req.on('error', (err) => {
      console.log('[License] Payhip API error:', err.message);
      resolve({ valid: false, networkError: true, reason: 'Could not reach license server. Check your internet connection.' });
    });
    req.setTimeout(10000, () => {
      req.destroy();
      resolve({ valid: false, networkError: true, reason: 'License server timed out. Check your internet connection.' });
    });
    req.end();
  });
}

function incrementPayhipUsage(licenseKey) {
  return new Promise((resolve) => {
    const postData = JSON.stringify({ license_key: licenseKey });
    const req = https.request('https://payhip.com/api/v2/license/usage', {
      method: 'PUT',
      headers: {
        'product-secret-key': PAYHIP_PRODUCT_SECRET,
        'Content-Type': 'application/json',
        'Content-Length': postData.length
      }
    }, (res) => {
      let body = '';
      res.on('data', (chunk) => body += chunk);
      res.on('end', () => resolve(true));
    });
    req.on('error', () => resolve(false));
    req.setTimeout(10000, () => { req.destroy(); resolve(false); });
    req.write(postData);
    req.end();
  });
}

function showLicenseDialog() {
  return new Promise((resolve) => {
    let resolved = false;
    function safeResolve(val) {
      if (resolved) return;
      resolved = true;
      resolve(val);
    }

    const licenseWin = new BrowserWindow({
      width: 520,
      height: 420,
      resizable: false,
      minimizable: false,
      maximizable: false,
      title: 'Shokker Paint Booth - Activate',
      backgroundColor: '#0a0a0a',
      autoHideMenuBar: true,
      webPreferences: {
        nodeIntegration: false,
        contextIsolation: true,
        sandbox: false,
        preload: path.join(__dirname, 'license-preload.js')
      }
    });

    debugLog('[Dialog] License window created, loading license.html');

    ipcMain.once('license-submit', async (_event, key) => {
      debugLog(`[Dialog] Received license-submit with key: ${(key || '').substring(0, 5)}...`);
      const trimmedKey = (key || '').trim();
      if (!trimmedKey) {
        licenseWin.webContents.send('license-error', 'Please enter a license key.');
        ipcMain.once('license-submit', arguments.callee);
        return;
      }

      licenseWin.webContents.send('license-status', 'Verifying...');

      const result = await verifyWithPayhip(trimmedKey);
      if (result.valid) {
        await incrementPayhipUsage(trimmedKey);
        saveLocalLicense(trimmedKey, result.email);
        safeResolve(true);
        licenseWin.close();
      } else {
        licenseWin.webContents.send('license-error', result.reason || 'Invalid license key.');
        const retryHandler = async (_ev, retryKey) => {
          const rk = (retryKey || '').trim();
          if (!rk) {
            licenseWin.webContents.send('license-error', 'Please enter a license key.');
            ipcMain.once('license-submit', retryHandler);
            return;
          }
          licenseWin.webContents.send('license-status', 'Verifying...');
          const r2 = await verifyWithPayhip(rk);
          if (r2.valid) {
            await incrementPayhipUsage(rk);
            saveLocalLicense(rk, r2.email);
            safeResolve(true);
            licenseWin.close();
          } else {
            licenseWin.webContents.send('license-error', r2.reason || 'Invalid license key.');
            ipcMain.once('license-submit', retryHandler);
          }
        };
        ipcMain.once('license-submit', retryHandler);
      }
    });

    ipcMain.once('license-buy', () => {
      shell.openExternal('https://payhip.com/b/AHgpV');
    });

    ipcMain.once('license-quit', () => {
      safeResolve(false);
      licenseWin.close();
    });

    licenseWin.on('closed', () => {
      debugLog('[Dialog] License window closed event fired');
      ipcMain.removeAllListeners('license-submit');
      ipcMain.removeAllListeners('license-quit');
      ipcMain.removeAllListeners('license-buy');
      safeResolve(false);
    });

    licenseWin.loadFile(path.join(__dirname, 'license.html'));
  });
}

async function checkLicenseAndActivate() {
  const local = readLocalLicense();
  if (local) {
    console.log(`[License] Valid local activation found (key: ${local.licenseKey.substring(0, 5)}...)`);
    const lastVerified = new Date(local.lastVerified);
    const daysSince = (Date.now() - lastVerified.getTime()) / (1000 * 60 * 60 * 24);
    if (daysSince > 7) {
      console.log('[License] Re-verifying with Payhip (last check was', Math.round(daysSince), 'days ago)');
      const result = await verifyWithPayhip(local.licenseKey);
      if (result.valid) {
        saveLocalLicense(local.licenseKey, local.email);
        return true;
      } else if (result.networkError) {
        console.log('[License] Re-verification skipped (network error) — keeping local license:', result.reason);
        return true;
      } else {
        console.log('[License] Re-verification failed (server rejected) - clearing local license');
        try { fs.unlinkSync(LICENSE_FILE); } catch (_) {}
      }
    } else {
      return true;
    }
  }

  debugLog('[License] No valid activation found, showing license dialog');
  const activated = await showLicenseDialog();
  debugLog(`[License] showLicenseDialog returned: ${activated}`);
  return activated;
}

// ===== IPC: Direct filesystem browsing (bypasses server entirely) =====
ipcMain.handle('list-dir', async (_event, dirPath, filter) => {
  try {
    if (!dirPath) return null;
    const resolved = path.resolve(dirPath);
    if (!fs.existsSync(resolved) || !fs.statSync(resolved).isDirectory()) {
      return { error: 'Not a directory: ' + resolved };
    }
    const entries = fs.readdirSync(resolved, { withFileTypes: true });
    const folders = [];
    const files = [];
    const MAX_FILES = 200;
    let totalFiles = 0;
    const isLarge = entries.length > 300;

    for (const entry of entries) {
      if (entry.name.startsWith('.')) continue;
      if (entry.isDirectory()) {
        folders.push({
          name: entry.name,
          path: path.join(resolved, entry.name).replace(/\\/g, '/'),
          type: 'folder'
        });
      } else {
        if (isLarge) continue;
        const lname = entry.name.toLowerCase();
        if (filter && !lname.endsWith(filter.toLowerCase())) continue;
        totalFiles++;
        if (files.length < MAX_FILES) {
          let size = 0;
          try { size = fs.statSync(path.join(resolved, entry.name)).size; } catch (_) {}
          files.push({
            name: entry.name,
            path: path.join(resolved, entry.name).replace(/\\/g, '/'),
            type: 'file',
            size,
            size_human: size > 0 ? Math.round(size / 1024) + ' KB' : '0'
          });
        }
      }
    }

    folders.sort((a, b) => a.name.toLowerCase().localeCompare(b.name.toLowerCase()));
    files.sort((a, b) => a.name.toLowerCase().localeCompare(b.name.toLowerCase()));

    const parentDir = path.dirname(resolved);
    const parentPath = parentDir !== resolved ? parentDir.replace(/\\/g, '/') : '';

    return {
      path: resolved.replace(/\\/g, '/'),
      parent: parentPath,
      items: folders.concat(files),
      total_folders: folders.length,
      total_files: totalFiles,
      hidden_files: isLarge ? -1 : totalFiles - files.length,
      large_dir: isLarge,
      entry_count: entries.length,
    };
  } catch (err) {
    return { error: err.message };
  }
});

ipcMain.handle('show-folder-dialog', async () => {
  const result = await dialog.showOpenDialog({
    properties: ['openDirectory'],
    title: 'Select PS Export Folder',
  });
  if (result.canceled || !result.filePaths || result.filePaths.length === 0) return null;
  return result.filePaths[0].replace(/\\/g, '/');
});

ipcMain.handle('get-quick-navs', async () => {
  const drives = [];
  for (const letter of 'CDEFGHIJKLMNOPQRSTUVWXYZ') {
    const drive = letter + ':/';
    if (fs.existsSync(drive)) drives.push({ name: letter + ':', path: drive, type: 'drive' });
  }
  const quick_navs = [];

  const home = os.homedir();
  const iracingCandidates = [
    path.join(home, 'Documents', 'iRacing', 'paint'),
    path.join(home, 'OneDrive', 'Documents', 'iRacing', 'paint'),
  ];

  try {
    const homeEntries = fs.readdirSync(home, { withFileTypes: true });
    for (const entry of homeEntries) {
      if (entry.isDirectory() && entry.name.startsWith('OneDrive -') || entry.name.startsWith('OneDrive-')) {
        iracingCandidates.push(path.join(home, entry.name, 'Documents', 'iRacing', 'paint'));
      }
    }
  } catch (_) {}

  if (process.env.USERPROFILE && process.env.USERPROFILE !== home) {
    iracingCandidates.push(path.join(process.env.USERPROFILE, 'Documents', 'iRacing', 'paint'));
  }

  let iracingFound = false;
  for (const candidate of iracingCandidates) {
    try {
      if (fs.existsSync(candidate) && fs.statSync(candidate).isDirectory()) {
        quick_navs.push({ name: 'iRacing Paint Folder', path: candidate.replace(/\\/g, '/'), type: 'shortcut' });
        console.log(`[QuickNav] iRacing paint folder found: ${candidate}`);
        iracingFound = true;
        break;
      }
    } catch (_) {}
  }
  if (!iracingFound) {
    console.log('[QuickNav] iRacing paint folder not found in any standard location');
  }

  return { drives, quick_navs };
});

// ----- IMPROVEMENT #38: Server port available to renderer over IPC -----
ipcMain.handle('get-server-port', () => serverPort);

// ----- IMPROVEMENT #13/26: About dialog + external links -----
ipcMain.handle('app-version', () => app.getVersion());
ipcMain.handle('open-external', async (_e, url) => {
  if (!/^https?:\/\//i.test(String(url || ''))) return false;
  await shell.openExternal(url);
  return true;
});

ipcMain.handle('show-about', () => {
  showAboutDialog();
  return true;
});

ipcMain.handle('show-error', (_e, title, message) => {
  dialog.showErrorBox(String(title || 'Error'), String(message || ''));
  return true;
});

// ----- IMPROVEMENT #14: Renderer can declare unsaved work -----
ipcMain.handle('set-unsaved-state', (_e, hasUnsaved) => {
  unsavedWork = !!hasUnsaved;
  if (mainWindow) mainWindow.setDocumentEdited(unsavedWork);
  return true;
});

// ----- IMPROVEMENT #29: Recent files / Jump List -----
function readRecentFiles() {
  try {
    if (!fs.existsSync(RECENT_FILES_FILE)) return [];
    const list = JSON.parse(fs.readFileSync(RECENT_FILES_FILE, 'utf8'));
    return Array.isArray(list) ? list.slice(0, 10) : [];
  } catch (_) { return []; }
}
function writeRecentFiles(list) {
  try { fs.writeFileSync(RECENT_FILES_FILE, JSON.stringify(list.slice(0, 10), null, 2), 'utf8'); } catch (_) {}
}
function refreshJumpList() {
  if (process.platform !== 'win32') return;
  const recent = readRecentFiles();
  try {
    app.setJumpList([
      {
        type: 'custom',
        name: 'Recent Paints',
        items: recent.map((p) => ({
          type: 'task',
          title: path.basename(p),
          program: process.execPath,
          args: `"${p}"`,
          description: p,
        })),
      },
      { type: 'recent' },
    ]);
  } catch (e) {
    debugLog(`[JumpList] setJumpList failed: ${e.message}`);
  }
}
ipcMain.handle('get-recent-files', () => readRecentFiles());
ipcMain.handle('add-recent-file', (_e, filePath) => {
  if (!filePath) return false;
  const list = readRecentFiles().filter((p) => p !== filePath);
  list.unshift(filePath);
  writeRecentFiles(list);
  try { app.addRecentDocument(filePath); } catch (_) {}
  refreshJumpList();
  return true;
});

// ----- IMPROVEMENT #6/7/8: Renderer-driven dev shortcuts -----
ipcMain.handle('request-reload', () => {
  if (mainWindow && !mainWindow.isDestroyed()) mainWindow.webContents.reload();
  return true;
});
ipcMain.handle('request-hard-reload', async () => {
  if (mainWindow && !mainWindow.isDestroyed()) {
    try { await mainWindow.webContents.session.clearCache(); } catch (_) {}
    mainWindow.webContents.reloadIgnoringCache();
  }
  return true;
});
ipcMain.handle('request-toggle-devtools', () => {
  if (mainWindow && !mainWindow.isDestroyed()) mainWindow.webContents.toggleDevTools();
  return true;
});

// ----- IMPROVEMENT #20/39: Renderer log forwarding -----
ipcMain.handle('log-renderer', (_e, level, message) => {
  debugLog(`[Renderer:${level}] ${message}`);
  return true;
});

// ----- IMPROVEMENT #21 (renderer side): crash report channel -----
ipcMain.on('renderer-crash-report', (_e, payload) => {
  try { debugLog(`[Renderer:CRASH] ${JSON.stringify(payload).slice(0, 2000)}`); } catch (_) {}
});

ipcMain.on('renderer-ready', () => {
  debugLog('[Renderer] DOMContentLoaded fired');
});

// ===== ZOMBIE SERVERS (preserved) =====
function killZombieServers() {
  return new Promise((resolve) => {
    const { execSync } = require('child_process');
    try {
      execSync('taskkill /F /IM shokker-paint-booth-v5.exe /T 2>nul', { windowsHide: true, timeout: 5000 });
      debugLog('[Zombie] Killed old V5 zombies');
    } catch (_) {}
    try {
      const myPid = process.pid;
      const result = execSync(`netstat -ano | findstr :${serverPort} | findstr LISTENING`,
        { encoding: 'utf-8', windowsHide: true, timeout: 5000 });
      const lines = result.trim().split('\n');
      for (const line of lines) {
        const parts = line.trim().split(/\s+/);
        const pid = parseInt(parts[parts.length - 1]);
        if (pid && pid !== myPid && pid > 4) {
          execSync(`taskkill /F /PID ${pid} 2>nul`, { windowsHide: true, timeout: 3000 });
          debugLog(`[Zombie] Killed process ${pid} on port ${serverPort}`);
        }
      }
    } catch (_) {}

    // ----- IMPROVEMENT #36: Sweep orphaned python processes that match our cwd -----
    try {
      const { execSync } = require('child_process');
      const wmic = execSync('wmic process where "name=\'python.exe\'" get ProcessId,CommandLine /format:csv',
        { encoding: 'utf-8', windowsHide: true, timeout: 5000 });
      const lines = wmic.split('\n').filter((l) => l.includes('server_v5.py'));
      for (const line of lines) {
        const parts = line.trim().split(',');
        const pid = parseInt(parts[parts.length - 1]);
        if (pid && pid !== process.pid && pid > 4) {
          try { execSync(`taskkill /F /PID ${pid} 2>nul`, { windowsHide: true, timeout: 3000 }); } catch (_) {}
          debugLog(`[Zombie] Killed orphaned server_v5.py python pid ${pid}`);
        }
      }
    } catch (_) { /* wmic missing on newer Windows — ignore */ }

    debugLog('[Zombie] Cleanup done');
    setTimeout(resolve, 500);
  });
}

// ===== BUNDLED PYTHON PATH (preserved) =====
function getBundledPythonPath() {
  const candidates = [
    path.join(process.resourcesPath, 'server', 'python', 'python.exe'),
    path.join(__dirname, 'server', 'python', 'python.exe'),
  ];
  for (const p of candidates) {
    if (fs.existsSync(p)) {
      debugLog(`[Server] Found bundled Python at: ${p}`);
      return p;
    }
  }
  return null;
}

function getServerDir() {
  const packaged = path.join(process.resourcesPath, 'server');
  if (fs.existsSync(path.join(packaged, 'server_v5.py'))) return packaged;
  const dev = path.join(__dirname, 'server');
  if (fs.existsSync(path.join(dev, 'server_v5.py'))) return dev;
  return path.join(__dirname, 'server');
}

// ===== IMPROVEMENT #17: PORT detection — try multiple ports if 59876 busy =====
function isPortFree(port) {
  return new Promise((resolve) => {
    const tester = net.createServer()
      .once('error', () => resolve(false))
      .once('listening', () => tester.close(() => resolve(true)))
      .listen(port, '127.0.0.1');
  });
}
async function pickServerPort() {
  // DEV ESCAPE HATCH: SPB_DEV_PORT lets a developer pin a specific port so two
  // side-by-side instances don't collide. If the requested port is unavailable
  // we log and fall through to the default scan.
  const devPortRaw = process.env.SPB_DEV_PORT;
  if (devPortRaw) {
    const devPort = parseInt(devPortRaw, 10);
    if (Number.isFinite(devPort) && devPort > 0 && devPort < 65536) {
      if (await isPortFree(devPort)) {
        debugLog(`[Server] Using dev-pinned port ${devPort} (SPB_DEV_PORT)`);
        return devPort;
      }
      debugLog(`[Server] SPB_DEV_PORT=${devPort} busy — falling back to default scan`);
    }
  }
  const tryOrder = [59876, 59877, 59878, 59879, 0]; // last resort: ephemeral
  for (const p of tryOrder) {
    if (p === 0) {
      // ephemeral — actually grab one
      const ephemeral = await new Promise((resolve) => {
        const s = net.createServer();
        s.listen(0, '127.0.0.1', () => {
          const port = s.address().port;
          s.close(() => resolve(port));
        });
      });
      debugLog(`[Server] Falling back to ephemeral port ${ephemeral}`);
      return ephemeral;
    }
    if (await isPortFree(p)) return p;
    debugLog(`[Server] Port ${p} busy, trying next`);
  }
  return 59876;
}

// ===== START PYTHON SERVER (preserved bundled-Python preference) =====
function startServer(port) {
  return new Promise((resolve, reject) => {
    const serverDir = getServerDir();
    const bundledPython = getBundledPythonPath();

    let spawnExe, spawnArgs, spawnCwd, spawnEnv;

    if (bundledPython) {
      debugLog(`[Server] Using bundled Python: ${bundledPython}`);
      spawnExe = bundledPython;
      spawnArgs = ['server_v5.py'];
      spawnCwd = serverDir;
      spawnEnv = Object.assign({}, process.env, { SHOKKER_PORT: String(port) });
    } else {
      debugLog('[Server] No bundled Python found, trying system Python');
      spawnExe = 'python';
      spawnArgs = ['server_v5.py'];
      spawnCwd = serverDir;
      spawnEnv = Object.assign({}, process.env, { SHOKKER_PORT: String(port) });
    }

    debugLog(`[Server] Server dir: ${serverDir}`);

    serverProcess = spawn(spawnExe, spawnArgs, {
      env: spawnEnv,
      cwd: spawnCwd,
      stdio: ['ignore', 'pipe', 'pipe'],
      windowsHide: true,
      detached: false
    });

    if (serverProcess.stdout) {
      serverProcess.stdout.on('data', (data) => {
        const lines = data.toString().split('\n').filter((l) => l.trim());
        for (const line of lines.slice(0, 5)) debugLog(`[Server:out] ${line.trim()}`);
      });
    }
    if (serverProcess.stderr) {
      serverProcess.stderr.on('data', (data) => {
        const lines = data.toString().split('\n').filter((l) => l.trim());
        for (const line of lines.slice(0, 10)) debugLog(`[Server:err] ${line.trim()}`);
      });
    }

    serverProcess.on('error', (err) => {
      debugLog(`[Server] ERROR: Failed to start: ${err.message}`);
      reject(err);
    });

    serverProcess.on('exit', (code) => {
      debugLog(`[Server] Exited with code ${code}`);
      if (code !== 0 && code !== null) {
        debugLog(`[Server] CRASH DETECTED: Python server exited with code ${code}`);
      }
      serverProcess = null;
      serverReady = false;
      updateTrayServerStatus(false);
    });

    const startTime = Date.now();
    const pollInterval = setInterval(() => {
      const sock = new net.Socket();
      sock.setTimeout(300);
      sock.once('connect', () => {
        sock.destroy();
        clearInterval(pollInterval);
        console.log(`[Electron] Server ready on port ${port} (${Date.now() - startTime}ms)`);
        serverReady = true;
        updateTrayServerStatus(true);
        resolve(port);
      });
      sock.once('error', () => sock.destroy());
      sock.once('timeout', () => sock.destroy());
      sock.connect(port, '127.0.0.1');
    }, 250);

    setTimeout(() => {
      clearInterval(pollInterval);
      debugLog('[Server] TIMEOUT: Server did not respond after 60 seconds');
      if (serverProcess && serverProcess.exitCode === null) {
        debugLog('[Server] Process is still running — resolving anyway');
        resolve(port);
      } else {
        debugLog('[Server] Process is DEAD — showing error dialog');
        dialog.showErrorBox('Shokker Paint Booth - Server Failed',
          'The Python engine failed to start.\n\n' +
          'Check the debug log at:\n' + LOG_FILE + '\n\n' +
          'Common causes:\n' +
          '• Antivirus blocking python.exe\n' +
          '• Missing Visual C++ Redistributable\n' +
          '• Port ' + port + ' in use by another app');
        resolve(port);
      }
    }, 60000);
  });
}

// ----- IMPROVEMENT #4: Retry helper around startServer -----
async function startServerWithRetry(port, attempts = 3) {
  let lastErr = null;
  for (let i = 1; i <= attempts; i++) {
    try {
      await startServer(port);
      return;
    } catch (e) {
      lastErr = e;
      debugLog(`[Server] Attempt ${i}/${attempts} failed: ${e.message}`);
      if (i < attempts) await new Promise((r) => setTimeout(r, 1500 * i));
    }
  }
  throw lastErr || new Error('Server failed to start after retries');
}

// ----- IMPROVEMENT #18: Watchdog — restart hung server -----
function startWatchdog() {
  if (watchdogTimer) clearInterval(watchdogTimer);
  watchdogTimer = setInterval(() => {
    if (!serverProcess) return; // already exited; on-exit handler will deal
    const sock = new net.Socket();
    sock.setTimeout(2500);
    sock.once('connect', () => { sock.destroy(); /* alive */ });
    sock.once('timeout', () => {
      sock.destroy();
      debugLog('[Watchdog] Server health check timed out — restarting');
      restartServer();
    });
    sock.once('error', () => {
      sock.destroy();
      if (serverProcess) {
        debugLog('[Watchdog] Server unreachable — restarting');
        restartServer();
      }
    });
    sock.connect(serverPort, '127.0.0.1');
  }, 30000);
}

async function restartServer() {
  if (serverRestartCount >= 3) {
    debugLog('[Watchdog] Restart cap reached (3); giving up');
    return;
  }
  serverRestartCount++;
  try {
    if (serverProcess && serverProcess.pid) {
      const { execSync } = require('child_process');
      try { execSync(`taskkill /F /PID ${serverProcess.pid} /T 2>nul`, { windowsHide: true, timeout: 3000 }); } catch (_) {}
    }
    serverProcess = null;
    serverReady = false;
    updateTrayServerStatus(false);
    await startServerWithRetry(serverPort, 2);
    debugLog('[Watchdog] Server restarted');
  } catch (e) {
    debugLog(`[Watchdog] Restart failed: ${e.message}`);
  }
}

// ===== IMPROVEMENT #1/22/23: Window state persistence + minimum size =====
function readWindowState() {
  try {
    if (!fs.existsSync(WINDOW_STATE_FILE)) return null;
    const state = JSON.parse(fs.readFileSync(WINDOW_STATE_FILE, 'utf8'));
    return state && typeof state === 'object' ? state : null;
  } catch (_) { return null; }
}
function writeWindowState(state) {
  try { fs.writeFileSync(WINDOW_STATE_FILE, JSON.stringify(state, null, 2), 'utf8'); } catch (_) {}
}
function clampToDisplay(state) {
  // ----- IMPROVEMENT #2: Multi-monitor — ensure window lands on a real display -----
  try {
    const displays = screen.getAllDisplays();
    const onScreen = displays.some((d) => {
      const b = d.workArea;
      return state.x >= b.x - 50 && state.x < b.x + b.width - 50 &&
             state.y >= b.y - 50 && state.y < b.y + b.height - 50;
    });
    if (!onScreen) {
      const primary = screen.getPrimaryDisplay().workArea;
      state.x = primary.x + Math.max(0, Math.floor((primary.width - state.width) / 2));
      state.y = primary.y + Math.max(0, Math.floor((primary.height - state.height) / 2));
    }
  } catch (_) {}
  return state;
}

// ===== IMPROVEMENT #24: Icon resolution with high-DPI fallback =====
function loadAppIcon() {
  const candidates = [
    path.join(__dirname, 'shokker-icon.ico'),
    path.join(__dirname, 'icon.ico'),
    path.join(__dirname, 'icon.png'),
    path.join(process.resourcesPath || '', 'shokker-icon.ico'),
  ];
  for (const p of candidates) {
    try {
      if (fs.existsSync(p)) {
        const img = nativeImage.createFromPath(p);
        if (!img.isEmpty()) return img;
      }
    } catch (_) {}
  }
  return undefined;
}

// ===== IMPROVEMENT #5: System tray with server status =====
function buildTrayMenu() {
  return Menu.buildFromTemplate([
    { label: serverReady ? 'Server: Running' : 'Server: Stopped', enabled: false },
    { type: 'separator' },
    { label: 'Show Window', click: () => {
      if (mainWindow) {
        if (mainWindow.isMinimized()) mainWindow.restore();
        mainWindow.show();
        mainWindow.focus();
      }
    } },
    { label: 'Restart Server', click: () => { restartServer(); } },
    { label: 'Open Logs Folder', click: () => { shell.openPath(LOG_DIR); } },
    { type: 'separator' },
    { label: 'About SPB', click: () => showAboutDialog() },
    { label: 'Quit', click: () => { quitInProgress = true; app.quit(); } },
  ]);
}
function setupTray() {
  try {
    const icon = loadAppIcon();
    tray = new Tray(icon || nativeImage.createEmpty());
    tray.setToolTip('Shokker Paint Booth');
    tray.setContextMenu(buildTrayMenu());
    tray.on('click', () => {
      if (!mainWindow) return;
      if (mainWindow.isVisible()) mainWindow.hide();
      else { mainWindow.show(); mainWindow.focus(); }
    });
  } catch (e) {
    debugLog(`[Tray] init failed: ${e.message}`);
  }
}
function updateTrayServerStatus(ready) {
  serverReady = !!ready;
  if (tray) {
    try {
      tray.setContextMenu(buildTrayMenu());
      tray.setToolTip(`Shokker Paint Booth — Server: ${ready ? 'Running' : 'Stopped'}`);
    } catch (_) {}
  }
  if (mainWindow && !mainWindow.isDestroyed()) {
    try { mainWindow.webContents.send('server-status', { ready }); } catch (_) {}
  }
}

// ===== IMPROVEMENT #12: Proper application menu =====
function buildAppMenu() {
  const isMac = process.platform === 'darwin';
  const template = [
    {
      label: 'File',
      submenu: [
        { label: 'Open Recent…', submenu: readRecentFiles().slice(0, 8).map((p) => ({
          label: path.basename(p),
          click: () => { if (mainWindow) mainWindow.webContents.send('menu-action', { action: 'open-file', path: p }); },
        })) },
        { type: 'separator' },
        { label: 'Quit', accelerator: isMac ? 'Cmd+Q' : 'Ctrl+Q', click: () => { quitInProgress = false; app.quit(); } },
      ],
    },
    { label: 'Edit', submenu: [
      { role: 'undo' }, { role: 'redo' }, { type: 'separator' },
      { role: 'cut' }, { role: 'copy' }, { role: 'paste' }, { role: 'selectAll' },
    ] },
    { label: 'View', submenu: [
      { label: 'Reload', accelerator: 'Ctrl+R', click: () => mainWindow && mainWindow.webContents.reload() },
      { label: 'Hard Reload', accelerator: 'Ctrl+Shift+R', click: async () => {
        if (!mainWindow) return;
        try { await mainWindow.webContents.session.clearCache(); } catch (_) {}
        mainWindow.webContents.reloadIgnoringCache();
      } },
      { label: 'Toggle Developer Tools', accelerator: 'F12', click: () => mainWindow && mainWindow.webContents.toggleDevTools() },
      { type: 'separator' },
      // ----- IMPROVEMENT #10: Disable zoom shortcuts (no-op handlers) -----
      { label: 'Actual Size', accelerator: 'Ctrl+0', click: () => { /* zoom disabled */ } },
      { label: 'Zoom In', accelerator: 'Ctrl+Plus', click: () => { /* zoom disabled */ } },
      { label: 'Zoom Out', accelerator: 'Ctrl+-', click: () => { /* zoom disabled */ } },
      { type: 'separator' },
      { role: 'togglefullscreen' },
    ] },
    { label: 'Window', submenu: [
      { role: 'minimize' }, { role: 'close' },
    ] },
    { label: 'Help', submenu: [
      { label: 'Open Logs Folder', click: () => shell.openPath(LOG_DIR) },
      { label: 'Open App Data Folder', click: () => shell.openPath(APP_DATA_DIR) },
      { label: 'Visit Shokker', click: () => shell.openExternal('https://shokkergroup.com') },
      { label: 'Releases', click: () => shell.openExternal('https://github.com/ShokkerGroup/ShokkerPaintBooth/releases') },
      { type: 'separator' },
      { label: 'About Shokker Paint Booth', click: () => showAboutDialog() },
    ] },
  ];
  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}

function showAboutDialog() {
  const win = mainWindow || BrowserWindow.getAllWindows()[0];
  dialog.showMessageBox(win, {
    type: 'info',
    title: 'About Shokker Paint Booth',
    message: `Shokker Paint Booth ${app.getVersion()}`,
    detail: [
      `Electron: ${process.versions.electron}`,
      `Chromium: ${process.versions.chrome}`,
      `Node: ${process.versions.node}`,
      `Platform: ${process.platform} ${os.release()}`,
      ``,
      `(c) ${new Date().getFullYear()} Shokker Group — All rights reserved.`,
      `Licensed via Payhip.`,
    ].join('\n'),
    buttons: ['Close', 'Copy Version'],
    defaultId: 0,
  }).then((res) => {
    if (res.response === 1) {
      try { electron.clipboard.writeText(`SPB ${app.getVersion()} (${process.versions.electron})`); } catch (_) {}
    }
  });
}

// ===== CREATE WINDOW =====
function createWindow(port) {
  const saved = readWindowState() || {};
  const defaults = { width: 1600, height: 1000, x: undefined, y: undefined, isMaximized: false };
  const state = clampToDisplay(Object.assign({}, defaults, saved));

  mainWindow = new BrowserWindow({
    width: state.width,
    height: state.height,
    x: state.x,
    y: state.y,
    minWidth: 1100,
    minHeight: 720,
    title: 'Shokker Paint Booth',
    backgroundColor: '#111111',
    icon: loadAppIcon(),
    show: false, // ----- IMPROVEMENT #31: defer paint until ready-to-show -----
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: false, // preload uses ipcRenderer
      webSecurity: true,
      allowRunningInsecureContent: false,
      experimentalFeatures: false,
      spellcheck: false,
      preload: path.join(__dirname, 'preload.js'),
      // ----- IMPROVEMENT #25: Pre-grant notification permission for our origin -----
      // (handled at the session level below)
    },
    autoHideMenuBar: true,
  });

  // ----- IMPROVEMENT #9: Content Security Policy -----
  // Allow loading from our own loopback server only.
  const cspValue = [
    "default-src 'self' http://127.0.0.1:* ws://127.0.0.1:*",
    "img-src 'self' data: blob: http://127.0.0.1:*",
    "style-src 'self' 'unsafe-inline' http://127.0.0.1:*",
    "script-src 'self' 'unsafe-inline' 'unsafe-eval' http://127.0.0.1:*",
    "connect-src 'self' http://127.0.0.1:* ws://127.0.0.1:* https://payhip.com",
    "font-src 'self' data: http://127.0.0.1:*",
    "object-src 'none'",
    "base-uri 'self'",
  ].join('; ');
  mainWindow.webContents.session.webRequest.onHeadersReceived((details, callback) => {
    const headers = Object.assign({}, details.responseHeaders);
    headers['Content-Security-Policy'] = [cspValue];
    callback({ responseHeaders: headers });
  });

  // ----- IMPROVEMENT #25: pre-grant notification permission to loopback -----
  mainWindow.webContents.session.setPermissionRequestHandler((_wc, permission, cb, requestingOrigin) => {
    const origin = requestingOrigin || '';
    const trusted = origin.startsWith(`http://127.0.0.1:`);
    if (permission === 'notifications' && trusted) return cb(true);
    if (permission === 'clipboard-read' && trusted) return cb(true);
    if (permission === 'clipboard-sanitized-write' && trusted) return cb(true);
    return cb(false);
  });

  // ----- IMPROVEMENT #26: External links open in default browser -----
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (/^https?:\/\//i.test(url)) {
      shell.openExternal(url);
      return { action: 'deny' };
    }
    return { action: 'deny' };
  });
  mainWindow.webContents.on('will-navigate', (e, url) => {
    if (!url.startsWith(`http://127.0.0.1:`)) {
      e.preventDefault();
      if (/^https?:\/\//i.test(url)) shell.openExternal(url);
    }
  });

  // BUILD 23: Clear cache before loading (preserved)
  mainWindow.webContents.session.clearCache().then(() => {
    console.log('[Electron] Cache cleared');
  }).catch((err) => console.log('[Electron] Cache clear failed:', err.message));
  mainWindow.webContents.session.clearStorageData({
    storages: ['cachestorage', 'serviceworkers']
  }).catch(() => {});

  // ----- IMPROVEMENT #28: File drag-drop -----
  // The renderer handles dragover/drop, but we also pull paths through 'will-navigate'
  // when files are dropped onto the window itself.
  mainWindow.webContents.on('will-navigate', (e, url) => {
    if (url.startsWith('file:///')) e.preventDefault();
  });

  // ----- IMPROVEMENT #35: Fallback error page when renderer load fails -----
  mainWindow.webContents.on('did-fail-load', (_e, errorCode, errorDesc, validatedURL) => {
    debugLog(`[Renderer] did-fail-load ${errorCode} ${errorDesc} for ${validatedURL}`);
    if (errorCode === -3) return; // ABORTED — usually our own reload
    const html = `<!DOCTYPE html><html><body style="background:#0a0a0a;color:#e0e0e0;font-family:Segoe UI,sans-serif;padding:40px;text-align:center">
      <h1 style="color:#E87A20">Could not reach the engine</h1>
      <p>${errorDesc} (${errorCode})</p>
      <p style="color:#888">Tried: ${validatedURL}</p>
      <p style="margin-top:24px"><button onclick="location.reload()" style="padding:10px 20px;background:#E87A20;color:#fff;border:none;border-radius:6px;cursor:pointer">Retry</button></p>
      <p style="color:#666;margin-top:24px;font-size:12px">Logs: ${LOG_FILE.replace(/\\/g, '/')}</p>
    </body></html>`;
    mainWindow.loadURL('data:text/html;charset=utf-8,' + encodeURIComponent(html));
  });

  // ----- IMPROVEMENT #21: renderer process gone -----
  mainWindow.webContents.on('render-process-gone', (_e, details) => {
    debugLog(`[Renderer] render-process-gone reason=${details.reason} exitCode=${details.exitCode}`);
    if (details.reason !== 'clean-exit') {
      dialog.showErrorBox('Shokker Paint Booth', `The interface crashed (${details.reason}). The window will reload.`);
      try { mainWindow.reload(); } catch (_) {}
    }
  });

  const url = `http://127.0.0.1:${port}/`;
  console.log(`[Electron] Loading: ${url}`);
  mainWindow.loadURL(url);

  // ----- IMPROVEMENT #31: Show only when ready (no white flash) -----
  mainWindow.once('ready-to-show', () => {
    if (saved.isMaximized) mainWindow.maximize();
    mainWindow.show();
  });

  // ----- IMPROVEMENT #1/23: Persist window state on resize/move/maximize -----
  const saveBounds = () => {
    if (!mainWindow || mainWindow.isDestroyed()) return;
    if (mainWindow.isMinimized()) return;
    const isMaximized = mainWindow.isMaximized();
    const bounds = isMaximized ? (saved && saved.width ? saved : mainWindow.getBounds()) : mainWindow.getBounds();
    writeWindowState({
      width: bounds.width, height: bounds.height,
      x: bounds.x, y: bounds.y, isMaximized,
    });
  };
  let saveTimer = null;
  const debouncedSave = () => {
    if (saveTimer) clearTimeout(saveTimer);
    saveTimer = setTimeout(saveBounds, 500);
  };
  mainWindow.on('resize', debouncedSave);
  mainWindow.on('move', debouncedSave);
  mainWindow.on('maximize', saveBounds);
  mainWindow.on('unmaximize', saveBounds);
  mainWindow.on('close', saveBounds);

  // ----- IMPROVEMENT #14: Quit confirmation when unsaved -----
  mainWindow.on('close', (e) => {
    if (quitInProgress) return;
    if (!unsavedWork) return;
    e.preventDefault();
    const choice = dialog.showMessageBoxSync(mainWindow, {
      type: 'warning',
      buttons: ['Cancel', 'Discard & Quit'],
      defaultId: 0,
      cancelId: 0,
      title: 'Unsaved work',
      message: 'You have unsaved changes. Quit anyway?',
    });
    if (choice === 1) {
      unsavedWork = false;
      quitInProgress = true;
      mainWindow.close();
    }
  });

  // ----- IMPROVEMENT #2: Multi-monitor — react to display changes -----
  const onDisplayChange = () => {
    if (!mainWindow || mainWindow.isDestroyed()) return;
    const bounds = mainWindow.getBounds();
    const fixed = clampToDisplay(bounds);
    if (fixed.x !== bounds.x || fixed.y !== bounds.y) {
      mainWindow.setBounds({ x: fixed.x, y: fixed.y, width: bounds.width, height: bounds.height });
      debugLog('[Display] Window re-positioned after display change');
    }
  };
  screen.on('display-removed', onDisplayChange);
  screen.on('display-metrics-changed', onDisplayChange);

  mainWindow.on('closed', () => {
    screen.off('display-removed', onDisplayChange);
    screen.off('display-metrics-changed', onDisplayChange);
    mainWindow = null;
  });
}

// ===== SPLASH / LOADING WINDOW =====
function showSplash(statusText) {
  if (splashWindow) {
    try { splashWindow.webContents.send('splash-status', statusText); } catch (_) {}
    return;
  }
  splashWindow = new BrowserWindow({
    width: 420, height: 260, frame: false, resizable: false,
    transparent: false, backgroundColor: '#0a0a0a',
    alwaysOnTop: true, skipTaskbar: false,
    icon: loadAppIcon(),
    webPreferences: { nodeIntegration: false, contextIsolation: true,
      preload: path.join(__dirname, 'license-preload.js') }
  });
  const splashHtml = `<!DOCTYPE html><html><head><meta charset="utf-8"><style>
    *{margin:0;padding:0;box-sizing:border-box}
    body{font-family:'Segoe UI',sans-serif;background:#0a0a0a;color:#e0e0e0;
      display:flex;flex-direction:column;align-items:center;justify-content:center;
      height:100vh;padding:30px;-webkit-app-region:drag}
    h1{font-size:22px;font-weight:700;color:#E87A20;margin-bottom:10px;letter-spacing:1px}
    .status{font-size:14px;color:#999;margin-top:8px;text-align:center}
    .spinner{width:32px;height:32px;border:3px solid #333;border-top:3px solid #E87A20;
      border-radius:50%;animation:spin 1s linear infinite;margin:16px auto 8px}
    @keyframes spin{to{transform:rotate(360deg)}}
    </style></head><body>
    <h1>SHOKKER PAINT BOOTH</h1>
    <div class="spinner"></div>
    <div class="status" id="status">${statusText || 'Starting...'}</div>
    <script>
      const {ipcRenderer} = require('electron');
      ipcRenderer.on('splash-status', (e, msg) => {
        document.getElementById('status').textContent = msg;
      });
    </script>
    </body></html>`;
  splashWindow.loadURL('data:text/html;charset=utf-8,' + encodeURIComponent(splashHtml));
  splashWindow.on('closed', () => { splashWindow = null; });
}

function closeSplash() {
  if (splashWindow) {
    try { splashWindow.close(); } catch (_) {}
    splashWindow = null;
  }
}

// ===== IMPROVEMENT #11: Custom protocol handler (shokker://) =====
try {
  if (process.defaultApp) {
    if (process.argv.length >= 2) app.setAsDefaultProtocolClient('shokker', process.execPath, [path.resolve(process.argv[1])]);
  } else {
    app.setAsDefaultProtocolClient('shokker');
  }
} catch (_) {}

function handleDeepLink(rawUrl) {
  if (!rawUrl || typeof rawUrl !== 'string') return;
  if (!rawUrl.toLowerCase().startsWith('shokker://')) return;
  debugLog(`[DeepLink] ${rawUrl}`);
  if (mainWindow) {
    if (mainWindow.isMinimized()) mainWindow.restore();
    mainWindow.show(); mainWindow.focus();
    try { mainWindow.webContents.send('deep-link', rawUrl); } catch (_) {}
  }
}

// ----- IMPROVEMENT #15: Honor second-instance: focus existing window -----
app.on('second-instance', (_event, argv) => {
  if (mainWindow) {
    if (mainWindow.isMinimized()) mainWindow.restore();
    mainWindow.show(); mainWindow.focus();
  }
  // Look for shokker:// or recent file path in the new instance's argv
  for (const a of argv) {
    if (typeof a === 'string' && a.toLowerCase().startsWith('shokker://')) handleDeepLink(a);
  }
});

// macOS open-url (kept for completeness; SPB ships Windows-only today)
app.on('open-url', (event, url) => { event.preventDefault(); handleDeepLink(url); });

// ===== APP LIFECYCLE =====
app.whenReady().then(async () => {
  try {
    debugLog('[Startup] app.whenReady fired');

    // ----- IMPROVEMENT #16: Auto-updater hooks (kept simple, deferred) -----
    // Wired further down once the window exists.

    const licensed = await checkLicenseAndActivate();
    debugLog(`[Startup] checkLicenseAndActivate returned: ${licensed}`);
    if (!licensed) {
      debugLog('[Startup] No valid license - quitting');
      app.quit();
      return;
    }
    debugLog('[Startup] License validated - starting app');

    showSplash('Starting engine...');

    debugLog('[Startup] Killing zombie servers...');
    showSplash('Cleaning up...');
    await killZombieServers();

    // ----- IMPROVEMENT #17: Pick a free port (still prefers 59876) -----
    serverPort = await pickServerPort();
    debugLog(`[Startup] Starting server on port ${serverPort}...`);
    showSplash('Starting Python server...');
    await startServerWithRetry(serverPort, 3);
    debugLog('[Startup] Server started');
    showSplash('Loading interface...');

    // PyInstaller HTML workaround (preserved)
    try {
      const buildCheck = await new Promise((res, rej) => {
        http.get(`http://127.0.0.1:${serverPort}/build-check`, (resp) => {
          let data = '';
          resp.on('data', (chunk) => data += chunk);
          resp.on('end', () => { try { res(JSON.parse(data)); } catch (e) { rej(e); } });
        }).on('error', rej);
      });
      const srvDir = buildCheck.server_dir;
      debugLog(`[Startup] Server reports SERVER_DIR: ${srvDir}`);
      const htmlInSrvDir = path.join(srvDir, 'paint-booth-v2.html');
      if (!fs.existsSync(htmlInSrvDir)) {
        const srcHtml = path.join(getServerDir(), 'paint-booth-v2.html');
        if (fs.existsSync(srcHtml)) {
          fs.copyFileSync(srcHtml, htmlInSrvDir);
          debugLog(`[Startup] Copied HTML to server dir: ${htmlInSrvDir}`);
        } else {
          debugLog(`[Startup] WARNING: HTML not found at ${srcHtml}`);
        }
      } else {
        debugLog('[Startup] HTML already in server dir');
      }
    } catch (e) {
      debugLog(`[Startup] Build-check workaround failed: ${e.message}`);
    }

    debugLog('[Startup] Creating window...');
    buildAppMenu();
    setupTray();
    refreshJumpList();
    createWindow(serverPort);
    debugLog('[Startup] Window created - app should be visible');

    // Close splash once main window finishes loading
    mainWindow.webContents.once('did-finish-load', () => {
      closeSplash();
      debugLog('[Startup] Splash closed, main window loaded');
      try { mainWindow.webContents.send('server-status', { ready: serverReady, port: serverPort }); } catch (_) {}
    });
    setTimeout(closeSplash, 10000);

    // ----- IMPROVEMENT #30: Auto-reload on JS/HTML changes in dev mode -----
    if (!app.isPackaged) {
      try {
        const watchTargets = [path.join(getServerDir())];
        for (const target of watchTargets) {
          if (!fs.existsSync(target)) continue;
          fs.watch(target, { recursive: true }, (_evt, filename) => {
            if (!filename) return;
            if (/\.(html|css|js)$/i.test(filename)) {
              debugLog(`[Dev] File changed: ${filename} — reloading renderer`);
              if (mainWindow && !mainWindow.isDestroyed()) mainWindow.webContents.reload();
            }
          });
          debugLog(`[Dev] Watching ${target} for HTML/CSS/JS changes`);
        }
      } catch (e) { debugLog(`[Dev] Watch setup failed: ${e.message}`); }
    }

    // ----- IMPROVEMENT #18: Start the server watchdog -----
    startWatchdog();

    // ----- Power-save blocker (don't sleep mid-render) -----
    try { powerSaveBlockerId = powerSaveBlocker.start('prevent-app-suspension'); } catch (_) {}

    // ===== AUTO-UPDATER (preserved + a couple polish bits) =====
    setTimeout(() => {
      debugLog('[Updater] Checking for updates...');
      autoUpdater.logger = { info: (m) => debugLog(`[Updater] ${m}`), warn: (m) => debugLog(`[Updater] WARN: ${m}`), error: (m) => debugLog(`[Updater] ERR: ${m}`) };
      autoUpdater.autoDownload = true;
      autoUpdater.autoInstallOnAppQuit = true;
      autoUpdater.allowPrerelease = true;

      autoUpdater.on('update-available', (info) => {
        debugLog(`[Updater] Update available: v${info.version}`);
        if (mainWindow) {
          dialog.showMessageBox(mainWindow, {
            type: 'info',
            title: 'Update Available',
            message: `Version ${info.version} is available and downloading in the background. It will install when you close the app.\n\nSee what's new: https://github.com/ShokkerGroup/ShokkerPaintBooth/releases`,
            buttons: ['OK']
          });
        }
      });
      autoUpdater.on('update-not-available', () => debugLog('[Updater] No updates available - running latest version'));
      autoUpdater.on('update-downloaded', (info) => debugLog(`[Updater] Update downloaded: v${info.version} - will install on quit`));
      autoUpdater.on('error', (err) => debugLog(`[Updater] Error: ${err.message}`));
      autoUpdater.checkForUpdates().catch((err) => debugLog(`[Updater] Check failed: ${err.message}`));
    }, 5000);

  } catch (err) {
    debugLog(`[Startup] CATCH ERROR: ${err.message}`);
    dialog.showErrorBox(
      'Shokker Paint Booth - Startup Error',
      `Failed to start the Shokker server.\n\n${err.message}\n\nPlease report this to Ricky.`
    );
    app.quit();
  }
});

// ===== IMPROVEMENT #37: Graceful shutdown sequence =====
function gracefulShutdown(reason) {
  debugLog(`[Shutdown] gracefulShutdown(${reason})`);
  try { if (watchdogTimer) clearInterval(watchdogTimer); } catch (_) {}
  try { if (powerSaveBlockerId !== null) powerSaveBlocker.stop(powerSaveBlockerId); } catch (_) {}
  const { execSync } = require('child_process');
  if (serverProcess && serverProcess.pid) {
    console.log(`[Electron] Killing server PID ${serverProcess.pid}...`);
    try { execSync(`taskkill /F /PID ${serverProcess.pid} /T 2>nul`, { windowsHide: true, timeout: 5000 }); }
    catch (e) { console.log('[Electron] taskkill failed:', e.message); }
  }
  // Sweep for any orphaned shokker-server.exe (preserved)
  try { execSync('taskkill /F /IM shokker-server.exe /T 2>nul', { windowsHide: true, timeout: 5000 }); } catch (_) {}
  serverProcess = null;
}

app.on('window-all-closed', () => {
  if (!mainWindow && BrowserWindow.getAllWindows().length === 0 && !serverReady) {
    debugLog('[Lifecycle] window-all-closed fired but no mainWindow yet - ignoring (license flow)');
    return;
  }
  debugLog('[Lifecycle] window-all-closed - shutting down');
  gracefulShutdown('window-all-closed');
  app.quit();
});

app.on('before-quit', () => {
  quitInProgress = true;
  gracefulShutdown('before-quit');
});

// Defense in depth: ensure children die if Electron itself dies hard.
process.on('exit', () => { try { gracefulShutdown('process-exit'); } catch (_) {} });
process.on('uncaughtException', (err) => {
  debugLog(`[Process] uncaughtException: ${err && err.stack || err}`);
});
process.on('unhandledRejection', (reason) => {
  debugLog(`[Process] unhandledRejection: ${reason && reason.stack || reason}`);
});
