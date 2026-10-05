# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 94.57; invariant nearest 0.54073 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 2: Paired Facet Lattice. Identity declared before scoring."""
from ..proof_designs import paired_facet_lattice
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_paired_facet_lattice',
 'display_name': 'Paired Facet Lattice — spec overlay',
 'promise': 'Paired platelets alternate material response around bevels, junctions, etched notches and '
            'polished tips.',
 'paint_policy': 'Preserve all source paint bytes; this is a spec-only overlay.',
 'reference_physics': {'mechanism': 'Static interleaving of metallic, roughness and acrylic-coat '
                                    'response aims at highlight exchange; no added normals or true '
                                    'interference shader is claimed.',
                       'sources': ['https://support.iracing.com/support/solutions/articles/31000168823-2023-season-1-release-notes-2022-12-06-01-']},
 'carrier_grammar': 'Paired platelets alternate material response around bevels, junctions, etched '
                    'notches and polished tips.',
 'spec_grammar': 'Feature-owned M/R/Cc intervals, independently shaded at alternating_platelets, '
                 'bevel_bands, junction_knots, etched_notches, polished_tips.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'alternating_platelets',
                 'role': 'Material response follows the named alternating platelets feature.'},
                {'name': 'bevel_bands',
                 'role': 'Material response follows the named bevel bands feature.'},
                {'name': 'junction_knots',
                 'role': 'Material response follows the named junction knots feature.'},
                {'name': 'etched_notches',
                 'role': 'Material response follows the named etched notches feature.'},
                {'name': 'polished_tips',
                 'role': 'Material response follows the named polished tips feature.'}],
 'material_binding': {'M': ['alternating_platelets',
                            'bevel_bands',
                            'junction_knots',
                            'etched_notches',
                            'polished_tips'],
                      'R': ['alternating_platelets',
                            'bevel_bands',
                            'junction_knots',
                            'etched_notches',
                            'polished_tips'],
                      'Cc': ['alternating_platelets',
                             'bevel_bands',
                             'junction_knots',
                             'etched_notches',
                             'polished_tips']},
 'material_tiers': ['bare substrate',
                    'rough recess',
                    'satin floor',
                    'polished ridge',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'highlight tip'],
 'nearest_neighbors': [{'finish_id': 'hex_cells',
                        'difference': 'Must differ through paired platelets alternate material response '
                                      'around bevels, junctions, etched notches and polished tips.'},
                       {'finish_id': 'spec_teal_hex_haze',
                        'difference': 'Must differ through paired platelets alternate material response '
                                      'around bevels, junctions, etched notches and polished tips.'}],
 'name_truth': {'visible_evidence': ['Paired opposing facets meet central junctions in an open lattice.',
                                     'alternating platelets is present in the native named-feature '
                                     'coverage probe.',
                                     'bevel bands is present in the native named-feature coverage '
                                     'probe.',
                                     'junction knots is present in the native named-feature coverage '
                                     'probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'v2/paired_facet_lattice/alternating_platelets:bevel_bands:junction_knots:etched_notches:polished_tips',
 'spec_key': 'v2/paired_facet_lattice/authored-feature-targets-and-coverage'}

render = build_renderer(paired_facet_lattice, IDENTITY_CONTRACT)
