const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');
const { loadManifest, syncRuntimeCopies } = require(path.join(__dirname, '..', 'scripts', 'sync-runtime-copies.js'));

const REPO_ROOT = path.join(__dirname, '..');
const SERVER_DIR = path.join(__dirname, 'server');
const FRONTEND_ASSETS = loadManifest().files;
const BACKEND_ASSETS = [
  'config.py',
  'server.py',
  'server_v5.py',
  'shokk_manager.py',
  'shokker_engine_v2.py',
  'shokker_24k_expansion.py',
  'shokker_color_monolithics.py',
  'shokker_fusions_expansion.py',
  'shokker_paradigm_expansion.py',
  'shokker_specials_overhaul.py',
  'finish_colors_lookup.py',
  'finish_colors.json',
];
const ASSETS = [...FRONTEND_ASSETS, ...BACKEND_ASSETS];

const COPY_ENGINE = true;
const ENGINE_DIR = path.join(REPO_ROOT, 'engine');

const COPY_THUMBNAILS = true;
const THUMBNAILS_DIR = path.join(REPO_ROOT, 'thumbnails');

const COPY_ASSETS = true;
const ASSETS_DIR = path.join(REPO_ROOT, 'assets');

const COPY_STAGING = true;
const STAGING_DIR = path.join(REPO_ROOT, '_staging');

// ----- IMPROVEMENT #42: structured progress / timing -----
const T0 = Date.now();
function log(tag, msg) {
  const elapsed = ((Date.now() - T0) / 1000).toFixed(2).padStart(6);
  console.log(`[copy-server +${elapsed}s] ${tag} ${msg}`);
}

// ----- IMPROVEMENT #44: track every copied file for a manifest -----
const copiedManifest = []; // { src, dest, bytes }
let copiedBytes = 0;

// ----- IMPROVEMENT #43: pre-flight path / destination validation -----
function ensureDir(dir) {
  if (!dir) throw new Error('ensureDir: empty path');
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  if (!fs.statSync(dir).isDirectory()) throw new Error(`Not a directory: ${dir}`);
}
function assertExists(p, kind) {
  if (!fs.existsSync(p)) throw new Error(`Missing ${kind}: ${p}`);
}

function copyFileTracked(src, dest) {
  ensureDir(path.dirname(dest));
  fs.copyFileSync(src, dest);
  let size = 0;
  try { size = fs.statSync(dest).size; } catch (_) {}
  copiedManifest.push({ src, dest, bytes: size });
  copiedBytes += size;
  return 1;
}

function copyDirRecursive(srcDir, destDir) {
  if (!fs.existsSync(srcDir)) return 0;
  ensureDir(destDir);
  let count = 0;
  for (const name of fs.readdirSync(srcDir)) {
    const src = path.join(srcDir, name);
    const dest = path.join(destDir, name);
    if (fs.statSync(src).isDirectory()) {
      count += copyDirRecursive(src, dest);
    } else {
      count += copyFileTracked(src, dest);
    }
  }
  return count;
}

// ----- IMPROVEMENT #45: parallel copy for large directories (engine / thumbnails / assets) -----
// Copies files through multiple workers to speed up the slowest step (file I/O on spinning disks).
async function copyDirParallel(srcDir, destDir, concurrency = 8) {
  if (!fs.existsSync(srcDir)) return 0;
  ensureDir(destDir);
  const jobs = [];
  function collect(s, d) {
    for (const name of fs.readdirSync(s)) {
      const src = path.join(s, name);
      const dest = path.join(d, name);
      if (fs.statSync(src).isDirectory()) {
        ensureDir(dest);
        collect(src, dest);
      } else {
        jobs.push([src, dest]);
      }
    }
  }
  collect(srcDir, destDir);
  let count = 0;
  let idx = 0;
  async function worker() {
    while (idx < jobs.length) {
      const i = idx++;
      const [src, dest] = jobs[i];
      try {
        await fs.promises.copyFile(src, dest);
        let size = 0;
        try { size = (await fs.promises.stat(dest)).size; } catch (_) {}
        copiedManifest.push({ src, dest, bytes: size });
        copiedBytes += size;
        count++;
      } catch (e) {
        console.error(`[copy-server] copy fail ${src} -> ${dest}: ${e.message}`);
        throw e;
      }
    }
  }
  await Promise.all(Array.from({ length: concurrency }, () => worker()));
  return count;
}

