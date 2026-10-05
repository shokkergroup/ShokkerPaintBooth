# SPB-105 ERA120 tick4: owner "build procedurally"; served M7 81.4 -> 86.6; paired geometry/provenance in authoring/ and PROCEDURAL_IMPLEMENTATION.md.
# SPB-105 ERA120 tick2: owner "DO what they say"; metric movement in docs/finish_audits/era120_2026-09-17/LIVE_REPORT.md.
from . import contract, make_paint, make_spec
IDENTITY_CONTRACT = contract('rad_attract_mode')
paint_fn = make_paint('rad_attract_mode')
spec_fn = make_spec('rad_attract_mode')
paint_fn.__module__ = __name__
spec_fn.__module__ = __name__
