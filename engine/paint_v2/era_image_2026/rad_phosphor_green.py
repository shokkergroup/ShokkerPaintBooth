# SPB-105 ERA120 tick2: owner "DO what they say"; metric movement in docs/finish_audits/era120_2026-09-17/LIVE_REPORT.md.
from . import contract, make_paint, make_spec
IDENTITY_CONTRACT = contract('rad_phosphor_green')
paint_fn = make_paint('rad_phosphor_green')
spec_fn = make_spec('rad_phosphor_green')
paint_fn.__module__ = __name__
spec_fn.__module__ = __name__
