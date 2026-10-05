"""
AFTERSHOCK scaffold - builds C:\\Shokker Paint Booth AFTERSHOCK from the current SPB workspace.

COPIES only what the app needs to RUN and SHIP:
  engine + server + runtime frontend + assets + thumbnails + electron shell + deploy tooling.
SKIPS the accumulated cruft: audits, archives, test corpora, forge/logo/car-intel data dumps,
marketing, build outputs, node_modules, .git.

Read-only against the source. Prints a full manifest.
"""
import os
import shutil
import sys
import time

SRC = r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum"
DST = r"C:\Shokker Paint Booth AFTERSHOCK"

# ---- directories that come over whole -------------------------------------
DIRS = [
    "engine",              # the crown jewels: paint physics + catalog
    "server_routes",
    "scripts",
    "js",
    "css",
    "assets",
    "thumbnails",          # picker swatches
    "image_forge",
    "forge_service",
    "recipes", "palettes", "psd_templates", "text_templates",
    "fonts", "decals", "helmets", "suits", "leagues", "inspiration",
    "tutorials", "wiki-assets",
    "docs",                # keep docs, minus the wiki archive (filtered below)
]

# subpaths inside the above that we do NOT want
DIR_EXCLUDES = {
    os.path.join("docs", "wiki_archive"),
    os.path.join("scripts", "__pycache__"),
}

# ---- root files that come over --------------------------------------------
FILES = [
    # server + engine entry points
    "server.py", "server_v5.py", "config.py", "clean_boot.py", "server_health.py",
    "shokker_engine_v2.py", "requirements.txt",
    # runtime frontend (the CLASSIC UI - kept as the hot-swap fallback)
    "paint-booth-v2.html", "paint-booth-v2.css",
    "paint-booth-0-finish-data.js", "paint-booth-0-finish-tags.js",
    "paint-booth-0-catalog-scorecard.js", "paint-booth-1-core.js", "paint-booth-1-data.js",
    "paint-booth-2-state-zones.js", "paint-booth-3-canvas.js",
    "paint-booth-4-pattern-renderer.js", "paint-booth-5-api-render.js",
    "paint-booth-6-ui-boot.js", "paint-booth-7-shokk.js",
    "paint-booth-layer-flow.js", "paint-booth-flashmap.js",
    "paint-booth-materialmap.js", "paint-booth-specstats.js",
    # secondary app surfaces
    "spec-sculpt.html", "shokk-drop.html", "SPB_WORKBENCH.html", "GETTING_STARTED.html",
    # ship tooling
    "deploy_r2.py", "icon.ico", "START_SERVER.bat",
    # key docs that stay useful
    "CLAUDE.md", "PRIORITIES.md", "CHANGELOG.md", "README.md",
    "WORKSPACE_LOCATION.md", "RELEASE_NOTES_8.0.4.md",
    "VIVA_MEXICO_SPEC_PIPELINE_MASTERCLASS.md",
    ".gitignore", ".gitattributes",
]

# ---- electron shell: copy the app, skip node_modules + dist ---------------
ELECTRON_SKIP = {"node_modules", "dist", "dist-sandbox", "out", "server"}


def human(n):
    for u in ("B", "KB", "MB", "GB"):
        if n < 1024 or u == "GB":
            return f"{n:.1f} {u}"
        n /= 1024


def copy_tree(rel, log):
    s, d = os.path.join(SRC, rel), os.path.join(DST, rel)
    if not os.path.isdir(s):
        log.append(f"  skip (missing): {rel}")
        return 0, 0
    files = bytes_ = 0
    for root, dirs, fs in os.walk(s):
        r = os.path.relpath(root, SRC)
        if any(r == e or r.startswith(e + os.sep) for e in DIR_EXCLUDES):
            dirs[:] = []
            continue
        dirs[:] = [x for x in dirs if x not in ("__pycache__", ".git")]
        td = os.path.join(DST, r)
        os.makedirs(td, exist_ok=True)
        for f in fs:
            if f.endswith((".pyc", ".pyo", ".log")):
                continue
            try:
                sp, dp = os.path.join(root, f), os.path.join(td, f)
                shutil.copy2(sp, dp)
                files += 1
                bytes_ += os.path.getsize(dp)
            except OSError:
                pass
    log.append(f"  {rel:24s} {files:7d} files  {human(bytes_)}")
    return files, bytes_


def main():
    t0 = time.time()
    os.makedirs(DST, exist_ok=True)
    log = ["AFTERSHOCK scaffold", f"source: {SRC}", f"dest:   {DST}", "", "DIRECTORIES:"]
    tf = tb = 0

    for rel in DIRS:
        f, b = copy_tree(rel, log)
        tf += f
        tb += b

    # electron shell (filtered)
    log.append("")
    log.append("ELECTRON SHELL (no node_modules/dist):")
    ea_s = os.path.join(SRC, "electron-app")
    ef = eb = 0
    for root, dirs, fs in os.walk(ea_s):
        dirs[:] = [d for d in dirs if d not in ELECTRON_SKIP and d != "__pycache__"]
        r = os.path.relpath(root, SRC)
        td = os.path.join(DST, r)
        os.makedirs(td, exist_ok=True)
        for f in fs:
            try:
                shutil.copy2(os.path.join(root, f), os.path.join(td, f))
                ef += 1
                eb += os.path.getsize(os.path.join(td, f))
            except OSError:
                pass
    log.append(f"  electron-app             {ef:7d} files  {human(eb)}")
    tf += ef
    tb += eb

    log.append("")
    log.append("ROOT FILES:")
    rf = rb = 0
    for f in FILES:
        s = os.path.join(SRC, f)
        if not os.path.isfile(s):
            log.append(f"  skip (missing): {f}")
            continue
        try:
            shutil.copy2(s, os.path.join(DST, f))
            rf += 1
            rb += os.path.getsize(s)
        except OSError as e:
            log.append(f"  FAILED {f}: {e}")
    log.append(f"  {rf} root files  {human(rb)}")
    tf += rf
    tb += rb

    log.append("")
    log.append(f"TOTAL: {tf} files, {human(tb)}, in {time.time()-t0:.0f}s")
    log.append("")
    log.append("DELIBERATELY NOT COPIED (cruft//regenerable/huge):")
    for x in ["_archive", "_audit", "output", "tests", "_forge_*", "_dev_asset_masters",
              "_car_intel", "_logo_data", "_logo_bench", "marketing", "basespatterns_examples",
              "SPB_AUDIT_*.html", "docs/wiki_archive", ".git", "node_modules",
              "electron-app/dist", "*.log", "__pycache__"]:
        log.append(f"  - {x}")

    text = "\n".join(log)
    with open(os.path.join(DST, "_SCAFFOLD_MANIFEST.txt"), "w", encoding="utf-8") as fh:
        fh.write(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
