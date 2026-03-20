/**
 * Copy V5 server assets into electron-app/server/ for packaging.
 * Run before npm run build so the installer contains the latest HTML/JS/CSS.
 * The server EXE (shokker-paint-booth-v5.exe) must be built separately and placed in server/.
 */
const fs = require('fs');
const path = require('path');

const V5_ROOT = path.join(__dirname, '..');
const SERVER_DIR = path.join(__dirname, 'server');

const ASSETS = [
  // Front-end (load order 0→7)
  'paint-booth-v2.html',
  'paint-booth-v2.css',
  'paint-booth-0-finish-data.js',   // NEW: pure data arrays (single source of truth)
  'paint-booth-1-data.js',          // Logic: TGA decoder, server merge
  'paint-booth-2-state-zones.js',
  'paint-booth-3-canvas.js',
  'paint-booth-4-pattern-renderer.js',
  'paint-booth-5-api-render.js',
  'paint-booth-6-ui-boot.js',
  'paint-booth-7-shokk.js',
  'fusion-swatches.js',
  'swatch-upgrades.js',
  'swatch-upgrades-2.js',
  'swatch-upgrades-3.js',
  // Backend Python
  'config.py',
  'server.py',
  'server_v5.py',
  'shokk_manager.py',
  'shokker_engine_v2.py',
  // Backward-compat shims (real code in engine/expansions/)
  'shokker_24k_expansion.py',
  'shokker_color_monolithics.py',
  'shokker_fusions_expansion.py',
  'shokker_paradigm_expansion.py',
  'shokker_specials_overhaul.py',
  'finish_colors_lookup.py',
  'finish_colors.json',
];

// Optional: copy engine/ and other Python deps if the EXE is not fully self-contained
const COPY_ENGINE = true;
const ENGINE_DIR = path.join(V5_ROOT, 'engine');

// Optional: copy pre-rendered thumbnails so packaged app shows accurate swatches without live render
const COPY_THUMBNAILS = true;
const THUMBNAILS_DIR = path.join(V5_ROOT, 'thumbnails');

// Copy assets/ (pattern PNGs, etc.) for image-based patterns
const COPY_ASSETS = true;
const ASSETS_DIR = path.join(V5_ROOT, 'assets');

// Copy _staging/pattern_upgrades so engine can load 20-per-decade patterns
const COPY_STAGING = true;
const STAGING_DIR = path.join(V5_ROOT, '_staging');

function copyDirRecursive(srcDir, destDir) {
  if (!fs.existsSync(srcDir)) return 0;
  if (!fs.existsSync(destDir)) fs.mkdirSync(destDir, { recursive: true });
  let n = 0;
  for (const f of fs.readdirSync(srcDir)) {
    const src = path.join(srcDir, f);
    const dest = path.join(destDir, f);
    if (fs.statSync(src).isDirectory()) {
      n += copyDirRecursive(src, dest);
    } else {
      fs.copyFileSync(src, dest);
      n++;
    }
  }
  return n;
}

if (!fs.existsSync(SERVER_DIR)) {
  fs.mkdirSync(SERVER_DIR, { recursive: true });
  console.log('[copy-server] Created server/');
}

let copied = 0;
for (const name of ASSETS) {
  const src = path.join(V5_ROOT, name);
  const dest = path.join(SERVER_DIR, name);
  if (fs.existsSync(src)) {
    fs.copyFileSync(src, dest);
    copied++;
  }
}

if (COPY_ENGINE && fs.existsSync(ENGINE_DIR)) {
  const destEngine = path.join(SERVER_DIR, 'engine');
  // Recurse into engine/ (includes engine/expansions/) so all modules are copied
  const n = copyDirRecursive(ENGINE_DIR, destEngine);
  copied += n;
  console.log(`[copy-server] Engine: ${n} files (including expansions/)`);
}

if (COPY_THUMBNAILS && fs.existsSync(THUMBNAILS_DIR)) {
  const destThumb = path.join(SERVER_DIR, 'thumbnails');
  const n = copyDirRecursive(THUMBNAILS_DIR, destThumb);
  copied += n;
  if (n > 0) console.log(`[copy-server] Thumbnails: ${n} PNGs`);
}

if (COPY_ASSETS && fs.existsSync(ASSETS_DIR)) {
  const destAssets = path.join(SERVER_DIR, 'assets');
  const n = copyDirRecursive(ASSETS_DIR, destAssets);
  copied += n;
  if (n > 0) console.log(`[copy-server] Assets: ${n} files`);
}

if (COPY_STAGING && fs.existsSync(STAGING_DIR)) {
  const destStaging = path.join(SERVER_DIR, '_staging');
  const n = copyDirRecursive(STAGING_DIR, destStaging);
  copied += n;
  if (n > 0) console.log(`[copy-server] Staging: ${n} files`);
}

