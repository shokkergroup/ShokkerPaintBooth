const { app, BrowserWindow, dialog, ipcMain } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const net = require('net');
const fs = require('fs');
const os = require('os');
const https = require('https');
const crypto = require('crypto');
const { autoUpdater } = require('electron-updater');

let mainWindow = null;
let serverProcess = null;
let serverPort = 5001;

// Debug logging to file (remove for production)
const DEBUG_LOG = path.join(os.tmpdir(), 'shokker-debug.log');
function debugLog(msg) {
  const ts = new Date().toISOString().substring(11, 23);
  const line = `[${ts}] ${msg}\n`;
  try { fs.appendFileSync(DEBUG_LOG, line); } catch (e) { }
  console.log(msg);
}
// Clear log on startup
try { fs.writeFileSync(DEBUG_LOG, ''); } catch (e) { }

// ===== LICENSE KEY SYSTEM =====
const LICENSE_DIR = path.join(process.env.APPDATA || os.homedir(), 'ShokkerPaintBooth');
const LICENSE_FILE = path.join(LICENSE_DIR, 'license.dat');
const ENCRYPTION_KEY = 'ShokkerPaintBooth2026AlphaKeyXX!'; // 32 bytes for AES-256

// Payhip product secret — set this when you create the Payhip listing
// For now, leave as placeholder. Replace with actual key from Payhip dashboard.
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
  // Simple machine fingerprint: hostname + username + homedir
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
    // Verify machine ID matches
    if (data.machineId !== getMachineId()) {
      console.log('[License] Machine ID mismatch — activation invalid on this device');
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
    if (!fs.existsSync(LICENSE_DIR)) {
      fs.mkdirSync(LICENSE_DIR, { recursive: true });
    }
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
    // If Payhip secret isn't set yet, accept any non-empty key (dev mode)
    // Dev mode bypass removed — real Payhip secret is configured

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
      resolve({ valid: false, reason: 'Could not reach license server. Check your internet connection.' });
    });
    req.setTimeout(10000, () => {
      req.destroy();
      resolve({ valid: false, reason: 'License server timed out. Check your internet connection.' });
    });
    req.end();
  });
}

function incrementPayhipUsage(licenseKey) {
  return new Promise((resolve) => {
    // Dev mode bypass removed — real Payhip secret is configured
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
    const licenseWin = new BrowserWindow({
      width: 520,
      height: 420,
      resizable: false,
      minimizable: false,
      maximizable: false,
      title: 'Shokker Paint Booth — Activate',
      backgroundColor: '#0a0a0a',
      autoHideMenuBar: true,
      webPreferences: {
        nodeIntegration: false,
        contextIsolation: true,
        preload: path.join(__dirname, 'license-preload.js')
      }
    });

    debugLog('[Dialog] License window created, loading license.html');

    // IPC: license dialog sends key back to main process
    ipcMain.once('license-submit', async (_event, key) => {
      debugLog(`[Dialog] Received license-submit with key: ${(key || '').substring(0, 5)}...`);
      const trimmedKey = (key || '').trim().toUpperCase();
      if (!trimmedKey) {
        licenseWin.webContents.send('license-error', 'Please enter a license key.');
        // Re-listen since this was a once
        ipcMain.once('license-submit', arguments.callee);
        return;
      }

      licenseWin.webContents.send('license-status', 'Verifying...');

      const result = await verifyWithPayhip(trimmedKey);
      if (result.valid) {
        await incrementPayhipUsage(trimmedKey);
        saveLocalLicense(trimmedKey, result.email);
        licenseWin.close();
        resolve(true);
      } else {
        licenseWin.webContents.send('license-error', result.reason || 'Invalid license key.');
        // Re-register the handler for retry
        const retryHandler = async (_ev, retryKey) => {
          const rk = (retryKey || '').trim().toUpperCase();
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
            licenseWin.close();
            resolve(true);
          } else {
            licenseWin.webContents.send('license-error', r2.reason || 'Invalid license key.');
            ipcMain.once('license-submit', retryHandler);
          }
        };
        ipcMain.once('license-submit', retryHandler);
      }
    });

    ipcMain.once('license-buy', () => {
      const { shell } = require('electron');
      shell.openExternal('https://payhip.com/b/AHgpV');
    });

    ipcMain.once('license-quit', () => {
      licenseWin.close();
      resolve(false);
    });

    licenseWin.on('closed', () => {
      debugLog('[Dialog] License window closed event fired');
      ipcMain.removeAllListeners('license-submit');
      ipcMain.removeAllListeners('license-quit');
      ipcMain.removeAllListeners('license-buy');
      resolve(false);
    });

    // Load license dialog from local HTML file (data: URLs don't get preload scripts)
    licenseWin.loadFile(path.join(__dirname, 'license.html'));
  });
}

