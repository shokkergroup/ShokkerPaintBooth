"""Run the MAIN tree's spb_golden_net --check with (optionally) HEAD versions of dirty engine
files swapped in via an import hook; diffs + last_check go to scratch, nothing in the repo is written."""
import sys, os, importlib.util, importlib.machinery
MAIN = r"C:/DRIVE E BACKUP/Shokker Paint Booth Gold to Platinum"
SCR = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1]
USE_HEAD = os.environ.get("GN_HEAD", "1") == "1"
OVER = {"engine.compose": "compose.py", "shokker_engine_v2": "shokker_engine_v2.py",
        "engine.paint_v2.flames_2026": "flames_2026.py"}
class Hook:
    def find_spec(self, name, path=None, target=None):
        if USE_HEAD and name in OVER:
            src = os.path.join(SCR, "overlay", OVER[name])
            real = os.path.join(MAIN, *name.split(".")) + ".py"
            class L(importlib.machinery.SourceFileLoader):
                def get_data(self, path):
                    if os.path.normcase(os.path.abspath(path)) == os.path.normcase(os.path.abspath(real)):
                        return open(src, "rb").read()
                    if path.endswith(".pyc"):
                        raise OSError("no pyc for overlay")
                    return super().get_data(path)
                def path_stats(self, path):
                    raise OSError("force source")
            return importlib.util.spec_from_file_location(name, real, loader=L(name, real))
        return None
sys.meta_path.insert(0, Hook())
sys.path.insert(0, MAIN)
spec = importlib.util.spec_from_file_location("gn", os.path.join(MAIN, "scripts", "spb_golden_net.py"))
gn = importlib.util.module_from_spec(spec); spec.loader.exec_module(gn)
gn.OUT_DIR = OUT; gn.DIFF_DIR = os.path.join(OUT, "diff"); os.makedirs(gn.DIFF_DIR, exist_ok=True)
orig_write = gn._atomic_write_json
def guarded(path, obj):
    assert os.path.abspath(path).startswith(os.path.abspath(OUT)), "refusing repo write: " + path
    return orig_write(path, obj)
gn._atomic_write_json = guarded
rc = gn.main(["--check"] + sys.argv[2:])
import shokker_engine_v2 as e, engine.compose as c
print("HOOK-VERIFY loader:", type(e.__loader__).__name__, type(c.__loader__).__name__, "| _zone_bbox_enabled present (dirty marker):", hasattr(e, "_zone_bbox_enabled"))
sys.exit(rc)
