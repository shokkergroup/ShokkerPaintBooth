"""After the build: the kits spb_release.ps1 -Phase build would have made, plus the packaged-copy checks.

    python scripts/release/spb_make_kits.py --version 10.0.3 [--check-only]

- copies the stub to _sandbox_share/ and _payhip_<version>/ (README templated from the previous _payhip_* if missing)
- zips _payhip_<version>/ -> ShokkerPaintBooth-<version>-Payhip.zip
- writes SPB_<version>_sandbox.wsb (24 GB RAM + vGPU: the engine MemoryErrors on the Sandbox default)
- packaged-copy checks: version strings, no thumbnails/audit, package.json has no "compression": "store"
"""
import argparse, glob, os, re, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
ap = argparse.ArgumentParser(); ap.add_argument("--version", required=True); ap.add_argument("--check-only", action="store_true"); a = ap.parse_args()
VER = a.version
fails = []


def check(ok, msg):
    print(("PASS  " if ok else "FAIL  ") + msg)
    if not ok:
        fails.append(msg)


# ---- packaged-copy checks
P = "electron-app/dist/win-unpacked/resources/server"
cfg = open(f"{P}/config.py", encoding="utf-8", errors="ignore").read() if os.path.isfile(f"{P}/config.py") else ""
check(f'VERSION: str = "{VER}' in cfg, f"packaged config.py reports {VER}")
api = open(f"{P}/paint-booth-5-api-render.js", encoding="utf-8", errors="ignore").read() if os.path.isfile(f"{P}/paint-booth-5-api-render.js") else ""
check(f"CLIENT_VERSION = '{VER}" in api, f"packaged CLIENT_VERSION reports {VER}")
check(not os.path.isdir(f"{P}/thumbnails/audit"), "thumbnails/audit is NOT packaged")
pkg = open("electron-app/package.json", encoding="utf-8").read()
check('"compression"' not in pkg, 'electron-app/package.json has no "compression" key (default LZMA)')
html_root = open("paint-booth-v2.html", encoding="utf-8", errors="ignore").read()
html_pkg = open(f"{P}/paint-booth-v2.html", encoding="utf-8", errors="ignore").read() if os.path.isfile(f"{P}/paint-booth-v2.html") else ""
check(html_root == html_pkg, "packaged paint-booth-v2.html == root")
html_live = re.sub(r"<!--.*?-->", "", html_root, flags=re.S)  # commented-out tags are not loaded
missing = [m for m in set(re.findall(r'(?:src|href)="((?:js|css)/[^"?]+)', html_live)) if not os.path.isfile(f"{P}/{m}")]
check(not missing, f"every js/css referenced by the HTML is packaged ({len(missing)} missing: {missing[:5]})")
stubs = [p for p in glob.glob("electron-app/dist/nsis-web/*Web-Setup.exe") if VER in p]
pays = [p for p in glob.glob("electron-app/dist/nsis-web/*.nsis.7z") if VER in p]
check(len(stubs) == 1 and len(pays) == 1, f"exactly one {VER} stub and payload in dist/nsis-web")
if pays:
    gb = os.path.getsize(pays[0]) / 1e9
    check(gb >= 3.5, f"payload {gb:.2f} GB (10.0.1 shipped at 4.11 GB; below 3.5 means finish packs are missing)")
if a.check_only or fails:
    sys.exit(1 if fails else 0)

# ---- kits
stub = stubs[0]
os.makedirs("_sandbox_share", exist_ok=True); shutil.copy2(stub, "_sandbox_share/")
pay_dir = f"_payhip_{VER}"; os.makedirs(pay_dir, exist_ok=True); shutil.copy2(stub, pay_dir)
readme = os.path.join(pay_dir, "READ ME FIRST.txt")
if not os.path.isfile(readme):
    prev = sorted([d for d in glob.glob("_payhip_*") if d != pay_dir and os.path.isfile(os.path.join(d, "READ ME FIRST.txt"))])
    if prev:
        old = open(os.path.join(prev[-1], "READ ME FIRST.txt"), encoding="utf-8").read()
        open(readme, "w", encoding="utf-8").write(re.sub(r"\d+\.\d+\.\d+", VER, old)); print(f"README templated from {prev[-1]} - REVIEW the WHAT'S NEW section")
    else:
        print("no previous README to template - write one before uploading")
zip_out = f"ShokkerPaintBooth-{VER}-Payhip.zip"
if os.path.exists(zip_out):
    os.remove(zip_out)
subprocess.run(["powershell", "-NoProfile", "-Command", f"Compress-Archive -Path '{os.path.abspath(pay_dir)}\\*' -DestinationPath '{os.path.abspath(zip_out)}' -Force"], check=True)
share = os.path.abspath("_sandbox_share"); desk = f"C:\\Users\\WDAGUtilityAccount\\Desktop\\SPB-{VER}-Installer"
open(f"SPB_{VER}_sandbox.wsb", "w", encoding="utf-8").write(
    "<Configuration>\n  <vGpu>Enable</vGpu>\n  <Networking>Enable</Networking>\n  <MemoryInMB>24576</MemoryInMB>\n  <MappedFolders>\n    <MappedFolder>\n"
    f"      <HostFolder>{share}</HostFolder>\n      <SandboxFolder>{desk}</SandboxFolder>\n      <ReadOnly>true</ReadOnly>\n    </MappedFolder>\n  </MappedFolders>\n"
    f"  <LogonCommand>\n    <Command>explorer.exe {desk}</Command>\n  </LogonCommand>\n</Configuration>\n")
print(f"kits: _sandbox_share/{os.path.basename(stub)}, {pay_dir}/, {zip_out}, SPB_{VER}_sandbox.wsb")
