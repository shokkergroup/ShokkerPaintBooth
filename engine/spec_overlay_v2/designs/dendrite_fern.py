# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 94.85; invariant nearest 0.37671 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Dendrite Fern. Identity declared before rendering/scoring."""
from ..crystal_designs import dendrite_fern
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_dendrite_fern',
 'display_name': 'Dendrite Fern - spec overlay',
 'promise': 'Dendrite Fern assembles primary growth stems, lateral dendrite arms, branch tip plates, '
            'interarm deposits and stem growth nodes.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of crystal surface processes; the '
                                    'authored masks and material tiers are an artistic construction, '
                                    'not a measured physical simulation.',
                       'sources': ['https://www.nist.gov/itl/math/visualization-dendritic-growth']},
 'carrier_grammar': 'Dendrite Fern assembles primary growth stems, lateral dendrite arms, branch tip '
                    'plates, interarm deposits and stem growth nodes. Geometry is independently '
                    'authored in crystal_designs.py:dendrite_fern.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to primary growth stems, '
                 'lateral dendrite arms, branch tip plates, interarm deposits, stem growth nodes.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'primary_growth_stems',
                 'role': 'Primary growth stems use M/R/Cc intervals [(146, 255), (20, 130), (24, 230)] '
                         'in their own geometry.'},
                {'name': 'lateral_dendrite_arms',
                 'role': 'Lateral dendrite arms use M/R/Cc intervals [(28, 224), (38, 226), (16, 248)] '
                         'in their own geometry.'},
                {'name': 'branch_tip_plates',
                 'role': 'Branch tip plates use M/R/Cc intervals [(0, 98), (170, 255), (142, 255)] in '
                         'their own geometry.'},
                {'name': 'interarm_deposits',
                 'role': 'Interarm deposits use M/R/Cc intervals [(70, 194), (102, 244), (56, 192)] in '
                         'their own geometry.'},
                {'name': 'stem_growth_nodes',
                 'role': 'Stem growth nodes use M/R/Cc intervals [(178, 255), (16, 70), (0, 80)] in '
                         'their own geometry.'}],
 'material_binding': {'M': ['primary_growth_stems',
                            'lateral_dendrite_arms',
                            'branch_tip_plates',
                            'interarm_deposits',
                            'stem_growth_nodes'],
                      'R': ['primary_growth_stems',
                            'lateral_dendrite_arms',
                            'branch_tip_plates',
                            'interarm_deposits',
                            'stem_growth_nodes'],
                      'Cc': ['primary_growth_stems',
                             'lateral_dendrite_arms',
                             'branch_tip_plates',
                             'interarm_deposits',
                             'stem_growth_nodes']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_crystal_front',
                        'difference': 'Dendrite Fern must visibly separate through primary growth '
                                      'stems, lateral dendrite arms, branch tip plates and the '
                                      'remaining named marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_conchoidal_obsidian',
                        'difference': 'Dendrite Fern must visibly separate through primary growth '
                                      'stems, lateral dendrite arms, branch tip plates and the '
                                      'remaining named marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Bilateral branchlets grow from short central crystal stems.',
                                     'primary growth stems is present in the native named-feature '
                                     'coverage probe.',
                                     'lateral dendrite arms is present in the native named-feature '
                                     'coverage probe.',
                                     'branch tip plates is present in the native named-feature coverage '
                                     'probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/dendrite_fern/independent-feature-carrier',
 'spec_key': 'spec-v2/dendrite_fern/named-material-bindings'}

render = build_renderer(dendrite_fern, IDENTITY_CONTRACT)
