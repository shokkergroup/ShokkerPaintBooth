/* Guard: the 2026-09-05 BETA LAUNCH PREP fixes stay wired and stay shipped.
 *
 * Owner, 2026-09-05 ("BETA LAUNCH PREP"):
 *   1. "toggle between SHOKKER BROWSER and WINDOWS FILE EXPLORER ... showing up
 *      in Settings but nothing changes" -> the File Picker setting must reach a
 *      real Windows dialog in a browser tab too (server route /api/native-dialog).
 *   2. "The version number is jacked up and overlapping the iracing user id box"
 *      -> small badge, bottom-right of the logo, inside the 194px brand reserve.
 *   3. "The BASE COLOR LOCK box is JACKED UP AGAIN ... regresses way too often"
 *      -> the visible box is a SPAN no checkbox rule can touch.
 *
 * Each of these has regressed before because the fix lived in one file and a
 * later file (a new stylesheet, a token rename, a missed mirror sync) undid it
 * silently. This guard fails loudly on every one of those paths.
 *
 * Run: node tests/guard_beta_polish_20260905.js
 */
'use strict';
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const read = (rel) => fs.readFileSync(path.join(ROOT, rel), 'utf8');
const failures = [];
const check = (ok, message) => { (ok ? console.log : failures.push.bind(failures))((ok ? 'PASS  ' : 'FAIL  ') + message); };

const CSS_REL = 'css/spb-beta-polish-20260905.css';
const html = read('paint-booth-v2.html');
const css = read(CSS_REL);
const zones = read('paint-booth-2-state-zones.js');
const bridge = read('js/spb-native-file-dialogs.js');
const routes = read('server_routes/file_picker_routes.py');

// --- stylesheet is linked, live (not commented), and BEFORE the clean skin, which stays last
const liveLinks = html.split(/\r?\n/)
  .filter((line) => /<link rel="stylesheet"/.test(line) && !/^\s*<!--/.test(line))
  .map((line) => (line.match(/href="([^"?]+)/) || [])[1])
  .filter(Boolean);
const polishIdx = liveLinks.indexOf(CSS_REL);
const cleanIdx = liveLinks.indexOf('css/spb-clean-default-20260829.css');
check(polishIdx !== -1, `${CSS_REL} is linked live in paint-booth-v2.html`);
check(cleanIdx === liveLinks.length - 1, 'css/spb-clean-default-20260829.css is still the LAST live stylesheet link');
check(polishIdx !== -1 && polishIdx < cleanIdx, 'beta-polish link sits before the clean skin');
check(/spb-beta-polish-20260905\.css\?v=[A-Za-z0-9._-]+/.test(html), 'beta-polish link carries a ?v= cache token');

// --- 2. version badge rules
check(/\.header \.header-brand \.subtitle #liveBuildBadge\.version-badge\s*\{[^}]*font-size:\s*9px\s*!important/s.test(css),
  'badge rule: 9px !important on a selector more specific than #liveBuildBadge.version-badge');
check(/@media \(min-width: 1350px\)\s*\{[^@]*\.subtitle\s*\{[^}]*position:\s*absolute\s*!important[^}]*bottom:\s*\d+px\s*!important[^}]*max-width:\s*56px\s*!important/s.test(css),
  'badge rule (>=1350px): absolute, bottom-anchored, capped at 56px so 138 + 56 = 194 never reaches the User ID box at 212');
check(/background:\s*none\s*!important/.test(css) && /border:\s*0\s*!important/.test(css), 'badge is plain text (no pill background / border)');

