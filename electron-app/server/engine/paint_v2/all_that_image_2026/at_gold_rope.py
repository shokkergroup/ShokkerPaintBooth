# SPB-105 AT-R2: owner local review; metric movement in R2_LIVE_REPORT.md.
from . import contract, make_paint, make_spec
IDENTITY_CONTRACT = contract('at_gold_rope')
paint_fn = make_paint('at_gold_rope')
spec_fn = make_spec('at_gold_rope')
paint_fn.__module__ = __name__
spec_fn.__module__ = __name__