function getLicenseDialogHTML() {
  return `<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Activate</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: 'Segoe UI', sans-serif;
    background: #0a0a0a;
    color: #e0e0e0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100vh;
    padding: 30px;
    -webkit-app-region: drag;
  }
  h1 {
    font-size: 22px;
    font-weight: 700;
    color: #ff3366;
    margin-bottom: 6px;
    letter-spacing: 1px;
  }
  .subtitle {
    font-size: 13px;
    color: #888;
    margin-bottom: 28px;
  }
  .input-group {
    width: 100%;
    max-width: 380px;
    -webkit-app-region: no-drag;
  }
  label {
    display: block;
    font-size: 12px;
    color: #aaa;
    margin-bottom: 6px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
  input {
    width: 100%;
    padding: 12px 14px;
    background: #1a1a1a;
    border: 1px solid #333;
    border-radius: 6px;
    color: #fff;
    font-size: 16px;
    font-family: 'Consolas', 'Courier New', monospace;
    letter-spacing: 2px;
    text-align: center;
    outline: none;
    transition: border-color 0.2s;
  }
  input:focus { border-color: #ff3366; }
  input::placeholder { color: #555; letter-spacing: 1px; font-size: 13px; }
  .btn-row {
    display: flex;
    gap: 10px;
    margin-top: 18px;
    width: 100%;
    max-width: 380px;
    -webkit-app-region: no-drag;
  }
  button {
    flex: 1;
    padding: 12px;
    border: none;
    border-radius: 6px;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s;
  }
  .btn-activate {
    background: #ff3366;
    color: #fff;
  }
  .btn-activate:hover { background: #e6295a; }
  .btn-activate:disabled { background: #663; cursor: wait; }
  .btn-buy {
    background: #222;
    color: #ff3366;
    border: 1px solid #333;
  }
  .btn-buy:hover { background: #2a2a2a; border-color: #ff3366; }
  .btn-quit {
    background: transparent;
    color: #666;
    font-size: 12px;
    margin-top: 16px;
    -webkit-app-region: no-drag;
    border: none;
    cursor: pointer;
    padding: 6px;
  }
  .btn-quit:hover { color: #999; }
  #status {
    margin-top: 14px;
    font-size: 13px;
    min-height: 20px;
    text-align: center;
  }
  .error { color: #ff4466; }
  .info { color: #66aaff; }
</style>
</head>
<body>
  <h1>SHOKKER PAINT BOOTH</h1>
  <div class="subtitle">Enter your license key to activate</div>
  <div class="input-group">
    <label>License Key</label>
    <input type="text" id="keyInput" placeholder="XXXXX-XXXXX-XXXXX-XXXXX" autofocus
           spellcheck="false" autocomplete="off" />
  </div>
  <div class="btn-row">
    <button class="btn-activate" id="activateBtn" onclick="doActivate()">Activate</button>
    <button class="btn-buy" onclick="doBuy()">Buy License</button>
  </div>
  <div id="status"></div>
  <button class="btn-quit" onclick="doQuit()">Exit</button>
  <script>
    const { ipcRenderer } = window.electronLicense || {};

    function doActivate() {
      const key = document.getElementById('keyInput').value;
      document.getElementById('activateBtn').disabled = true;
      document.getElementById('status').className = 'info';
      document.getElementById('status').textContent = 'Verifying...';
      if (ipcRenderer) ipcRenderer.send('license-submit', key);
    }

    function doBuy() {
      if (ipcRenderer) ipcRenderer.send('license-buy');
      // Fallback: open in default browser
      window.open('https://payhip.com/b/AHgpV', '_blank');
    }

    function doQuit() {
      if (ipcRenderer) ipcRenderer.send('license-quit');
    }

    document.getElementById('keyInput').addEventListener('keydown', (e) => {
      if (e.key === 'Enter') doActivate();
    });

    // Listen for messages from main process
    if (ipcRenderer) {
      ipcRenderer.on('license-error', (_e, msg) => {
        document.getElementById('status').className = 'error';
        document.getElementById('status').textContent = msg;
        document.getElementById('activateBtn').disabled = false;
      });
      ipcRenderer.on('license-status', (_e, msg) => {
        document.getElementById('status').className = 'info';
        document.getElementById('status').textContent = msg;
      });
    }
  </script>
</body>
</html>`;
}

