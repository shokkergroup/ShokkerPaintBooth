# SPB-105 ERA120 tick2: owner "DO what they say"; metric movement in docs/finish_audits/era120_2026-09-17/LIVE_REPORT.md.
from . import contract, make_paint, make_spec
IDENTITY_CONTRACT = contract('cbp_kanji_signage')
paint_fn = make_paint('cbp_kanji_signage')
spec_fn = make_spec('cbp_kanji_signage')
paint_fn.__module__ = __name__
spec_fn.__module__ = __name__
