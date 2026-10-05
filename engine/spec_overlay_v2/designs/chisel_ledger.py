# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 98.52; invariant nearest 0.50231 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Chisel Ledger. Identity declared before rendering/scoring."""
from ..machine_designs import chisel_ledger
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_chisel_ledger',
 'display_name': 'Chisel Ledger - spec overlay',
 'promise': 'Chisel Ledger assembles chisel facets, strike heads, lifted shavings, tail splits and '
            'corner gouges.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of machine surface processes; the '
                                    'authored masks and material tiers are an artistic construction, '
                                    'not a measured physical simulation.',
                       'sources': ['https://videos.sandvik.coromant.com/machining-guide-step-7-specify']},
 'carrier_grammar': 'Chisel Ledger assembles chisel facets, strike heads, lifted shavings, tail splits '
                    'and corner gouges. Geometry is independently authored in '
                    'machine_designs.py:chisel_ledger.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to chisel facets, strike heads, '
                 'lifted shavings, tail splits, corner gouges.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'chisel_facets',
                 'role': 'Chisel facets use M/R/Cc intervals [(12, 252), (0, 246), (24, 246)] in their '
                         'own geometry.'},
                {'name': 'strike_heads',
                 'role': 'Strike heads use M/R/Cc intervals [(160, 254), (0, 64), (0, 142)] in their '
                         'own geometry.'},
                {'name': 'lifted_shavings',
                 'role': 'Lifted shavings use M/R/Cc intervals [(44, 202), (52, 166), (130, 255)] in '
                         'their own geometry.'},
                {'name': 'tail_splits',
                 'role': 'Tail splits use M/R/Cc intervals [(6, 94), (160, 248), (118, 238)] in their '
                         'own geometry.'},
                {'name': 'corner_gouges',
                 'role': 'Corner gouges use M/R/Cc intervals [(20, 142), (100, 218), (22, 124)] in '
                         'their own geometry.'}],
 'material_binding': {'M': ['chisel_facets',
                            'strike_heads',
                            'lifted_shavings',
                            'tail_splits',
                            'corner_gouges'],
                      'R': ['chisel_facets',
                            'strike_heads',
                            'lifted_shavings',
                            'tail_splits',
                            'corner_gouges'],
                      'Cc': ['chisel_facets',
                             'strike_heads',
                             'lifted_shavings',
                             'tail_splits',
                             'corner_gouges']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_toolpath_reversal',
                        'difference': 'Chisel Ledger must visibly separate through chisel facets, '
                                      'strike heads, lifted shavings and the remaining named marks, not '
                                      'color or parameter changes.'},
                       {'finish_id': 'spov2_weld_pool_archive',
                        'difference': 'Chisel Ledger must visibly separate through chisel facets, '
                                      'strike heads, lifted shavings and the remaining named marks, not '
                                      'color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Three offset chisel strikes show separate head edges and broken '
                                     'tails.',
                                     'chisel facets is present in the native named-feature coverage '
                                     'probe.',
                                     'strike heads is present in the native named-feature coverage '
                                     'probe.',
                                     'lifted shavings is present in the native named-feature coverage '
                                     'probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/chisel_ledger/independent-feature-carrier',
 'spec_key': 'spec-v2/chisel_ledger/named-material-bindings'}

render = build_renderer(chisel_ledger, IDENTITY_CONTRACT)
