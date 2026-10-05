# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 98.84; invariant nearest 0.47602 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 2: Crystal Front. Identity declared before scoring."""
from ..proof_designs import crystal_front
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_crystal_front',
 'display_name': 'Crystal Front — spec overlay',
 'promise': 'Competing square growth terraces surround nuclei, twin seams, interstitial pockets and '
            'chipped tips.',
 'paint_policy': 'Preserve all source paint bytes; this is a spec-only overlay.',
 'reference_physics': {'mechanism': 'Crystal surfaces grow through successive terrace steps and can '
                                    'form symmetry-related twin domains.',
                       'sources': ['https://journals.iucr.org/paper?buy=yes&cnor=mm0041']},
 'carrier_grammar': 'Competing square growth terraces surround nuclei, twin seams, interstitial pockets '
                    'and chipped tips.',
 'spec_grammar': 'Feature-owned M/R/Cc intervals, independently shaded at growth_terraces, twin_seams, '
                 'nuclei, interstitial_pockets, chipped_tips.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'growth_terraces',
                 'role': 'Material response follows the named growth terraces feature.'},
                {'name': 'twin_seams',
                 'role': 'Material response follows the named twin seams feature.'},
                {'name': 'nuclei', 'role': 'Material response follows the named nuclei feature.'},
                {'name': 'interstitial_pockets',
                 'role': 'Material response follows the named interstitial pockets feature.'},
                {'name': 'chipped_tips',
                 'role': 'Material response follows the named chipped tips feature.'}],
 'material_binding': {'M': ['growth_terraces',
                            'twin_seams',
                            'nuclei',
                            'interstitial_pockets',
                            'chipped_tips'],
                      'R': ['growth_terraces',
                            'twin_seams',
                            'nuclei',
                            'interstitial_pockets',
                            'chipped_tips'],
                      'Cc': ['growth_terraces',
                             'twin_seams',
                             'nuclei',
                             'interstitial_pockets',
                             'chipped_tips']},
 'material_tiers': ['bare substrate',
                    'rough recess',
                    'satin floor',
                    'polished ridge',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'highlight tip'],
 'nearest_neighbors': [{'finish_id': 'prismatic_shatter',
                        'difference': 'Must differ through competing square growth terraces surround '
                                      'nuclei, twin seams, interstitial pockets and chipped tips.'},
                       {'finish_id': 'spec_ice_facet_shatter',
                        'difference': 'Must differ through competing square growth terraces surround '
                                      'nuclei, twin seams, interstitial pockets and chipped tips.'}],
 'name_truth': {'visible_evidence': ['Stepped square growth fronts surround dark crystal centers.',
                                     'growth terraces is present in the native named-feature coverage '
                                     'probe.',
                                     'twin seams is present in the native named-feature coverage probe.',
                                     'nuclei is present in the native named-feature coverage probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'v2/crystal_front/growth_terraces:twin_seams:nuclei:interstitial_pockets:chipped_tips',
 'spec_key': 'v2/crystal_front/authored-feature-targets-and-coverage'}

render = build_renderer(crystal_front, IDENTITY_CONTRACT)
