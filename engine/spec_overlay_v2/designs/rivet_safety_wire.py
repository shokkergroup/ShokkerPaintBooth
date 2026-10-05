# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 96.4; invariant nearest 0.51805 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Rivet Safety Wire. Identity declared before rendering/scoring."""
from ..track_designs import rivet_safety_wire
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_rivet_safety_wire',
 'display_name': 'Rivet Safety Wire - spec overlay',
 'promise': 'Rivet Safety Wire assembles rivet head discs, twisted safety wires, drilled lock holes, '
            'rivet annular lips and folded wire tails.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of track surface processes; the authored '
                                    'masks and material tiers are an artistic construction, not a '
                                    'measured physical simulation.',
                       'sources': ['https://support.iracing.com/support/solutions/articles/31000153524-paint-textures']},
 'carrier_grammar': 'Rivet Safety Wire assembles rivet head discs, twisted safety wires, drilled lock '
                    'holes, rivet annular lips and folded wire tails. Geometry is independently '
                    'authored in track_designs.py:rivet_safety_wire.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to rivet head discs, twisted '
                 'safety wires, drilled lock holes, rivet annular lips, folded wire tails.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'rivet_head_discs',
                 'role': 'Rivet head discs use M/R/Cc intervals [(18, 246), (24, 214), (24, 248)] in '
                         'their own geometry.'},
                {'name': 'twisted_safety_wires',
                 'role': 'Twisted safety wires use M/R/Cc intervals [(146, 255), (16, 108), (0, 114)] '
                         'in their own geometry.'},
                {'name': 'drilled_lock_holes',
                 'role': 'Drilled lock holes use M/R/Cc intervals [(0, 98), (180, 255), (146, 254)] in '
                         'their own geometry.'},
                {'name': 'rivet_annular_lips',
                 'role': 'Rivet annular lips use M/R/Cc intervals [(56, 204), (102, 232), (68, 204)] in '
                         'their own geometry.'},
                {'name': 'folded_wire_tails',
                 'role': 'Folded wire tails use M/R/Cc intervals [(98, 228), (54, 180), (164, 255)] in '
                         'their own geometry.'}],
 'material_binding': {'M': ['rivet_head_discs',
                            'twisted_safety_wires',
                            'drilled_lock_holes',
                            'rivet_annular_lips',
                            'folded_wire_tails'],
                      'R': ['rivet_head_discs',
                            'twisted_safety_wires',
                            'drilled_lock_holes',
                            'rivet_annular_lips',
                            'folded_wire_tails'],
                      'Cc': ['rivet_head_discs',
                             'twisted_safety_wires',
                             'drilled_lock_holes',
                             'rivet_annular_lips',
                             'folded_wire_tails']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_pit_lane_ghost',
                        'difference': 'Rivet Safety Wire must visibly separate through rivet head '
                                      'discs, twisted safety wires, drilled lock holes and the '
                                      'remaining named marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_tire_sipes',
                        'difference': 'Rivet Safety Wire must visibly separate through rivet head '
                                      'discs, twisted safety wires, drilled lock holes and the '
                                      'remaining named marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Small fastener heads connect through bent safety-wire segments.',
                                     'rivet head discs is present in the native named-feature coverage '
                                     'probe.',
                                     'twisted safety wires is present in the native named-feature '
                                     'coverage probe.',
                                     'drilled lock holes is present in the native named-feature '
                                     'coverage probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/rivet_safety_wire/independent-feature-carrier',
 'spec_key': 'spec-v2/rivet_safety_wire/named-material-bindings'}

render = build_renderer(rivet_safety_wire, IDENTITY_CONTRACT)
