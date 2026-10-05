const fs = require('fs');
const os = require('os');
const path = require('path');
const { execSync, execFileSync } = require('child_process');
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
  // 2026-06-21: the boot swatch-warm (server_v5.py) shells out to this script to
  // re-bake ONLY changed picker thumbnails at startup. It was never in this list, so
  // it never shipped to electron-app/server -> the boot warm's os.path.isfile() check
  // failed and the auto-rebake silently no-oped (stale thumbnails after finish edits).
  'rebuild_picker_swatches.py',
  'finish_colors.json',
  // First-launch default source paint (SPB 2026-06-08): the Chevy truck starter PSD
  // must ship so /api/default-assets -> _default_asset_path() resolves it in the
  // packaged layout. It lands at resources\server\<filename>, which _default_asset_path
  // finds via its server-root (root_candidate) branch. 8MB.
  'SPB Chevy Truck Starting Example PSD.psd',
];
const ASSETS = [...FRONTEND_ASSETS, ...BACKEND_ASSETS];

const COPY_ENGINE = true;
const ENGINE_DIR = path.join(REPO_ROOT, 'engine');

// finish-pack/SHOKK DROP fix 2026-06-08: scripts/ was never copied into the build, so SHOKK DROP's
// runtime importlib loads (scripts/build_cultural_*.py) threw "No such file". scripts/ is only ~2MB.
const COPY_SCRIPTS = true;
const SCRIPTS_DIR = path.join(REPO_ROOT, 'scripts');

const COPY_THUMBNAILS = true;
const THUMBNAILS_DIR = path.join(REPO_ROOT, 'thumbnails');

const COPY_ASSETS = true;
const ASSETS_DIR = path.join(REPO_ROOT, 'assets');
const SLIM_CULTURAL_RUNTIME_PACKS = [
  ['cultural', 'union_jacked'],
  ['cultural', 'rising_sun'],
  ['cultural', 'viva_mexico'],
];

/** Multi-gig authoring refs; omit from installers unless explicitly requested (SPB_INCLUDE_REFERENCE_TEXTURES=1). */
const INCLUDE_REFERENCE_TEXTURES = process.env.SPB_INCLUDE_REFERENCE_TEXTURES === '1';

/**
 * "All-in-one bundle" mode (SPB_BUNDLE_ALL=1). Bakes EVERY premium finish-pack family's
 * reference_textures into the installer SLIM (2048-max) so nothing has to download in-app.
 * For a one-shot Cloudflare-R2-hosted install.
 *
 * Each pack ships to <SERVER_DIR>/assets/reference_textures/<rel> so the layout matches the
 * dev assets/reference_textures/<rel> exactly — which is what the engine loaders' bundled
 * path (engine.asset_packs.resolve_ref_dir -> <bundled>/assets/reference_textures/<rel>) and
 * their png_2048/jpg_2048 "prefer small" branches expect.
 *
 * variant: name of the 2048 sub-variant dir to ship INSTEAD of the 4K pack root images.
 *   - When set (png_2048 / jpg_2048): copy manifest.json + *.json at the pack root, then ONLY
 *     that variant subdir; the 4K originals at the pack root are DROPPED.
 *   - When null: the pack is already <=2048 — copy it recursively (incl. nested content subdirs
 *     like colorshoxx/ai_reference_*, spec_overlays/ricky_reference*, guest_designers/<key>),
 *     downscaling any stray image whose longest side >2048 to 2048 (preserve mode/alpha).
 */
