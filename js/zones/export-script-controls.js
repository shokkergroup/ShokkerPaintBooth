'use strict';

(function () {
  function install(deps) {
    deps = deps || {};
    const getZones = deps.getZones || function () { return window.zones || []; };
    const showToast = deps.showToast || window.showToast || function () {};

    function downloadText(text, filename, type) {
      const blob = new Blob([text], { type: type || 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }

    window.exportJSON = function exportJSON() {
      const zoneData = getZones().map(z => {
        const entry = { name: z.name, finish: z.finish, intensity: z.intensity };
        const rawMaterialStack = Array.isArray(z.materialStack)
          ? z.materialStack
          : (Array.isArray(z.material_stack) ? z.material_stack : []);
        if (rawMaterialStack.length > 0) {
          entry.materialStack = rawMaterialStack.map(item => item && typeof item === 'object' ? { ...item } : item);
          entry.materialStackMode = z.materialStackMode ?? z.material_stack_mode ?? null;
          entry.materialStackAmount = z.materialStackAmount ?? z.material_stack_amount ?? null;
          entry.materialScale = z.materialScale ?? z.material_scale ?? 1;
        }
        if (z.customSpec != null) entry.custom_intensity = { spec: z.customSpec, paint: z.customPaint, bright: z.customBright };
        if (z.color !== null) entry.color = z.color;
        return entry;
      });
      downloadText(JSON.stringify(zoneData, null, 2), `shokker_zones_${Date.now()}.json`, 'application/json');
      showToast('Zone JSON exported!');
    };

    window.openModal = function openModal() {
      const modal = document.getElementById('scriptModal');
      if (modal) modal.classList.add('active');
      else console.warn('[SPB] scriptModal element not found');
    };

    window.closeModal = function closeModal() {
      const modal = document.getElementById('scriptModal');
      if (modal) modal.classList.remove('active');
    };

    window.copyScript = function copyScript() {
      const el = document.getElementById('scriptOutput');
      if (!el) { showToast('Script output element not found', true); return; }
      const text = el.textContent;
      if (!text) { showToast('No script to copy - generate a script first', true); return; }
      navigator.clipboard.writeText(text).then(() => {
        const fb = document.getElementById('copyFeedback');
        if (fb) {
          fb.classList.add('show');
          setTimeout(() => fb.classList.remove('show'), 2000);
        }
        showToast('Script copied to clipboard');
      }).catch(err => {
        showToast('Copy failed: ' + err.message, true);
      });
    };

    window.saveScriptFile = function saveScriptFile() {
      const scriptEl = document.getElementById('scriptOutput');
      const text = scriptEl ? scriptEl.textContent : '';
      if (!text) { showToast('No script generated yet - click Generate first', true); return; }
      const filenameEl = document.getElementById('scriptFilename');
      let filename = filenameEl ? filenameEl.value.trim() : '';
      if (!filename) filename = 'shokker_multizone.py';
      if (!filename.endsWith('.py')) filename += '.py';
      downloadText(text, filename, 'text/plain');
      showToast(`Saved ${filename}`);
    };

    window.saveBatLauncher = function saveBatLauncher() {
      let pyFilename = (document.getElementById('scriptFilename') || {}).value || '';
      pyFilename = pyFilename.trim();
      if (!pyFilename) pyFilename = 'shokker_multizone.py';
      if (!pyFilename.endsWith('.py')) pyFilename += '.py';

      const driverName = document.getElementById('driverName')?.value.trim() || 'Paint';
      const baseName = pyFilename.replace(/\.py$/, '');
      const batName = `RUN_${baseName}.bat`;
      const batContent = `@echo off\r
REM Auto-unblock .py files in this folder (browser downloads get Zone.Identifier)\r
powershell -ExecutionPolicy Bypass -Command "Get-ChildItem '%~dp0*.py' | Unblock-File" >nul 2>&1\r
\r
echo ============================================================\r
echo   SHOKKER PAINT BOOTH - ${driverName} Build\r
echo ============================================================\r
echo.\r
\r
REM Try the exact script name first\r
if exist "%~dp0${pyFilename}" (\r
    echo   Running: ${pyFilename}\r
    python "%~dp0${pyFilename}"\r
    goto :done\r
)\r
\r
REM Browser renamed the file - use PowerShell to find newest matching .py\r
echo   ${pyFilename} not found, searching for latest version...\r
for /f "usebackq delims=" %%f in (\`powershell -ExecutionPolicy Bypass -Command "Get-ChildItem -Path '%~dp0' -Filter '${baseName}*.py' | Sort-Object LastWriteTime -Descending | Select-Object -First 1 -ExpandProperty Name"\`) do (\r
    echo   Found: %%f\r
    python "%~dp0%%f"\r
    goto :done\r
)\r
\r
REM Last resort: find ANY .py file (newest first, skip RUN_ bat scripts)\r
for /f "usebackq delims=" %%f in (\`powershell -ExecutionPolicy Bypass -Command "Get-ChildItem -Path '%~dp0' -Filter '*.py' | Sort-Object LastWriteTime -Descending | Select-Object -First 1 -ExpandProperty Name"\`) do (\r
    echo   Using newest script found: %%f\r
    python "%~dp0%%f"\r
    goto :done\r
)\r
\r
echo   ERROR: No .py scripts found in this folder!\r
echo   Make sure the .py file is in the same folder as this .bat file.\r
echo   Current folder: %~dp0\r
\r
:done\r
echo.\r
echo ============================================================\r
echo   DONE! Check the output files above.\r
echo ============================================================\r
echo.\r
pause\r\n`;

      downloadText(batContent, batName, 'text/plain');
      showToast(`Saved ${batName} - double-click to run!`);
    };

    window.getAutoScriptName = function getAutoScriptName() {
      const driver = document.getElementById('driverName')?.value.trim() || '';
      const car = document.getElementById('carName')?.value.trim() || '';
      if (driver && car) return `${driver}_${car}.py`.replace(/[<>:"/\\|?*\s]+/g, '_');
      if (driver) return `${driver}.py`.replace(/[<>:"/\\|?*\s]+/g, '_');
      return 'shokker_multizone.py';
    };
  }

  window.SPBZoneExportScriptControls = { install };
})();
