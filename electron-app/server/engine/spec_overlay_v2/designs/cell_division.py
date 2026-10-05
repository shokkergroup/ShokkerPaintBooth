# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 97.25; invariant nearest 0.41758 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Cell Division. Identity declared before rendering/scoring."""
from ..skin_designs import cell_division
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_cell_division',
 'display_name': 'Cell Division - spec overlay',
 'promise': 'Cell Division assembles daughter cell membranes, contractile furrows, membrane lips, '
            'paired nuclei and vesicle chains.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of skin surface processes; the authored '
                                    'masks and material tiers are an artistic construction, not a '
                                    'measured physical simulation.',
                       'sources': ['https://pmc.ncbi.nlm.nih.gov/articles/PMC6631580/']},
 'carrier_grammar': 'Cell Division assembles daughter cell membranes, contractile furrows, membrane '
                    'lips, paired nuclei and vesicle chains. Geometry is independently authored in '
                    'skin_designs.py:cell_division.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to daughter cell membranes, '
                 'contractile furrows, membrane lips, paired nuclei, vesicle chains.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'daughter_cell_membranes',
                 'role': 'Daughter cell membranes use M/R/Cc intervals [(18, 238), (0, 246), (24, 248)] '
                         'in their own geometry.'},
                {'name': 'contractile_furrows',
                 'role': 'Contractile furrows use M/R/Cc intervals [(0, 102), (164, 255), (132, 252)] '
                         'in their own geometry.'},
                {'name': 'membrane_lips',
                 'role': 'Membrane lips use M/R/Cc intervals [(152, 255), (0, 98), (0, 110)] in their '
                         'own geometry.'},
                {'name': 'paired_nuclei',
                 'role': 'Paired nuclei use M/R/Cc intervals [(54, 200), (90, 218), (66, 206)] in their '
                         'own geometry.'},
                {'name': 'vesicle_chains',
                 'role': 'Vesicle chains use M/R/Cc intervals [(106, 232), (48, 172), (158, 255)] in '
                         'their own geometry.'}],
 'material_binding': {'M': ['daughter_cell_membranes',
                            'contractile_furrows',
                            'membrane_lips',
                            'paired_nuclei',
                            'vesicle_chains'],
                      'R': ['daughter_cell_membranes',
                            'contractile_furrows',
                            'membrane_lips',
                            'paired_nuclei',
                            'vesicle_chains'],
                      'Cc': ['daughter_cell_membranes',
                             'contractile_furrows',
                             'membrane_lips',
                             'paired_nuclei',
                             'vesicle_chains']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_denticle_armor',
                        'difference': 'Cell Division must visibly separate through daughter cell '
                                      'membranes, contractile furrows, membrane lips and the remaining '
                                      'named marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_diatom_sieve',
                        'difference': 'Cell Division must visibly separate through daughter cell '
                                      'membranes, contractile furrows, membrane lips and the remaining '
                                      'named marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Constricted cell outlines enclose separated daughter nuclei.',
                                     'daughter cell membranes is present in the native named-feature '
                                     'coverage probe.',
                                     'contractile furrows is present in the native named-feature '
                                     'coverage probe.',
                                     'membrane lips is present in the native named-feature coverage '
                                     'probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/cell_division/independent-feature-carrier',
 'spec_key': 'spec-v2/cell_division/named-material-bindings'}

render = build_renderer(cell_division, IDENTITY_CONTRACT)
