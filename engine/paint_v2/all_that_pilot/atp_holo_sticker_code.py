"""SPB-105 / AT-P1: owner requires unique name-true finishes.
M7: N/A baseline to diagnostic evidence in _all_that_pilot_work/m7_report.json.
Review candidate, not a shipped replacement.
"""
from . import contract, paint_fn, spec_fn
IDENTITY_CONTRACT = contract('atp_holo_sticker_code')
paint = paint_fn('atp_holo_sticker_code')
spec = spec_fn('atp_holo_sticker_code')
