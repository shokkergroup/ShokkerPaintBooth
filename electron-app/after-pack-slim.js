// electron-builder afterPack (11.0.2 slim, owner 2026-10-16: "6GB").
// Re-encodes the reference/generated texture PNGs in the PACKAGED server as verified lossless WebP
// (same file names, identical decoded pixels) - see scripts/slim_packaged_textures.py.
// Runs on dist/win-unpacked only; the repo and electron-app/server keep their PNGs.
const { execFileSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const REPO_ROOT = path.resolve(__dirname, '..');

exports.default = async function afterPack(context) {
  const server = path.join(context.appOutDir, 'resources', 'server');
  const bundled = path.join(__dirname, 'server', 'python', 'python.exe');
  const python = process.env.SPB_PYTHON || (fs.existsSync(bundled) ? bundled : 'python');
  execFileSync(python, [path.join(REPO_ROOT, 'scripts', 'slim_packaged_textures.py'), 'apply', '--server', server],
    { cwd: REPO_ROOT, stdio: 'inherit', windowsHide: true });
};
