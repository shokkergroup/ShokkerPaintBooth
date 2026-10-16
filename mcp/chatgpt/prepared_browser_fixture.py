"""Import shim for the private prepared-browser read fixture."""
import importlib.util
from pathlib import Path
_path=Path(__file__).resolve().parent/'prepared-browser/read_fixture.py'
_spec=importlib.util.spec_from_file_location('spb_prepared_read_fixture',_path)
_module=importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
spec=_module.spec