const BUNDLE_ALL_PREMIUM = process.env.SPB_BUNDLE_ALL === '1';
const BUNDLE_ALL_PREMIUM_PACKS = [
  { rel: ['mortal_shokk'], variant: 'png_2048' },
  { rel: ['grunge_fun'], variant: 'jpg_2048' },
  { rel: ['cultural', 'forbidden_dragon'], variant: 'jpg_2048' },
  { rel: ['colorshoxx'], variant: null },
  { rel: ['pattern_plates'], variant: null },
  { rel: ['spec_overlays'], variant: null },
  { rel: ['guest_designers'], variant: null },
];

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
  // SPB-BUILD-2026-07-20: fs.copyFileSync (Windows CopyFile API) fails with
  // "UNKNOWN: unknown error, copyfile" when the DESTINATION is memory-mapped by
  // another process (e.g. a browser pane holding the served HTML) — it killed
  // three consecutive 8.0.4 builds on paint-booth-v2.html while a plain
  // stream-write to the same path succeeded every time. Fallback chain:
  // CopyFile → read+write streams → unlink-then-write (a fresh inode is never
  // someone else's mapping).
  try {
    fs.copyFileSync(src, dest);
  } catch (err1) {
    try {
      fs.writeFileSync(dest, fs.readFileSync(src));
      console.log(`[copy-server] copyfile fallback (stream write) used for ${path.basename(dest)}: ${err1.code || err1.message}`);
    } catch (err2) {
      fs.rmSync(dest, { force: true });
      fs.writeFileSync(dest, fs.readFileSync(src));
      console.log(`[copy-server] copyfile fallback (fresh inode) used for ${path.basename(dest)}`);
    }
  }
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