// Copy shokk_factory (pre-built factory SHOKK files)
const SHOKK_FACTORY_SRC = path.join(V5_ROOT, 'shokk_factory');
const SHOKK_FACTORY_DEST = path.join(SERVER_DIR, 'shokk_factory');
if (fs.existsSync(SHOKK_FACTORY_SRC)) {
  const n = copyDirRecursive(SHOKK_FACTORY_SRC, SHOKK_FACTORY_DEST);
  copied += n;
  if (n > 0) console.log(`[copy-server] SHOKK Factory: ${n} files`);
} else {
  // Create empty factory dir so app can still start
  if (!fs.existsSync(SHOKK_FACTORY_DEST)) fs.mkdirSync(SHOKK_FACTORY_DEST, { recursive: true });
}

// Verify bundled portable Python exists (set up by setup_portable_python.py)
const PYTHON_DIR = path.join(SERVER_DIR, 'python');
const PYTHON_EXE = path.join(PYTHON_DIR, 'python.exe');
if (fs.existsSync(PYTHON_EXE)) {
  const pythonFiles = fs.readdirSync(PYTHON_DIR, { recursive: true }).length;
  console.log(`[copy-server] Bundled Python: OK (${pythonFiles} items)`);
} else {
  console.error('[copy-server] ERROR: Bundled Python not found at server/python/');
  console.error('[copy-server]   Run: C:\\Python313\\python.exe setup_portable_python.py');
  process.exit(1);
}

// ===== CRITICAL: Verify bundled Python has ALL required packages =====
// Without these, the server WILL crash on any machine except the dev machine.
// The bundled Python must be SELF-CONTAINED — no reliance on user site-packages.
const { execSync } = require('child_process');
const REQUIRED_PACKAGES = [
  { module: 'flask', name: 'Flask' },
  { module: 'flask_cors', name: 'flask-cors' },
  { module: 'numpy', name: 'numpy' },
  { module: 'PIL', name: 'Pillow' },
  { module: 'scipy', name: 'scipy' },
];
const SITE_PACKAGES = path.join(PYTHON_DIR, 'Lib', 'site-packages');

console.log('[copy-server] Verifying bundled Python packages...');
let missingPackages = [];

for (const pkg of REQUIRED_PACKAGES) {
  // Check if the package directory actually exists in the bundled site-packages
  // (NOT in the user's global site-packages — that's the bug we're preventing)
  const pkgDir = path.join(SITE_PACKAGES, pkg.module);
  const pkgDirAlt = path.join(SITE_PACKAGES, pkg.module.toLowerCase());
  if (!fs.existsSync(pkgDir) && !fs.existsSync(pkgDirAlt)) {
    missingPackages.push(pkg);
  }
}

if (missingPackages.length > 0) {
  console.log(`[copy-server] Missing ${missingPackages.length} package(s) in bundled Python. Installing...`);
  const pipTarget = SITE_PACKAGES;
  const pipPkgs = missingPackages.map(p => p.name).join(' ');
  try {
    execSync(`"${PYTHON_EXE}" -m pip install --target="${pipTarget}" --no-user ${pipPkgs}`, {
      stdio: 'inherit',
      timeout: 300000 // 5 min max
    });
    console.log('[copy-server] Package installation complete.');
  } catch (err) {
    console.error('[copy-server] FATAL: Failed to install packages into bundled Python!');
    console.error('[copy-server]   ' + err.message);
    process.exit(1);
  }
}

// FINAL VERIFICATION: Actually import each package with PYTHONNOUSERSITE=1
// This simulates what happens on an end-user's machine with NO Python installed
console.log('[copy-server] Final verification (simulating clean machine)...');
let verifyFailed = false;
for (const pkg of REQUIRED_PACKAGES) {
  try {
    execSync(
      `"${PYTHON_EXE}" -c "import ${pkg.module}"`,
      { env: { ...process.env, PYTHONNOUSERSITE: '1' }, timeout: 30000, stdio: 'pipe' }
    );
    console.log(`  ✓ ${pkg.name}`);
  } catch (err) {
    console.error(`  ✗ ${pkg.name} — IMPORT FAILED`);
    verifyFailed = true;
  }
}

if (verifyFailed) {
  console.error('');
  console.error('[copy-server] ══════════════════════════════════════════════════════');
  console.error('[copy-server] FATAL: Bundled Python is missing required packages!');
  console.error('[copy-server] The installer WILL produce a broken app.');
  console.error('[copy-server] Fix: pip install --target=server/python/Lib/site-packages <pkg>');
  console.error('[copy-server] ══════════════════════════════════════════════════════');
  process.exit(1);
}

console.log('[copy-server] All packages verified — bundled Python is self-contained.');
console.log(`[copy-server] Copied ${copied} assets to server/`);