async function checkLicenseAndActivate() {
  // Check for existing local activation
  const local = readLocalLicense();
  if (local) {
    console.log(`[License] Valid local activation found (key: ${local.licenseKey.substring(0, 5)}...)`);
    // Optional: periodic re-verification (every 7 days)
    const lastVerified = new Date(local.lastVerified);
    const daysSince = (Date.now() - lastVerified.getTime()) / (1000 * 60 * 60 * 24);
    if (daysSince > 7) {
      console.log('[License] Re-verifying with Payhip (last check was', Math.round(daysSince), 'days ago)');
      const result = await verifyWithPayhip(local.licenseKey);
      if (result.valid) {
        // Update last verified timestamp
        saveLocalLicense(local.licenseKey, local.email);
        return true;
      } else {
        console.log('[License] Re-verification failed — clearing local license');
        try { fs.unlinkSync(LICENSE_FILE); } catch (e) { }
        // Fall through to show dialog
      }
    } else {
      return true;
    }
  }

  // No valid local activation — show the license dialog
  debugLog('[License] No valid activation found, showing license dialog');
  const activated = await showLicenseDialog();
  debugLog(`[License] showLicenseDialog returned: ${activated}`);
  return activated;
}

// ===== IPC: Direct filesystem browsing (bypasses server entirely) =====
ipcMain.handle('list-dir', async (_event, dirPath, filter) => {
  try {
    if (!dirPath) return null; // signal to use get-quick-navs instead

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
        if (isLarge) continue; // large dir = folders only, skip all files
        const lname = entry.name.toLowerCase();
        if (filter && !lname.endsWith(filter.toLowerCase())) continue;
        totalFiles++;
        if (files.length < MAX_FILES) {
          let size = 0;
          try { size = fs.statSync(path.join(resolved, entry.name)).size; } catch (e) { }
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

ipcMain.handle('get-quick-navs', async () => {
  const drives = [];
  for (const letter of 'CDEFGHIJKLMNOPQRSTUVWXYZ') {
    const drive = letter + ':/';
    if (fs.existsSync(drive)) drives.push({ name: letter + ':', path: drive, type: 'drive' });
  }
  const quick_navs = [];

  // BUILD 30: OneDrive compatibility — search multiple possible iRacing paint paths
  // OneDrive redirects Documents, so the paint folder may live under OneDrive/ instead
  const home = os.homedir();
  const iracingCandidates = [
    // Standard path
    path.join(home, 'Documents', 'iRacing', 'paint'),
    // OneDrive personal
    path.join(home, 'OneDrive', 'Documents', 'iRacing', 'paint'),
    // OneDrive for Business (has org name suffix)
    // We scan for OneDrive - * folders dynamically below
  ];

  // Scan for any "OneDrive - *" folders (business/education OneDrive)
  try {
    const homeEntries = fs.readdirSync(home, { withFileTypes: true });
    for (const entry of homeEntries) {
      if (entry.isDirectory() && entry.name.startsWith('OneDrive -') || entry.name.startsWith('OneDrive-')) {
        iracingCandidates.push(path.join(home, entry.name, 'Documents', 'iRacing', 'paint'));
      }
    }
  } catch (e) { /* ignore scan errors */ }

  // Also check Windows Known Folder path via environment variable
  // USERPROFILE\Documents may differ from os.homedir() on some setups
  if (process.env.USERPROFILE && process.env.USERPROFILE !== home) {
    iracingCandidates.push(path.join(process.env.USERPROFILE, 'Documents', 'iRacing', 'paint'));
  }

  // Use the first valid path found
  let iracingFound = false;
  for (const candidate of iracingCandidates) {
    try {
      if (fs.existsSync(candidate) && fs.statSync(candidate).isDirectory()) {
        quick_navs.push({ name: 'iRacing Paint Folder', path: candidate.replace(/\\/g, '/'), type: 'shortcut' });
        console.log(`[QuickNav] iRacing paint folder found: ${candidate}`);
        iracingFound = true;
        break;
      }
    } catch (e) { /* skip inaccessible paths */ }
  }
  if (!iracingFound) {
    console.log('[QuickNav] iRacing paint folder not found in any standard location');
  }

  return { drives, quick_navs };
});

// ===== BUILD 25: KILL ZOMBIE SERVERS =====
// Previous app launches may leave shokker-server.exe processes running.
// These zombies squat on port 5001 and intercept requests meant for the new server.
function killZombieServers() {
  return new Promise((resolve) => {
    const { execSync } = require('child_process');
    try {
      // Find all shokker-paint-booth-ag.exe processes and kill them
      execSync('taskkill /F /IM shokker-paint-booth-ag.exe /T 2>nul', { windowsHide: true, timeout: 5000 });
      console.log('[Electron] Killed zombie shokker-paint-booth-ag processes');
    } catch (e) {
      // No processes found or other error — that's fine
      console.log('[Electron] No zombie servers found (or kill failed)');
    }
    // Small delay to let ports be released
    setTimeout(resolve, 500);
  });
}

// ===== SERVER PATH =====
function getServerPath() {
  // @electron/packager --extra-resource puts files directly in resources/
  const packaged1 = path.join(process.resourcesPath, 'shokker-paint-booth-ag.exe');
  // electron-builder puts them in resources/server/
  const packaged2 = path.join(process.resourcesPath, 'server', 'shokker-paint-booth-ag.exe');
  const dev = path.join(__dirname, 'server', 'shokker-paint-booth-ag.exe');
  if (fs.existsSync(packaged1)) return packaged1;
  if (fs.existsSync(packaged2)) return packaged2;
  if (fs.existsSync(dev)) return dev;
  return null;
}

// ===== SERVER DIR (where HTML and config files live) =====
function getServerDir() {
  const serverPath = getServerPath();
  return serverPath ? path.dirname(serverPath) : path.join(__dirname, 'server');
}

// ===== FIND FREE PORT =====
function findFreePort(startPort) {
  return new Promise((resolve) => {
    const server = net.createServer();
    server.listen(startPort, () => {
      const port = server.address().port;
      server.close(() => resolve(port));
    });
    server.on('error', () => resolve(findFreePort(startPort + 1)));
  });
}

// ===== START PYTHON SERVER =====
// CRITICAL: stdio set to 'ignore' to prevent pipe backpressure from freezing the main process.
// Previous builds piped stdout/stderr which caused the renderer to lock up when the server
// did heavy I/O (like scanning 5000+ file directories).
function startServer(port) {
  return new Promise((resolve, reject) => {
    const serverPath = getServerPath();
    debugLog(`[Server] getServerPath returned: ${serverPath}`);
    if (!serverPath) {
      debugLog('[Server] ERROR: shokker-paint-booth-ag.exe not found');
      reject(new Error('shokker-paint-booth-ag.exe not found'));
      return;
    }

    debugLog(`[Server] Launching: ${serverPath} on port ${port}`);

    // The server's SERVER_DIR may resolve to a temp extraction folder (PyInstaller --onefile).
    // Pass SHOKKER_EXE_DIR so the server knows where the REAL files are.
    // For older builds that don't read this env var, we'll also copy the HTML after startup.

    const env = Object.assign({}, process.env, {
      SHOKKER_PORT: String(port),
      SHOKKER_EXE_DIR: path.dirname(serverPath)  // Tell server where the exe REALLY lives
    });

    serverProcess = spawn(serverPath, [], {
      env,
      stdio: 'ignore',   // NO PIPES — prevents main process blocking
      windowsHide: true,
      detached: false
    });

    serverProcess.on('error', (err) => {
      debugLog(`[Server] ERROR: Failed to start: ${err.message}`);
      reject(err);
    });

    serverProcess.on('exit', (code) => {
      debugLog(`[Server] Exited with code ${code}`);
      serverProcess = null;
    });

    // Since stdio is ignored, we can't watch for "Running on" message.
    // Poll the port instead to detect when the server is ready.
    const startTime = Date.now();
    const pollInterval = setInterval(() => {
      const sock = new net.Socket();
      sock.setTimeout(300);
      sock.once('connect', () => {
        sock.destroy();
        clearInterval(pollInterval);
        console.log(`[Electron] Server ready on port ${port} (${Date.now() - startTime}ms)`);
        resolve(port);
      });
      sock.once('error', () => sock.destroy());
      sock.once('timeout', () => sock.destroy());
      sock.connect(port, '127.0.0.1');
    }, 250);

    // Timeout after 20s
    setTimeout(() => {
      clearInterval(pollInterval);
      console.log('[Electron] Server startup timeout, trying anyway...');
      resolve(port);
    }, 20000);
  });
}

// ===== CREATE WINDOW =====
function createWindow(port) {
  mainWindow = new BrowserWindow({
    width: 1600,
    height: 1000,
    minWidth: 1200,
    minHeight: 800,
    title: 'Shokker Paint Booth',
    backgroundColor: '#111111',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    },
    autoHideMenuBar: true
  });

  // BUILD 23: Clear ALL caches before loading to prevent stale page serving
  // This was causing the app to show cached HTML from previous builds while
  // the actual Flask server wasn't receiving any requests.
  mainWindow.webContents.session.clearCache().then(() => {
    console.log('[Electron] Cache cleared');
  }).catch(err => {
    console.log('[Electron] Cache clear failed:', err.message);
  });
  mainWindow.webContents.session.clearStorageData({
    storages: ['cachestorage', 'serviceworkers']
  }).catch(() => { });

  const url = `http://127.0.0.1:${port}/`;
  console.log(`[Electron] Loading: ${url}`);
  mainWindow.loadURL(url);

  mainWindow.on('closed', () => { mainWindow = null; });
}

// ===== APP LIFECYCLE =====
app.whenReady().then(async () => {
  try {
    // BUILD 28: License check BEFORE server startup
    debugLog('[Startup] app.whenReady fired');
    const licensed = await checkLicenseAndActivate();
    debugLog(`[Startup] checkLicenseAndActivate returned: ${licensed}`);
    if (!licensed) {
      debugLog('[Startup] No valid license — quitting');
      app.quit();
      return;
    }
    debugLog('[Startup] License validated — starting app');

    // Kill zombies then use HARDCODED port 59876
    debugLog('[Startup] Killing zombie servers...');
    await killZombieServers();
    serverPort = 59876;
    debugLog(`[Startup] Starting server on port ${serverPort}...`);
    await startServer(serverPort);
    debugLog('[Startup] Server started');

    // WORKAROUND: PyInstaller --onefile extracts to temp dir, so server can't find HTML.
    // Hit /build-check to get the server's actual SERVER_DIR, then copy HTML there if missing.
    try {
      const http = require('http');
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
    createWindow(serverPort);
    debugLog('[Startup] Window created — app should be visible');

    // ===== AUTO-UPDATER =====
    // Check for updates after app is fully loaded (silent check, no nagging)
    setTimeout(() => {
      debugLog('[Updater] Checking for updates...');
      autoUpdater.logger = { info: (m) => debugLog(`[Updater] ${m}`), warn: (m) => debugLog(`[Updater] WARN: ${m}`), error: (m) => debugLog(`[Updater] ERR: ${m}`) };
      autoUpdater.autoDownload = true;
      autoUpdater.autoInstallOnAppQuit = true;

      autoUpdater.on('update-available', (info) => {
        debugLog(`[Updater] Update available: v${info.version}`);
        if (mainWindow) {
          dialog.showMessageBox(mainWindow, {
            type: 'info',
            title: 'Update Available',
            message: `A new version (v${info.version}) is available and downloading in the background. It will install when you close the app.`,
            buttons: ['OK']
          });
        }
      });

      autoUpdater.on('update-not-available', () => {
        debugLog('[Updater] No updates available — running latest version');
      });

      autoUpdater.on('update-downloaded', (info) => {
        debugLog(`[Updater] Update downloaded: v${info.version} — will install on quit`);
      });

      autoUpdater.on('error', (err) => {
        debugLog(`[Updater] Error: ${err.message}`);
      });

      autoUpdater.checkForUpdates().catch((err) => {
        debugLog(`[Updater] Check failed: ${err.message}`);
      });
    }, 5000); // Wait 5s after launch to avoid slowing startup

  } catch (err) {
    debugLog(`[Startup] CATCH ERROR: ${err.message}`);
    dialog.showErrorBox(
      'Shokker Paint Booth — Startup Error',
      `Failed to start the Shokker server.\n\n${err.message}\n\nPlease report this to Ricky.`
    );
    app.quit();
  }
});

app.on('window-all-closed', () => {
  // Don't quit during license check — the license dialog closes before the main window opens
  if (!mainWindow) {
    debugLog('[Lifecycle] window-all-closed fired but no mainWindow yet — ignoring (license flow)');
    return;
  }
  debugLog('[Lifecycle] window-all-closed — shutting down');
  // BUILD 25: Use taskkill on Windows — SIGTERM/SIGKILL don't work reliably
  // and leave zombie processes that squat on ports
  const { execSync } = require('child_process');
  if (serverProcess && serverProcess.pid) {
    console.log(`[Electron] Killing server PID ${serverProcess.pid}...`);
    try { execSync(`taskkill /F /PID ${serverProcess.pid} /T 2>nul`, { windowsHide: true, timeout: 5000 }); }
    catch (e) { console.log('[Electron] taskkill failed:', e.message); }
  }
  // Also sweep for any orphaned shokker-server.exe
  try { execSync('taskkill /F /IM shokker-server.exe /T 2>nul', { windowsHide: true, timeout: 5000 }); }
  catch (e) { /* none found, fine */ }
  app.quit();
});

app.on('before-quit', () => {
  const { execSync } = require('child_process');
  if (serverProcess && serverProcess.pid) {
    try { execSync(`taskkill /F /PID ${serverProcess.pid} /T 2>nul`, { windowsHide: true, timeout: 3000 }); }
    catch (e) { }
  }
});
