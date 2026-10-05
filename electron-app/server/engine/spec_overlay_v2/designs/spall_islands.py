# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 98.56; invariant nearest 0.31244 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Spall Islands. Identity declared before rendering/scoring."""
from ..crack_designs import spall_islands
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_spall_islands',
 'display_name': 'Spall Islands - spec overlay',
 'promise': 'Spall Islands assembles retained coating flakes, spalled substrate windows, undercut flake '
            'edges, shear bridge filaments and detached chip triads.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of crack surface processes; the authored '
                                    'masks and material tiers are an artistic construction, not a '
                                    'measured physical simulation.',
                       'sources': ['https://pmc.ncbi.nlm.nih.gov/articles/PMC10456388/']},
 'carrier_grammar': 'Spall Islands assembles retained coating flakes, spalled substrate windows, '
                    'undercut flake edges, shear bridge filaments and detached chip triads. Geometry is '
                    'independently authored in crack_designs.py:spall_islands.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to retained coating flakes, '
                 'spalled substrate windows, undercut flake edges, shear bridge filaments, detached '
                 'chip triads.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'retained_coating_flakes',
                 'role': 'Retained coating flakes use M/R/Cc intervals [(16, 244), (26, 216), (24, '
                         '248)] in their own geometry.'},
                {'name': 'spalled_substrate_windows',
                 'role': 'Spalled substrate windows use M/R/Cc intervals [(148, 255), (16, 106), (0, '
                         '114)] in their own geometry.'},
                {'name': 'undercut_flake_edges',
                 'role': 'Undercut flake edges use M/R/Cc intervals [(0, 102), (176, 255), (142, 254)] '
                         'in their own geometry.'},
                {'name': 'shear_bridge_filaments',
                 'role': 'Shear bridge filaments use M/R/Cc intervals [(54, 204), (102, 232), (68, '
                         '204)] in their own geometry.'},
                {'name': 'detached_chip_triads',
                 'role': 'Detached chip triads use M/R/Cc intervals [(98, 228), (54, 180), (164, 255)] '
                         'in their own geometry.'}],
 'material_binding': {'M': ['retained_coating_flakes',
                            'spalled_substrate_windows',
                            'undercut_flake_edges',
                            'shear_bridge_filaments',
                            'detached_chip_triads'],
                      'R': ['retained_coating_flakes',
                            'spalled_substrate_windows',
                            'undercut_flake_edges',
                            'shear_bridge_filaments',
                            'detached_chip_triads'],
                      'Cc': ['retained_coating_flakes',
                             'spalled_substrate_windows',
                             'undercut_flake_edges',
                             'shear_bridge_filaments',
                             'detached_chip_triads']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_crazed_porcelain',
                        'difference': 'Spall Islands must visibly separate through retained coating '
                                      'flakes, spalled substrate windows, undercut flake edges and the '
                                      'remaining named marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_mud_crackle',
                        'difference': 'Spall Islands must visibly separate through retained coating '
                                      'flakes, spalled substrate windows, undercut flake edges and the '
                                      'remaining named marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Angular spall islands retain lifted edges and detached fragments.',
                                     'retained coating flakes is present in the native named-feature '
                                     'coverage probe.',
                                     'spalled substrate windows is present in the native named-feature '
                                     'coverage probe.',
                                     'undercut flake edges is present in the native named-feature '
                                     'coverage probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/spall_islands/independent-feature-carrier',
 'spec_key': 'spec-v2/spall_islands/named-material-bindings'}

render = build_renderer(spall_islands, IDENTITY_CONTRACT)