/** Like copyDirParallel but skips top-level directory names under srcDir (e.g. reference_textures). */
async function copyDirParallelSkip(srcDir, destDir, excludeTopLevelNames, concurrency = 8) {
  if (!fs.existsSync(srcDir)) return 0;
  ensureDir(destDir);
  const skip = new Set((excludeTopLevelNames || []).map((n) => n.toLowerCase()));
  const jobs = [];
  function collect(s, d, depth) {
    for (const name of fs.readdirSync(s)) {
      if (depth === 0 && skip.has(name.toLowerCase())) continue;
      const src = path.join(s, name);
      const dest = path.join(d, name);
      if (fs.statSync(src).isDirectory()) {
        ensureDir(dest);
        collect(src, dest, depth + 1);
      } else {
        jobs.push([src, dest]);
      }
    }
  }
  collect(srcDir, destDir, 0);
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

async function copySlimCulturalRuntimePacks(destAssetsDir) {
  let count = 0;
  const destRef = path.join(destAssetsDir, 'reference_textures');
  for (const parts of SLIM_CULTURAL_RUNTIME_PACKS) {
    const srcPack = path.join(ASSETS_DIR, 'reference_textures', ...parts);
    if (!fs.existsSync(srcPack)) continue;
    const destPack = path.join(destRef, ...parts);
    ensureDir(destPack);
    const manifest = path.join(srcPack, 'manifest.json');
    if (fs.existsSync(manifest)) {
      count += copyFileTracked(manifest, path.join(destPack, 'manifest.json'));
    }
    const jpgDir = path.join(srcPack, 'jpg_2048');
    if (fs.existsSync(jpgDir)) {
      count += await copyDirParallel(jpgDir, path.join(destPack, 'jpg_2048'), 8);
    }
  }
  return count;
}

// ===== "All-in-one bundle" (SPB_BUNDLE_ALL) — bake every premium pack SLIM =====

const IMAGE_EXTS = new Set(['.png', '.jpg', '.jpeg', '.tga']);
const BUNDLE_MAX_SIDE = 2048;

// Lazily-written temp resize helper script. We invoke it as `python <script> <src> <dest> <max>`
// instead of `python -c "<inline>"` because multi-line code passed to `-c` through cmd.exe loses
// its newlines (it ends up a broken one-liner). A real .py file sidesteps all shell escaping.
const _BUNDLE_RESIZE_PY = `import sys
from PIL import Image
s, d, m = sys.argv[1], sys.argv[2], int(sys.argv[3])
im = Image.open(s)
w, h = im.size
longest = max(w, h)
if longest > m:
    sc = m / float(longest)
    nw, nh = max(1, round(w * sc)), max(1, round(h * sc))
    im = im.resize((nw, nh), Image.LANCZOS)
    im.save(d)
    print("RESIZED")
else:
    print("COPYAS-IS")
`;
let _bundleResizeScriptPath = null;
function _ensureBundleResizeScript() {
  if (_bundleResizeScriptPath && fs.existsSync(_bundleResizeScriptPath)) return _bundleResizeScriptPath;
  const tmp = path.join(os.tmpdir(), `spb_bundle_resize_${process.pid}.py`);
  fs.writeFileSync(tmp, _BUNDLE_RESIZE_PY, 'utf8');
  _bundleResizeScriptPath = tmp;
  return tmp;
}

/**
 * Copy a single image file into the build, downscaling to BUNDLE_MAX_SIDE on its longest side
 * if (and only if) it currently exceeds it. Preserves mode/alpha (PIL keeps the source mode through
 * resize + save). Uses the bundled Python's PIL via a tiny temp script (the build already verifies
 * Pillow is present). If the resize cannot run for any reason, falls back to a verbatim copy.
 * Returns the number of files written (always 1).
 *
 * NOTE: this NEVER writes back to `src`; the dev source stays untouched — we only ever write `dest`.
 */
function copyImageTrackedSlim(src, dest, pythonExe) {
  ensureDir(path.dirname(dest));
  let resized = false;
  if (pythonExe && IMAGE_EXTS.has(path.extname(src).toLowerCase())) {
    try {
      const script = _ensureBundleResizeScript();
      const out = execSync(
        `"${pythonExe}" "${script}" "${src}" "${dest}" ${BUNDLE_MAX_SIDE}`,
        { env: { ...process.env, PYTHONNOUSERSITE: '1' }, timeout: 120000, stdio: 'pipe' }
      ).toString();
      // The script only writes `dest` when it actually downscaled (prints RESIZED). When the image
      // is already <=2048 it prints COPYAS-IS and writes nothing, so we copy verbatim below.
      if (out.includes('RESIZED')) resized = true;
    } catch (e) {
      // Probe/resize failed — fall back to verbatim copy below.
      resized = false;
    }
  }
  if (!resized) {
    fs.copyFileSync(src, dest);
  }
  let size = 0;
  try { size = fs.statSync(dest).size; } catch (_) {}
  copiedManifest.push({ src, dest, bytes: size });
  copiedBytes += size;
  return 1;
}

/** Recursively copy a dir, downscaling any image >2048 (only writes to dest; src untouched). */
function copyDirRecursiveSlim(srcDir, destDir, pythonExe) {
  if (!fs.existsSync(srcDir)) return 0;
  ensureDir(destDir);
  let count = 0;
  for (const name of fs.readdirSync(srcDir)) {
    const src = path.join(srcDir, name);
    const dest = path.join(destDir, name);
    if (fs.statSync(src).isDirectory()) {
      count += copyDirRecursiveSlim(src, dest, pythonExe);
    } else if (IMAGE_EXTS.has(path.extname(name).toLowerCase())) {
      count += copyImageTrackedSlim(src, dest, pythonExe);
    } else {
      count += copyFileTracked(src, dest);
    }
  }
  return count;
}

/**
 * SPB_BUNDLE_ALL: bake every premium pack into <destAssetsDir>/reference_textures SLIM.
 * Packs with a png_2048/jpg_2048 variant ship ONLY that variant (+ root *.json) and DROP the 4K
 * pack-root originals. Packs already <=2048 ship recursively with a >2048 safety downscale.
 */
async function bundleAllPremiumPacks(destAssetsDir, pythonExe) {
  let count = 0;
  let bundledBytesBefore = copiedBytes;
  const destRef = path.join(destAssetsDir, 'reference_textures');
  for (const pack of BUNDLE_ALL_PREMIUM_PACKS) {
    const srcPack = path.join(ASSETS_DIR, 'reference_textures', ...pack.rel);
    if (!fs.existsSync(srcPack)) {
      log('bundle-all', `SKIP missing pack ${pack.rel.join('/')}`);
      continue;
    }
    const destPack = path.join(destRef, ...pack.rel);
    ensureDir(destPack);
    let packCount = 0;

    if (pack.variant) {
      // Variant packs: copy root *.json (manifest etc.) + ONLY the 2048 variant subdir.
      // The 4K originals at the pack root are intentionally NOT copied.
      for (const name of fs.readdirSync(srcPack)) {
        if (name.toLowerCase().endsWith('.json')) {
          packCount += copyFileTracked(path.join(srcPack, name), path.join(destPack, name));
        }
      }
      const variantSrc = path.join(srcPack, pack.variant);
      if (fs.existsSync(variantSrc)) {
        packCount += await copyDirParallel(variantSrc, path.join(destPack, pack.variant), 8);
      } else {
        // Variant expected but absent — fall back to a recursive slim copy so the pack still ships.
        log('bundle-all', `WARN ${pack.rel.join('/')} has no ${pack.variant}; recursive-slim fallback`);
        packCount += copyDirRecursiveSlim(srcPack, destPack, pythonExe);
      }
    } else {
      // Already-<=2048 packs: recursive copy incl. nested content subdirs; downscale stray >2048.
      packCount += copyDirRecursiveSlim(srcPack, destPack, pythonExe);
    }

    count += packCount;
    log('bundle-all', `${pack.rel.join('/')}: ${packCount} files${pack.variant ? ` (${pack.variant} only, 4K dropped)` : ' (recursive slim)'}`);
  }
  const bundledMiB = ((copiedBytes - bundledBytesBefore) / 1024 / 1024).toFixed(1);
  log('bundle-all', `premium bundle: ${count} files, ${bundledMiB} MiB`);
  // Clean up the temp resize helper script (best-effort).
  if (_bundleResizeScriptPath) {
    try { fs.rmSync(_bundleResizeScriptPath, { force: true }); } catch (_) {}
    _bundleResizeScriptPath = null;
  }
  return count;
}

(async function main() {
  log('init', `repo=${REPO_ROOT}`);

  // ----- IMPROVEMENT #43: validate critical paths BEFORE writing anything -----
  assertExists(REPO_ROOT, 'repo root');
  // Owner 2026-10-02: a build cannot silently ship a cold/on-demand picker.
  // Exact catalog tints + renderer identities must have current masters/cards.
  execFileSync(process.execPath, [path.join(REPO_ROOT, 'tests/picker_baked_loading_contract.cjs')],
    { cwd: REPO_ROOT, stdio: 'inherit', env: { ...process.env, ELECTRON_RUN_AS_NODE: '1' } });
  execFileSync(process.execPath, [path.join(REPO_ROOT, 'scripts/spb_picker_catalog.cjs'), '--check'],
    { cwd: REPO_ROOT, stdio: 'inherit', env: { ...process.env, ELECTRON_RUN_AS_NODE: '1' } });
  const pickerPython = process.env.SPB_PYTHON ||
    (fs.existsSync(path.join(SERVER_DIR, 'python/python.exe')) ? path.join(SERVER_DIR, 'python/python.exe') : 'python');
  execFileSync(pickerPython, [path.join(REPO_ROOT, 'scripts/bake_faithful_picker.py'), '--check'],
    { cwd: REPO_ROOT, stdio: 'inherit', windowsHide: true });
  ensureDir(SERVER_DIR);
  log('dirs', `server=${SERVER_DIR}`);

  const runtimeSync = syncRuntimeCopies({ write: true, verbose: true });
  if (runtimeSync.missingSources.length > 0) {
    console.error('[copy-server] FATAL: runtime sync is missing source files.');
    process.exit(1);
  }
  // 2026-06-09 anti-drift GATE: after the write pass, re-run a check-only pass and HARD-FAIL the
  // build if any writable (managed-code) mirror is STILL drifted — i.e. a copy silently failed
  // (EBUSY / locked file on Windows). Guarantees the shipped electron-app/server tree always
  // matches repo root; a stale mirror can no longer slip into a release. (engine/ check-only drift
  // is owner-managed and intentionally NOT a build blocker.)
  const runtimeVerify = syncRuntimeCopies({ write: false, quiet: true });
  if (runtimeVerify.writableDriftCount > 0) {
    console.error('[copy-server] FATAL: ' + runtimeVerify.writableDriftCount + ' managed-code mirror file(s) STILL drifted after sync --write (a copy likely failed / was locked):');
    for (const p of runtimeVerify.drift.filter((d) => !d.checkOnly)) {
      console.error('  ' + p.sourceRel + ' -> ' + p.targetRel);
    }
    console.error('[copy-server] Refusing to build a stale mirror. Close any process locking electron-app/server and retry.');
    process.exit(1);
  }
  log('runtime-sync', 'OK (verified: no managed-code drift)');

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

  if (COPY_SCRIPTS && fs.existsSync(SCRIPTS_DIR)) {
    const destScripts = path.join(SERVER_DIR, 'scripts');
    const count = await copyDirParallel(SCRIPTS_DIR, destScripts, 8);
    copied += count;
    log('scripts', `${count} files`);
  }

  // OFFLINE_BUILDER 2026-10-04 (SPB Encyclopedia reader): the article files, generated pages and figures the
  // reader (js/spb-encyclopedia.js) fetches from /data/encyclopedia/** (server_v5.py route). Drafts stay home.
  const ENC_DIR = path.join(REPO_ROOT, 'data', 'encyclopedia');
  if (fs.existsSync(ENC_DIR)) {
    const count = await copyDirParallelSkip(ENC_DIR, path.join(SERVER_DIR, 'data', 'encyclopedia'), ['_drafts'], 8);
    copied += count;
    log('encyclopedia', `${count} files`);
  }

  if (COPY_THUMBNAILS && fs.existsSync(THUMBNAILS_DIR)) {
    const destThumb = path.join(SERVER_DIR, 'thumbnails');
    const count = await copyDirParallel(THUMBNAILS_DIR, destThumb, 12);
    copied += count;
    if (count > 0) log('thumbnails', `${count} files`);
  }

  if (COPY_ASSETS && fs.existsSync(ASSETS_DIR)) {
    const destAssets = path.join(SERVER_DIR, 'assets');
    const refDest = path.join(destAssets, 'reference_textures');
    // SPB_BUNDLE_ALL ships SLIM 2048 packs. We must NOT also bulk-copy the 4K reference_textures
    // for these families, so when bundling-all we skip reference_textures from the bulk copy even
    // if SPB_INCLUDE_REFERENCE_TEXTURES is set (avoid shipping both 4K and 2048).
    const bulkRefTextures = INCLUDE_REFERENCE_TEXTURES && !BUNDLE_ALL_PREMIUM;
    if (!bulkRefTextures && fs.existsSync(refDest)) {
      fs.rmSync(refDest, { recursive: true, force: true });
      log('assets-dir', 'removed prior reference_textures (dev-only bulk; not shipped in this mode)');
    }
    const excludeAssets = bulkRefTextures ? [] : ['reference_textures'];
    const count = await copyDirParallelSkip(ASSETS_DIR, destAssets, excludeAssets, 8);
    copied += count;
    if (count > 0) {
      log('assets-dir', `${count} files${bulkRefTextures ? ' (reference_textures included, 4K)' : ''}`);
    }
    // Slim cultural runtime packs (rising_sun/union_jacked/viva_mexico) ship in every mode that
    // isn't the explicit 4K-include — including SPB_BUNDLE_ALL.
    if (!bulkRefTextures) {
      const slimCount = await copySlimCulturalRuntimePacks(destAssets);
      copied += slimCount;
      if (slimCount > 0) {
        log('assets-dir', `${slimCount} slim cultural reference texture files`);
      }
    }
    // SPB_BUNDLE_ALL: bake the 7 premium finish-pack families SLIM (2048-max) into the build so
    // nothing has to download in-app. Runs after the engine/scripts/assets copy above.
    if (BUNDLE_ALL_PREMIUM) {
      const bundlePythonExe = path.join(SERVER_DIR, 'python', 'python.exe');
      const pyForBundle = fs.existsSync(bundlePythonExe) ? bundlePythonExe : null;
      if (!pyForBundle) {
        log('bundle-all', 'WARN bundled Python not found yet; >2048 images will copy as-is (no downscale)');
      }
      const bundleCount = await bundleAllPremiumPacks(destAssets, pyForBundle);
      copied += bundleCount;
    }
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

  // 2026-06-09: the vestigial PyInstaller mirror `electron-app/server/pyserver/_internal` was
  // DELETED (it was excluded from the installer via package.json `!pyserver/**`, so it shipped to
  // nobody and only created 3-way drift). The old prune step that cleared its bundled
  // reference_textures is gone with it. Sync is now 2-copy: repo root -> electron-app/server.

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
