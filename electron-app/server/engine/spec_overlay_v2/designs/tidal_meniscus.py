# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 96.01; invariant nearest 0.54073 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 2: Tidal Meniscus. Identity declared before scoring."""
from ..proof_designs import tidal_meniscus
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_tidal_meniscus',
 'display_name': 'Tidal Meniscus — spec overlay',
 'promise': 'Wet islands recede inside contact arcs, leaving pinning points, beads and residue rings.',
 'paint_policy': 'Preserve all source paint bytes; this is a spec-only overlay.',
 'reference_physics': {'mechanism': 'A pinned or receding liquid contact line leaves distinct wet '
                                    'boundaries and deposited residue.',
                       'sources': ['https://www.nature.com/articles/s41467-022-30660-6']},
 'carrier_grammar': 'Wet islands recede inside contact arcs, leaving pinning points, beads and residue '
                    'rings.',
 'spec_grammar': 'Feature-owned M/R/Cc intervals, independently shaded at receding_islands, '
                 'contact_line_arcs, residue_rings, pinning_points, bead_clusters.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'receding_islands',
                 'role': 'Material response follows the named receding islands feature.'},
                {'name': 'contact_line_arcs',
                 'role': 'Material response follows the named contact line arcs feature.'},
                {'name': 'residue_rings',
                 'role': 'Material response follows the named residue rings feature.'},
                {'name': 'pinning_points',
                 'role': 'Material response follows the named pinning points feature.'},
                {'name': 'bead_clusters',
                 'role': 'Material response follows the named bead clusters feature.'}],
 'material_binding': {'M': ['receding_islands',
                            'contact_line_arcs',
                            'residue_rings',
                            'pinning_points',
                            'bead_clusters'],
                      'R': ['receding_islands',
                            'contact_line_arcs',
                            'residue_rings',
                            'pinning_points',
                            'bead_clusters'],
                      'Cc': ['receding_islands',
                             'contact_line_arcs',
                             'residue_rings',
                             'pinning_points',
                             'bead_clusters']},
 'material_tiers': ['bare substrate',
                    'rough recess',
                    'satin floor',
                    'polished ridge',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'highlight tip'],
 'nearest_neighbors': [{'finish_id': 'cc_wet_zone',
                        'difference': 'Must differ through wet islands recede inside contact arcs, '
                                      'leaving pinning points, beads and residue rings.'},
                       {'finish_id': 'spec_fuel_stain_evap_ring',
                        'difference': 'Must differ through wet islands recede inside contact arcs, '
                                      'leaving pinning points, beads and residue rings.'}],
 'name_truth': {'visible_evidence': ['Pinned meniscus arcs, residue collars and bead groups remain '
                                     'separate.',
                                     'receding islands is present in the native named-feature coverage '
                                     'probe.',
                                     'contact line arcs is present in the native named-feature coverage '
                                     'probe.',
                                     'residue rings is present in the native named-feature coverage '
                                     'probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'v2/tidal_meniscus/receding_islands:contact_line_arcs:residue_rings:pinning_points:bead_clusters',
 'spec_key': 'v2/tidal_meniscus/authored-feature-targets-and-coverage'}

render = build_renderer(tidal_meniscus, IDENTITY_CONTRACT)
