# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 94.05; invariant nearest 0.47335 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Feather Barbules. Identity declared before rendering/scoring."""
from ..skin_designs import feather_barbules
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_feather_barbules',
 'display_name': 'Feather Barbules - spec overlay',
 'promise': 'Feather Barbules assembles barb shafts, hooked barbules, interlocking slots, barbule hook '
            'heads and abraded shaft nodes.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of skin surface processes; the authored '
                                    'masks and material tiers are an artistic construction, not a '
                                    'measured physical simulation.',
                       'sources': ['https://pmc.ncbi.nlm.nih.gov/articles/PMC6631580/']},
 'carrier_grammar': 'Feather Barbules assembles barb shafts, hooked barbules, interlocking slots, '
                    'barbule hook heads and abraded shaft nodes. Geometry is independently authored in '
                    'skin_designs.py:feather_barbules.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to barb shafts, hooked '
                 'barbules, interlocking slots, barbule hook heads, abraded shaft nodes.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'barb_shafts',
                 'role': 'Barb shafts use M/R/Cc intervals [(72, 246), (0, 246), (24, 240)] in their '
                         'own geometry.'},
                {'name': 'hooked_barbules',
                 'role': 'Hooked barbules use M/R/Cc intervals [(148, 255), (0, 110), (0, 114)] in '
                         'their own geometry.'},
                {'name': 'interlocking_slots',
                 'role': 'Interlocking slots use M/R/Cc intervals [(0, 104), (172, 255), (144, 254)] in '
                         'their own geometry.'},
                {'name': 'barbule_hook_heads',
                 'role': 'Barbule hook heads use M/R/Cc intervals [(44, 194), (90, 218), (64, 226)] in '
                         'their own geometry.'},
                {'name': 'abraded_shaft_nodes',
                 'role': 'Abraded shaft nodes use M/R/Cc intervals [(14, 158), (132, 238), (164, 252)] '
                         'in their own geometry.'}],
 'material_binding': {'M': ['barb_shafts',
                            'hooked_barbules',
                            'interlocking_slots',
                            'barbule_hook_heads',
                            'abraded_shaft_nodes'],
                      'R': ['barb_shafts',
                            'hooked_barbules',
                            'interlocking_slots',
                            'barbule_hook_heads',
                            'abraded_shaft_nodes'],
                      'Cc': ['barb_shafts',
                             'hooked_barbules',
                             'interlocking_slots',
                             'barbule_hook_heads',
                             'abraded_shaft_nodes']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_denticle_armor',
                        'difference': 'Feather Barbules must visibly separate through barb shafts, '
                                      'hooked barbules, interlocking slots and the remaining named '
                                      'marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_diatom_sieve',
                        'difference': 'Feather Barbules must visibly separate through barb shafts, '
                                      'hooked barbules, interlocking slots and the remaining named '
                                      'marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Hooked barbules branch from curving feather shafts.',
                                     'barb shafts is present in the native named-feature coverage '
                                     'probe.',
                                     'hooked barbules is present in the native named-feature coverage '
                                     'probe.',
                                     'interlocking slots is present in the native named-feature '
                                     'coverage probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/feather_barbules/independent-feature-carrier',
 'spec_key': 'spec-v2/feather_barbules/named-material-bindings'}

render = build_renderer(feather_barbules, IDENTITY_CONTRACT)