// --- 3. lock box markup + rules
const lockMarkup = zones.match(/<label class="spb-lock-toggle"[\s\S]*?<\/label>/);
check(!!lockMarkup, 'state-zones renders <label class="spb-lock-toggle"> for Base Color lock');
if (lockMarkup) {
  const m = lockMarkup[0];
  check(/<input type="checkbox" class="spb-lock-input"/.test(m), 'lock: real checkbox carries class spb-lock-input');
  check(/onchange="setZoneLockBaseColor\(\$\{i\}, this\.checked\)"/.test(m), 'lock: checkbox still calls setZoneLockBaseColor');
  check(/<span class="spb-lock-box" aria-hidden="true"><\/span>/.test(m), 'lock: visible square is the .spb-lock-box span');
  check(!/width:10px; height:10px/.test(m), 'lock: the old 10px inline sizing is gone');
}
check(/\.spb-lock-toggle > \.spb-lock-box\s*\{[^}]*width:\s*14px\s*!important[^}]*height:\s*14px\s*!important[^}]*border:\s*2px solid/s.test(css),
  'lock rule: .spb-lock-box is a 14px square with a 2px border, all !important');
check(/input\.spb-lock-input\[type="checkbox"\]\s*\{[^}]*opacity:\s*0\s*!important[^}]*pointer-events:\s*none\s*!important/s.test(css),
  'lock rule: the real checkbox is transparent and inert (the span is the UI)');
check(/input\.spb-lock-input:checked \+ \.spb-lock-box\s*\{/.test(css), 'lock rule: checked state paints the span');

// --- 1. file picker setting reaches a dialog in a browser tab
check(/window\.fetch\('\/api\/native-dialog'/.test(bridge), 'bridge: browser tab posts to /api/native-dialog when the setting says Windows');
check(/function openWindowsFilePicker\(request\)\s*\{\s*if \(tryOpenNativeFilePicker\(request\)\) return true;\s*return openServerNativeDialog\(request\);/s.test(bridge),
  'bridge: Electron bridge first, server dialog second');
check(/function nativeAwareOpenFilePicker[\s\S]*?getMainFilePickerMode\(\) !== 'windows'\) return useLegacy/.test(bridge),
  'bridge: the generic openFilePicker wrapper honours the saved setting');
check(/function syncHeaderBrowseTooltips/.test(bridge) && /data-testid="btn-browse-output-dir"/.test(html),
  'bridge: header browse tooltips follow the setting (folder button has data-testid="btn-browse-output-dir")');
check(/@app\.route\('\/api\/native-dialog', methods=\['POST'\]\)/.test(routes), 'server: /api/native-dialog route registered in file_picker_routes.py');
check(/X-Shokker-Internal/.test(routes.slice(routes.indexOf("'/api/native-dialog'"))), 'server: route requires the SPB internal header');
check(/FOS_PICKFOLDERS/.test(routes) && /OpenFileDialog/.test(routes), 'server: folder picker is the Explorer-style IFileOpenDialog, files use OpenFileDialog');

// --- cache tokens: every file changed by this fix must carry a token newer than 2026-09-03
check(/spb-native-file-dialogs\.js\?v=spb-native-file-dialogs-2026090[5-9]/.test(html) || /spb-native-file-dialogs\.js\?v=spb-native-file-dialogs-20260[9]-?(1|2|3)\d/.test(html) || /spb-native-file-dialogs\.js\?v=(?!spb-native-file-dialogs-20260903)/.test(html),
  'token: js/spb-native-file-dialogs.js is not on the pre-fix 20260903b token');
check(!/paint-booth-2-state-zones\.js\?v=spb-retire-six-20260905a"><\/script>/.test(html), 'token: paint-booth-2-state-zones.js was bumped past the pre-fix token');

// --- the installer ships electron-app/server: every touched file must be byte-identical there
for (const rel of ['paint-booth-v2.html', 'paint-booth-2-state-zones.js', 'js/spb-native-file-dialogs.js',
  'server_routes/file_picker_routes.py', CSS_REL]) {
  const mirror = path.join(ROOT, 'electron-app', 'server', rel);
  const same = fs.existsSync(mirror) && fs.readFileSync(mirror).equals(fs.readFileSync(path.join(ROOT, rel)));
  check(same, `mirror: electron-app/server/${rel} matches root`);
}

if (failures.length) {
  console.error('\n' + failures.join('\n'));
  console.error(`\n${failures.length} guard check(s) FAILED - the 2026-09-05 beta fixes are not fully wired/shipped.`);
  process.exit(1);
}
console.log('\nOK  guard_beta_polish_20260905: all checks passed');
