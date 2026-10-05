# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 97.41; invariant nearest 0.54044 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 2: Denticle Armor. Identity declared before scoring."""
from ..proof_designs import denticle_armor
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_denticle_armor',
 'display_name': 'Denticle Armor — spec overlay',
 'promise': 'Pointed plates carry split keels, root collars, worn patches and separate between-plate '
            'pores.',
 'paint_policy': 'Preserve all source paint bytes; this is a spec-only overlay.',
 'reference_physics': {'mechanism': 'Shark denticles carry riblets and pointed crowns above overlapping '
                                    'roots; this is a decorative material interpretation.',
                       'sources': ['https://pmc.ncbi.nlm.nih.gov/articles/PMC6631580/']},
 'carrier_grammar': 'Pointed plates carry split keels, root collars, worn patches and separate '
                    'between-plate pores.',
 'spec_grammar': 'Feature-owned M/R/Cc intervals, independently shaded at individual_plates, '
                 'split_keels, root_collars, abrasion_patches, between_plate_pores.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'individual_plates',
                 'role': 'Material response follows the named individual plates feature.'},
                {'name': 'split_keels',
                 'role': 'Material response follows the named split keels feature.'},
                {'name': 'root_collars',
                 'role': 'Material response follows the named root collars feature.'},
                {'name': 'abrasion_patches',
                 'role': 'Material response follows the named abrasion patches feature.'},
                {'name': 'between_plate_pores',
                 'role': 'Material response follows the named between plate pores feature.'}],
 'material_binding': {'M': ['individual_plates',
                            'split_keels',
                            'root_collars',
                            'abrasion_patches',
                            'between_plate_pores'],
                      'R': ['individual_plates',
                            'split_keels',
                            'root_collars',
                            'abrasion_patches',
                            'between_plate_pores'],
                      'Cc': ['individual_plates',
                             'split_keels',
                             'root_collars',
                             'abrasion_patches',
                             'between_plate_pores']},
 'material_tiers': ['bare substrate',
                    'rough recess',
                    'satin floor',
                    'polished ridge',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'highlight tip'],
 'nearest_neighbors': [{'finish_id': 'shark_denticle',
                        'difference': 'Must differ through pointed plates carry split keels, root '
                                      'collars, worn patches and separate between-plate pores.'},
                       {'finish_id': 'spec_sharkskin_riblet',
                        'difference': 'Must differ through pointed plates carry split keels, root '
                                      'collars, worn patches and separate between-plate pores.'}],
 'name_truth': {'visible_evidence': ['Overlapping pointed dermal plates carry ridges and attachment '
                                     'details.',
                                     'individual plates is present in the native named-feature coverage '
                                     'probe.',
                                     'split keels is present in the native named-feature coverage '
                                     'probe.',
                                     'root collars is present in the native named-feature coverage '
                                     'probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'v2/denticle_armor/individual_plates:split_keels:root_collars:abrasion_patches:between_plate_pores',
 'spec_key': 'v2/denticle_armor/authored-feature-targets-and-coverage'}

render = build_renderer(denticle_armor, IDENTITY_CONTRACT)
