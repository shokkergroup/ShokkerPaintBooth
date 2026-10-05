# SPB-105 AT-R2: owner local review; metric movement in R2_LIVE_REPORT.md.
from . import contract, make_paint, make_spec
IDENTITY_CONTRACT = contract('at_chipped_nail')
paint_fn = make_paint('at_chipped_nail')
spec_fn = make_spec('at_chipped_nail')
paint_fn.__module__ = __name__
spec_fn.__module__ = __name__
