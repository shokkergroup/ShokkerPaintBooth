# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 96.83; invariant nearest 0.43846 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Leno Lock. Identity declared before rendering/scoring."""
from ..weave_designs import leno_lock
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_leno_lock',
 'display_name': 'Leno Lock - spec overlay',
 'promise': 'Leno Lock assembles countertwisted warp pairs, locking weft passes, underpass resin slots, '
            'twist contact shoulders and short loose filaments.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of weave surface processes; the authored '
                                    'masks and material tiers are an artistic construction, not a '
                                    'measured physical simulation.',
                       'sources': ['https://www.toraycma.com/wp-content/uploads/3900-Prepreg-System.pdf']},
 'carrier_grammar': 'Leno Lock assembles countertwisted warp pairs, locking weft passes, underpass '
                    'resin slots, twist contact shoulders and short loose filaments. Geometry is '
                    'independently authored in weave_designs.py:leno_lock.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to countertwisted warp pairs, '
                 'locking weft passes, underpass resin slots, twist contact shoulders, short loose '
                 'filaments.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'countertwisted_warp_pairs',
                 'role': 'Countertwisted warp pairs use M/R/Cc intervals [(16, 242), (28, 224), (24, '
                         '250)] in their own geometry.'},
                {'name': 'locking_weft_passes',
                 'role': 'Locking weft passes use M/R/Cc intervals [(148, 255), (16, 108), (0, 116)] in '
                         'their own geometry.'},
                {'name': 'underpass_resin_slots',
                 'role': 'Underpass resin slots use M/R/Cc intervals [(0, 102), (180, 255), (146, 254)] '
                         'in their own geometry.'},
                {'name': 'twist_contact_shoulders',
                 'role': 'Twist contact shoulders use M/R/Cc intervals [(56, 208), (104, 232), (68, '
                         '214)] in their own geometry.'},
                {'name': 'short_loose_filaments',
                 'role': 'Short loose filaments use M/R/Cc intervals [(96, 226), (54, 184), (164, 255)] '
                         'in their own geometry.'}],
 'material_binding': {'M': ['countertwisted_warp_pairs',
                            'locking_weft_passes',
                            'underpass_resin_slots',
                            'twist_contact_shoulders',
                            'short_loose_filaments'],
                      'R': ['countertwisted_warp_pairs',
                            'locking_weft_passes',
                            'underpass_resin_slots',
                            'twist_contact_shoulders',
                            'short_loose_filaments'],
                      'Cc': ['countertwisted_warp_pairs',
                             'locking_weft_passes',
                             'underpass_resin_slots',
                             'twist_contact_shoulders',
                             'short_loose_filaments']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_braided_junction',
                        'difference': 'Leno Lock must visibly separate through countertwisted warp '
                                      'pairs, locking weft passes, underpass resin slots and the '
                                      'remaining named marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_triaxial_basket',
                        'difference': 'Leno Lock must visibly separate through countertwisted warp '
                                      'pairs, locking weft passes, underpass resin slots and the '
                                      'remaining named marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Continuous opposing warp curves lock a separate weft.',
                                     'countertwisted warp pairs is present in the native named-feature '
                                     'coverage probe.',
                                     'locking weft passes is present in the native named-feature '
                                     'coverage probe.',
                                     'underpass resin slots is present in the native named-feature '
                                     'coverage probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/leno_lock/independent-feature-carrier',
 'spec_key': 'spec-v2/leno_lock/named-material-bindings'}

render = build_renderer(leno_lock, IDENTITY_CONTRACT)
