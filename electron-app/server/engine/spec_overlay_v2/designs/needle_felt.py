# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 98.8; invariant nearest 0.5011 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Needle Felt. Identity declared before rendering/scoring."""
from ..weave_designs import needle_felt
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_needle_felt',
 'display_name': 'Needle Felt - spec overlay',
 'promise': 'Needle Felt assembles compressed fiber pads, tangled fibers, needle punctures, fiber loops '
            'and raised nap.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of weave surface processes; the authored '
                                    'masks and material tiers are an artistic construction, not a '
                                    'measured physical simulation.',
                       'sources': ['https://www.toraycma.com/wp-content/uploads/3900-Prepreg-System.pdf']},
 'carrier_grammar': 'Needle Felt assembles compressed fiber pads, tangled fibers, needle punctures, '
                    'fiber loops and raised nap. Geometry is independently authored in '
                    'weave_designs.py:needle_felt.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to compressed fiber pads, '
                 'tangled fibers, needle punctures, fiber loops, raised nap.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'compressed_fiber_pads',
                 'role': 'Compressed fiber pads use M/R/Cc intervals [(4, 144), (88, 220), (44, 220)] '
                         'in their own geometry.'},
                {'name': 'tangled_fibers',
                 'role': 'Tangled fibers use M/R/Cc intervals [(138, 255), (22, 140), (24, 244)] in '
                         'their own geometry.'},
                {'name': 'needle_punctures',
                 'role': 'Needle punctures use M/R/Cc intervals [(0, 64), (188, 255), (170, 255)] in '
                         'their own geometry.'},
                {'name': 'fiber_loops',
                 'role': 'Fiber loops use M/R/Cc intervals [(54, 224), (44, 196), (0, 108)] in their '
                         'own geometry.'},
                {'name': 'raised_nap',
                 'role': 'Raised nap use M/R/Cc intervals [(164, 254), (120, 250), (130, 250)] in their '
                         'own geometry.'}],
 'material_binding': {'M': ['compressed_fiber_pads',
                            'tangled_fibers',
                            'needle_punctures',
                            'fiber_loops',
                            'raised_nap'],
                      'R': ['compressed_fiber_pads',
                            'tangled_fibers',
                            'needle_punctures',
                            'fiber_loops',
                            'raised_nap'],
                      'Cc': ['compressed_fiber_pads',
                             'tangled_fibers',
                             'needle_punctures',
                             'fiber_loops',
                             'raised_nap']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_braided_junction',
                        'difference': 'Needle Felt must visibly separate through compressed fiber pads, '
                                      'tangled fibers, needle punctures and the remaining named marks, '
                                      'not color or parameter changes.'},
                       {'finish_id': 'spov2_triaxial_basket',
                        'difference': 'Needle Felt must visibly separate through compressed fiber pads, '
                                      'tangled fibers, needle punctures and the remaining named marks, '
                                      'not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Unequal angled fiber fragments form a dense felt packing.',
                                     'compressed fiber pads is present in the native named-feature '
                                     'coverage probe.',
                                     'tangled fibers is present in the native named-feature coverage '
                                     'probe.',
                                     'needle punctures is present in the native named-feature coverage '
                                     'probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/needle_felt/independent-feature-carrier',
 'spec_key': 'spec-v2/needle_felt/named-material-bindings'}

render = build_renderer(needle_felt, IDENTITY_CONTRACT)
