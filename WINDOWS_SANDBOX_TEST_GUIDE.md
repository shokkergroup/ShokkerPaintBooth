# Windows Sandbox Test Guide — Shokker Paint Booth

**Audience:** Internal QA, alpha testers, and developers who need a disposable, known-clean Windows environment to validate SPB builds before they leave the lab.

**Why Sandbox?** Windows Sandbox gives you a lightweight, throwaway Windows 10/11 VM in about 15 seconds. Every time you close it, state resets. That means each SPB install starts from a pristine machine with no leftover Python, no stale cache, no installer residue — exactly what a brand-new customer sees on their first launch. If SPB runs clean in Sandbox, it will almost certainly run clean on a customer's real PC.

---

## 1. Prerequisites

Before you can use this guide you need:

| Requirement | Notes |
|-------------|-------|
| Windows 10 Pro/Enterprise or Windows 11 Pro/Enterprise | Home editions **do not** ship with Sandbox. |
| Virtualization enabled in BIOS | Intel VT-x or AMD-V. |
| 4 GB free RAM (8 GB recommended) | SPB + Electron + Python will eat ~1.5 GB on load. |
| 1 GB free disk | Installer + render cache. |
| Windows Sandbox feature installed | `Control Panel -> Turn Windows features on or off -> Windows Sandbox`. Reboot after install. |

> **Tip:** If Sandbox won't start with an error about virtualization, open Task Manager -> Performance -> CPU and confirm "Virtualization: Enabled". If it's disabled, enable it in BIOS.

---

## 2. The `.wsb` File

We ship a configuration file named `spb-sandbox.wsb` in the repo root (or under `scripts/sandbox/` depending on build). A `.wsb` file is just XML that tells Windows Sandbox what folders to map, how much RAM to grant, and what to auto-run.

Example skeleton (do not edit without consulting Release Process):

```xml
<Configuration>
  <VGpu>Enable</VGpu>
  <MappedFolders>
    <MappedFolder>
      <HostFolder>C:\SPB-Installers</HostFolder>
      <SandboxFolder>C:\Installers</SandboxFolder>
      <ReadOnly>true</ReadOnly>
    </MappedFolder>
  </MappedFolders>
  <LogonCommand>
    <Command>C:\Installers\ShokkerPaintBooth-Setup.exe /S</Command>
  </LogonCommand>
  <MemoryInMB>8192</MemoryInMB>
</Configuration>
```

**What each block does:**

- `VGpu Enable` — forwards the host GPU. Required for SPB's GPU pipeline to behave anywhere near realistically.
- `MappedFolders` — read-only link so the sandbox can see the installer on the host without copying.
- `LogonCommand` — auto-runs the installer once the sandbox boots. `/S` is a silent install flag if the installer supports it; remove it to see the UI.
- `MemoryInMB` — give it at least 6 GB for comfortable testing.

---

## 3. Step-By-Step Test Run

### 3.1 Prepare the host

1. Drop the latest SPB installer (e.g. `ShokkerPaintBooth-6.2.0-alpha-Setup.exe`) into `C:\SPB-Installers\` on the **host** machine.
2. Double-click `spb-sandbox.wsb`. Sandbox boots in ~15 seconds.

### 3.2 Inside the sandbox

Once the sandbox loads:

1. If you used `LogonCommand`, wait for the installer to finish. A Start Menu shortcut will appear.
2. Launch SPB from the Start Menu.
3. Confirm the splash shows `6.2.0-alpha (Boil the Ocean)`.
4. Run through the **smoke checklist** below.

### 3.3 Smoke Checklist

- [ ] App window opens without a Python traceback in the console
- [ ] Default car model loads within 5 seconds
- [ ] Paint a zone with `Gloss Black` -> confirm render preview appears
- [ ] Apply `Chrome (Spec)` -> mirror finish visible
- [ ] Swap to a pattern finish (e.g. `Carbon Fiber`) -> pattern tiles correctly, no magenta fallback
- [ ] Save a Shokk -> file lands in the default Shokks folder
- [ ] Load the saved Shokk -> round-trips without zone-count or color drift
- [ ] Close + relaunch -> last session restores
- [ ] Close the sandbox -> nothing prompts for save/confirmation on the host

### 3.4 Capture results

Because Sandbox discards everything on close, copy logs out **before** you shut it down:

1. Drag `%APPDATA%\ShokkerPaintBooth\logs\` back to the mapped folder (make the mapped folder writable temporarily, or set up a second mapped writable folder for logs).
2. Note the build hash, commit, and any failures in the QA tracker.

---

## 4. Common Gotchas

| Symptom | Cause | Fix |
|---------|-------|-----|
| Black render window | `VGpu` not enabled in `.wsb` | Re-check XML, restart sandbox. |
| Installer says "Windows protected your PC" | SmartScreen — installer isn't signed in alpha | Click `More info -> Run anyway`. Note in the QA log. |
| App starts, UI blank | Chromium cache collision from host (shouldn't happen in Sandbox) | Close, reboot sandbox. If it recurs, file a bug with steps. |
| "Python not found" error | Installer failed to bundle `pyserver/_internal` | Build broken — reject release, notify Release Captain. |

---

## 5. Resetting State

Sandbox resets automatically on close. You do **not** need to uninstall. If you want a warm run (same session, fresh SPB state), close SPB, delete `%APPDATA%\ShokkerPaintBooth\` inside the sandbox, and relaunch.

---

## 6. When Not To Use Sandbox

Sandbox is great for clean-install and smoke tests but not a substitute for:

- **Real hardware GPU tests** — iGPU behavior is virtualized and sometimes off from bare metal.
- **Installer upgrade paths** — use a persistent VM or real machine with an older SPB build already installed.
- **Licensing / activation flows** — these touch hardware IDs; Sandbox reissues IDs each boot.

For those cases, use a Hyper-V checkpoint-backed VM or a dedicated QA laptop.

---

## 7. Reporting Issues

If anything in the smoke checklist fails, file the bug in the `#spb-qa` Discord channel with:

1. Build version (from the splash or `VERSION.txt`)
2. Step that failed
3. Screenshot + log files (from `%APPDATA%\ShokkerPaintBooth\logs\`)
4. Whether `VGpu` was enabled
5. Host Windows version

Alpha testers should additionally tag `@spb-dev` for the release captain on duty.

---

*Last updated for SPB 6.2.0-alpha. Update this doc when the installer filename, folder layout, or `.wsb` config changes.*