(async function main() {
  log('init', `repo=${REPO_ROOT}`);

  // ----- IMPROVEMENT #43: validate critical paths BEFORE writing anything -----
  assertExists(REPO_ROOT, 'repo root');
  ensureDir(SERVER_DIR);
  log('dirs', `server=${SERVER_DIR}`);

  const runtimeSync = syncRuntimeCopies({ write: true, verbose: true });
  if (runtimeSync.missingSources.length > 0) {
    console.error('[copy-server] FATAL: runtime sync is missing source files.');
    process.exit(1);
  }
  log('runtime-sync', 'OK');

  // ----- Flat assets (config.py, server.py, JS/HTML files) -----
  // BACKEND_ASSETS are required — any missing backend file is a hard fail.
  // FRONTEND_ASSETS (from manifest) are also required.
  // Only truly-optional files can be skipped without failing the build.
  let copied = 0;
  const missingRequired = [];
  for (const name of ASSETS) {
    const src = path.join(REPO_ROOT, name);
    const dest = path.join(SERVER_DIR, name);
    if (fs.existsSync(src)) {
      copied += copyFileTracked(src, dest);
    } else {
      missingRequired.push(name);
    }
  }
  if (missingRequired.length > 0) {
    console.error('');
    console.error('[copy-server] FATAL: ' + missingRequired.length + ' required asset(s) missing from repo root:');
    for (const m of missingRequired) console.error('  - ' + m);
    console.error('[copy-server] The installer would be broken. Aborting build.');
    process.exit(1);
  }
  log('assets', `flat files: ${copied} copied`);

  if (COPY_ENGINE && fs.existsSync(ENGINE_DIR)) {
    const destEngine = path.join(SERVER_DIR, 'engine');
    const count = await copyDirParallel(ENGINE_DIR, destEngine, 8);
    copied += count;
    log('engine', `${count} files`);
  }

  if (COPY_THUMBNAILS && fs.existsSync(THUMBNAILS_DIR)) {
    const destThumb = path.join(SERVER_DIR, 'thumbnails');
    const count = await copyDirParallel(THUMBNAILS_DIR, destThumb, 12);
    copied += count;
    if (count > 0) log('thumbnails', `${count} files`);
  }

  if (COPY_ASSETS && fs.existsSync(ASSETS_DIR)) {
    const destAssets = path.join(SERVER_DIR, 'assets');
    const count = await copyDirParallel(ASSETS_DIR, destAssets, 8);
    copied += count;
    if (count > 0) log('assets-dir', `${count} files`);
  }

  if (COPY_STAGING && fs.existsSync(STAGING_DIR)) {
    const destStaging = path.join(SERVER_DIR, '_staging');
    const count = copyDirRecursive(STAGING_DIR, destStaging); // kept sync — typically small
    copied += count;
    if (count > 0) log('staging', `${count} files`);
  }

  const SHOKK_FACTORY_SRC = path.join(REPO_ROOT, 'shokk_factory');
  const SHOKK_FACTORY_DEST = path.join(SERVER_DIR, 'shokk_factory');
  if (fs.existsSync(SHOKK_FACTORY_SRC)) {
    const count = copyDirRecursive(SHOKK_FACTORY_SRC, SHOKK_FACTORY_DEST);
    copied += count;
    if (count > 0) log('shokk-factory', `${count} files`);
  } else if (!fs.existsSync(SHOKK_FACTORY_DEST)) {
    ensureDir(SHOKK_FACTORY_DEST);
  }

  const PYTHON_DIR = path.join(SERVER_DIR, 'python');
  const PYTHON_EXE = path.join(PYTHON_DIR, 'python.exe');
  if (fs.existsSync(PYTHON_EXE)) {
    const pythonItems = fs.readdirSync(PYTHON_DIR, { recursive: true }).length;
    log('python', `bundled: OK (${pythonItems} items)`);
  } else {
    console.error('[copy-server] ERROR: Bundled Python not found at server/python/');
    console.error('[copy-server]   Run: C:\\Python313\\python.exe setup_portable_python.py');
    process.exit(1);
  }

  const REQUIRED_PACKAGES = [
    { module: 'flask', name: 'Flask' },
    { module: 'flask_cors', name: 'flask-cors' },
    { module: 'numpy', name: 'numpy' },
    { module: 'PIL', name: 'Pillow' },
    { module: 'scipy', name: 'scipy' },
    { module: 'cv2', name: 'opencv-python-headless' },
    { module: 'psd_tools', name: 'psd-tools' },
  ];
  const SITE_PACKAGES = path.join(PYTHON_DIR, 'Lib', 'site-packages');

  // ----- IMPROVEMENT #41: Pre-check bundled Python BEFORE any copy work is trusted -----
  // (We already copied flat assets above for speed; this still runs before the final
  // verification step and before the manifest is written, which is what consumers rely on.)
  log('python-check', 'verifying bundled Python packages...');
  const missingPackages = [];
  for (const pkg of REQUIRED_PACKAGES) {
    const pkgDir = path.join(SITE_PACKAGES, pkg.module);
    const pkgDirAlt = path.join(SITE_PACKAGES, pkg.module.toLowerCase());
    if (!fs.existsSync(pkgDir) && !fs.existsSync(pkgDirAlt)) {
      missingPackages.push(pkg);
    }
  }

  // IMPORTANT: Do NOT run `pip install` during packaging. Mutating the bundled
  // runtime at build time makes builds machine-dependent and non-reproducible,
  // and masks the fact that the vendored Python is incomplete. If something is
  // missing, fail loudly and require the developer to provision the bundled
  // Python up-front via `setup_portable_python.py` (or an equivalent script).
  if (missingPackages.length > 0) {
    console.error('');
    console.error('[copy-server] FATAL: Bundled Python is missing required packages.');
    console.error('[copy-server]   Missing: ' + missingPackages.map(p => p.name).join(', '));
    console.error('[copy-server]');
    console.error('[copy-server] Builds MUST NOT mutate the bundled runtime at packaging time.');
    console.error('[copy-server] To provision the bundled Python, run (ONCE, outside of builds):');
    console.error('[copy-server]   "' + PYTHON_EXE + '" -m pip install --target="' + SITE_PACKAGES + '" --no-user ' + missingPackages.map(p => p.name).join(' '));
    console.error('[copy-server]');
    console.error('[copy-server] Or regenerate the portable Python with setup_portable_python.py.');
    process.exit(1);
  }
  log('python-check', 'all required packages already present');

  log('python-verify', 'final verification (simulating clean machine)...');
  let verifyFailed = false;
  for (const pkg of REQUIRED_PACKAGES) {
    try {
      execSync(`"${PYTHON_EXE}" -c "import ${pkg.module}"`, {
        env: { ...process.env, PYTHONNOUSERSITE: '1' },
        timeout: 30000,
        stdio: 'pipe',
      });
      log('python-verify', `OK ${pkg.name}`);
    } catch (err) {
      console.error(`  FAIL ${pkg.name} - import failed`);
      verifyFailed = true;
    }
  }

  if (verifyFailed) {
    console.error('');
    console.error('[copy-server] FATAL: Bundled Python is missing required packages!');
    console.error('[copy-server] The installer would be broken.');
    console.error('[copy-server] Fix: pip install --target=server/python/Lib/site-packages <pkg>');
    process.exit(1);
  }

  log('python-verify', 'all packages verified - bundled Python is self-contained.');

  // ----- IMPROVEMENT #44: Write manifest of copied files for debugging / audits -----
  try {
    const manifestPath = path.join(SERVER_DIR, '_copy-manifest.json');
    const manifest = {
      generated_at: new Date().toISOString(),
      repo_root: REPO_ROOT,
      server_dir: SERVER_DIR,
      total_files: copiedManifest.length,
      total_bytes: copiedBytes,
      elapsed_seconds: Number(((Date.now() - T0) / 1000).toFixed(2)),
      required_python_packages: REQUIRED_PACKAGES.map((p) => p.name),
      files: copiedManifest.map((f) => ({
        rel: path.relative(SERVER_DIR, f.dest).replace(/\\/g, '/'),
        bytes: f.bytes,
      })),
    };
    fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2), 'utf8');
    log('manifest', `wrote ${manifestPath} (${manifest.total_files} files, ${(manifest.total_bytes / 1024 / 1024).toFixed(1)} MiB)`);
  } catch (e) {
    console.error('[copy-server] WARN: failed to write manifest:', e.message);
  }

  log('done', `copied ${copied} assets to server/ in ${((Date.now() - T0) / 1000).toFixed(2)}s`);
})().catch((err) => {
  console.error('[copy-server] FATAL:', err && err.stack || err);
  process.exit(1);
});
