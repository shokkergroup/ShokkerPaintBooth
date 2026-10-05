"""The v2 overlay catalog: explicit modules, metadata and stable IDs."""
from pathlib import Path
import importlib,json
ROOT=Path(__file__).resolve().parent
def definitions():return json.loads((ROOT/'catalog.json').read_text(encoding='utf-8'))
def build_catalog():
    return {row['id']:importlib.import_module('engine.spec_overlay_v2.designs.'+row['id'][6:]).render for row in definitions()['items']}
