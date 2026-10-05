# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 98.51; invariant nearest 0.42888 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Corrosion Blisters. Identity declared before rendering/scoring."""
from ..crack_designs import corrosion_blisters
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_corrosion_blisters',
 'display_name': 'Corrosion Blisters - spec overlay',
 'promise': 'Corrosion Blisters assembles lifted blister caps, ruptured radial flaps, corrosion halos, '
            'exposed core windows and oxide satellite grains.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of crack surface processes; the authored '
                                    'masks and material tiers are an artistic construction, not a '
                                    'measured physical simulation.',
                       'sources': ['https://pmc.ncbi.nlm.nih.gov/articles/PMC10456388/']},
 'carrier_grammar': 'Corrosion Blisters assembles lifted blister caps, ruptured radial flaps, corrosion '
                    'halos, exposed core windows and oxide satellite grains. Geometry is independently '
                    'authored in crack_designs.py:corrosion_blisters.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to lifted blister caps, '
                 'ruptured radial flaps, corrosion halos, exposed core windows, oxide satellite grains.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'lifted_blister_caps',
                 'role': 'Lifted blister caps use M/R/Cc intervals [(16, 240), (26, 210), (24, 248)] in '
                         'their own geometry.'},
                {'name': 'ruptured_radial_flaps',
                 'role': 'Ruptured radial flaps use M/R/Cc intervals [(142, 255), (16, 110), (0, 114)] '
                         'in their own geometry.'},
                {'name': 'corrosion_halos',
                 'role': 'Corrosion halos use M/R/Cc intervals [(0, 96), (182, 255), (148, 254)] in '
                         'their own geometry.'},
                {'name': 'exposed_core_windows',
                 'role': 'Exposed core windows use M/R/Cc intervals [(52, 204), (96, 228), (66, 204)] '
                         'in their own geometry.'},
                {'name': 'oxide_satellite_grains',
                 'role': 'Oxide satellite grains use M/R/Cc intervals [(96, 226), (54, 178), (164, '
                         '255)] in their own geometry.'}],
 'material_binding': {'M': ['lifted_blister_caps',
                            'ruptured_radial_flaps',
                            'corrosion_halos',
                            'exposed_core_windows',
                            'oxide_satellite_grains'],
                      'R': ['lifted_blister_caps',
                            'ruptured_radial_flaps',
                            'corrosion_halos',
                            'exposed_core_windows',
                            'oxide_satellite_grains'],
                      'Cc': ['lifted_blister_caps',
                             'ruptured_radial_flaps',
                             'corrosion_halos',
                             'exposed_core_windows',
                             'oxide_satellite_grains']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_crazed_porcelain',
                        'difference': 'Corrosion Blisters must visibly separate through lifted blister '
                                      'caps, ruptured radial flaps, corrosion halos and the remaining '
                                      'named marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_mud_crackle',
                        'difference': 'Corrosion Blisters must visibly separate through lifted blister '
                                      'caps, ruptured radial flaps, corrosion halos and the remaining '
                                      'named marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Raised blister rings surround interrupted corrosion centers.',
                                     'lifted blister caps is present in the native named-feature '
                                     'coverage probe.',
                                     'ruptured radial flaps is present in the native named-feature '
                                     'coverage probe.',
                                     'corrosion halos is present in the native named-feature coverage '
                                     'probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/corrosion_blisters/independent-feature-carrier',
 'spec_key': 'spec-v2/corrosion_blisters/named-material-bindings'}

render = build_renderer(corrosion_blisters, IDENTITY_CONTRACT)
