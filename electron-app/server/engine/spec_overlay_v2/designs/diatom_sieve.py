# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 98.33; invariant nearest 0.42271 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 2: Diatom Sieve. Identity declared before scoring."""
from ..proof_designs import diatom_sieve
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_diatom_sieve',
 'display_name': 'Diatom Sieve — spec overlay',
 'promise': 'Bilateral pennate frustules contain an axial raphe, repeated pore rows, terminal plugs and '
            'separate valve rims.',
 'paint_policy': 'Preserve all source paint bytes; this is a spec-only overlay.',
 'reference_physics': {'mechanism': 'Diatom silica valves form patterned perforations and supporting '
                                    'structures; this design adapts those motifs to spec-only material '
                                    'fields.',
                       'sources': ['https://doi.org/10.1073/pnas.2211549119']},
 'carrier_grammar': 'Bilateral pennate frustules contain an axial raphe, repeated pore rows, terminal '
                    'plugs and separate valve rims.',
 'spec_grammar': 'Feature-owned M/R/Cc intervals, independently shaded at valve_rims, radial_struts, '
                 'perforation_rows, bridge_ribs, scar_plugs.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'valve_rims',
                 'role': 'Material response follows the named valve rims feature.'},
                {'name': 'radial_struts',
                 'role': 'Material response follows the named radial struts feature.'},
                {'name': 'perforation_rows',
                 'role': 'Material response follows the named perforation rows feature.'},
                {'name': 'bridge_ribs',
                 'role': 'Material response follows the named bridge ribs feature.'},
                {'name': 'scar_plugs',
                 'role': 'Material response follows the named scar plugs feature.'}],
 'material_binding': {'M': ['valve_rims',
                            'radial_struts',
                            'perforation_rows',
                            'bridge_ribs',
                            'scar_plugs'],
                      'R': ['valve_rims',
                            'radial_struts',
                            'perforation_rows',
                            'bridge_ribs',
                            'scar_plugs'],
                      'Cc': ['valve_rims',
                             'radial_struts',
                             'perforation_rows',
                             'bridge_ribs',
                             'scar_plugs']},
 'material_tiers': ['bare substrate',
                    'rough recess',
                    'satin floor',
                    'polished ridge',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'highlight tip'],
 'nearest_neighbors': [{'finish_id': 'pebble_grain',
                        'difference': 'Must differ through perforation rings link radial struts, valve '
                                      'rims, bridge ribs and isolated scar plugs.'},
                       {'finish_id': 'hex_cells',
                        'difference': 'Must differ through perforation rings link radial struts, valve '
                                      'rims, bridge ribs and isolated scar plugs.'}],
 'name_truth': {'visible_evidence': ['Elongated bilateral frustules contain an axial raphe and repeated '
                                     'pore rows.',
                                     'valve rims is present in the native named-feature coverage probe.',
                                     'radial struts is present in the native named-feature coverage '
                                     'probe.',
                                     'perforation rows is present in the native named-feature coverage '
                                     'probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'v2/diatom_sieve/valve_rims:radial_struts:perforation_rows:bridge_ribs:scar_plugs',
 'spec_key': 'v2/diatom_sieve/authored-feature-targets-and-coverage'}

render = build_renderer(diatom_sieve, IDENTITY_CONTRACT)
