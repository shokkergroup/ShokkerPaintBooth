const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const APP_DIR = __dirname;
const PACKAGE_PATH = path.join(APP_DIR, 'package.json');
const TEMP_CONFIG_PATH = path.join(APP_DIR, 'electron-builder.contributor.tmp.json');
const FLAG_PATH = path.join(APP_DIR, 'contributor-build.flag');

const pkg = JSON.parse(fs.readFileSync(PACKAGE_PATH, 'utf8'));
const baseBuild = pkg.build || {};
const contributorName = 'Shokker Paint Booth V6 Contributor Test';

function uniqueFiles(files) {
  return Array.from(new Set([...(files || []), 'contributor-build.flag']));
}

const contributorBuild = {
  ...baseBuild,
  appId: `${baseBuild.appId || 'com.shokker.paintbooth.v6'}.contributor`,
  productName: contributorName,
  directories: {
    ...(baseBuild.directories || {}),
    output: 'dist-contributor-portable',
  },
  win: {
    ...(baseBuild.win || {}),
    target: 'zip',
    artifactName: 'ShokkerPaintBoothV6-ContributorTest-${version}-Portable.${ext}',
  },
  nsis: {
    ...(baseBuild.nsis || {}),
    shortcutName: contributorName,
  },
  files: uniqueFiles(baseBuild.files),
  extraMetadata: {
    ...(baseBuild.extraMetadata || {}),
    productName: contributorName,
    contributorTestBuild: true,
  },
};

function run(command, args) {
  const result = spawnSync(command, args, {
    cwd: APP_DIR,
    stdio: 'inherit',
    env: {
      ...process.env,
      SPB_CONTRIBUTOR_BUILD: '1',
    },
    windowsHide: true,
  });
  if (result.error) {
    throw result.error;
  }
  if (result.status !== 0) {
    const shown = [command, ...args].join(' ');
    throw new Error(`${shown} failed with exit code ${result.status}`);
  }
}

try {
  fs.writeFileSync(FLAG_PATH, 'SPB contributor test build - license gate bypass enabled.\n', 'utf8');
  fs.writeFileSync(TEMP_CONFIG_PATH, JSON.stringify(contributorBuild, null, 2), 'utf8');

  run(process.execPath, ['copy-server-assets.js']);
  run(process.execPath, [
    path.join(APP_DIR, 'node_modules', 'electron-builder', 'cli.js'),
    '--win',
    '--x64',
    '--config',
    TEMP_CONFIG_PATH,
  ]);

  console.log('');
  console.log(`Contributor package output: ${path.join(APP_DIR, contributorBuild.directories.output)}`);
} finally {
  for (const tempPath of [TEMP_CONFIG_PATH, FLAG_PATH]) {
    try {
      if (fs.existsSync(tempPath)) fs.unlinkSync(tempPath);
    } catch (_) {}
  }
}
