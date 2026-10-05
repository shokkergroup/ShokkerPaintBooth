# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 94.7; invariant nearest 0.28596 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Mushroom Gills. Identity declared before rendering/scoring."""
from ..skin_designs import mushroom_gills
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_mushroom_gills',
 'display_name': 'Mushroom Gills - spec overlay',
 'promise': 'Mushroom Gills assembles radial lamella blades, short intercalary gills, gill attachment '
            'roots, spore print clusters and torn lamella tips.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of skin surface processes; the authored '
                                    'masks and material tiers are an artistic construction, not a '
                                    'measured physical simulation.',
                       'sources': ['https://pmc.ncbi.nlm.nih.gov/articles/PMC6631580/']},
 'carrier_grammar': 'Mushroom Gills assembles radial lamella blades, short intercalary gills, gill '
                    'attachment roots, spore print clusters and torn lamella tips. Geometry is '
                    'independently authored in skin_designs.py:mushroom_gills.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to radial lamella blades, short '
                 'intercalary gills, gill attachment roots, spore print clusters, torn lamella tips.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'radial_lamella_blades',
                 'role': 'Radial lamella blades use M/R/Cc intervals [(24, 250), (0, 255), (24, 240)] '
                         'in their own geometry.'},
                {'name': 'short_intercalary_gills',
                 'role': 'Short intercalary gills use M/R/Cc intervals [(154, 255), (16, 100), (0, '
                         '126)] in their own geometry.'},
                {'name': 'gill_attachment_roots',
                 'role': 'Gill attachment roots use M/R/Cc intervals [(0, 106), (176, 255), (140, 254)] '
                         'in their own geometry.'},
                {'name': 'spore_print_clusters',
                 'role': 'Spore print clusters use M/R/Cc intervals [(70, 216), (70, 200), (68, 222)] '
                         'in their own geometry.'},
                {'name': 'torn_lamella_tips',
                 'role': 'Torn lamella tips use M/R/Cc intervals [(114, 240), (36, 164), (166, 255)] in '
                         'their own geometry.'}],
 'material_binding': {'M': ['radial_lamella_blades',
                            'short_intercalary_gills',
                            'gill_attachment_roots',
                            'spore_print_clusters',
                            'torn_lamella_tips'],
                      'R': ['radial_lamella_blades',
                            'short_intercalary_gills',
                            'gill_attachment_roots',
                            'spore_print_clusters',
                            'torn_lamella_tips'],
                      'Cc': ['radial_lamella_blades',
                             'short_intercalary_gills',
                             'gill_attachment_roots',
                             'spore_print_clusters',
                             'torn_lamella_tips']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_denticle_armor',
                        'difference': 'Mushroom Gills must visibly separate through radial lamella '
                                      'blades, short intercalary gills, gill attachment roots and the '
                                      'remaining named marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_diatom_sieve',
                        'difference': 'Mushroom Gills must visibly separate through radial lamella '
                                      'blades, short intercalary gills, gill attachment roots and the '
                                      'remaining named marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Branching radial lamellae form irregular gill fans.',
                                     'radial lamella blades is present in the native named-feature '
                                     'coverage probe.',
                                     'short intercalary gills is present in the native named-feature '
                                     'coverage probe.',
                                     'gill attachment roots is present in the native named-feature '
                                     'coverage probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/mushroom_gills/independent-feature-carrier',
 'spec_key': 'spec-v2/mushroom_gills/named-material-bindings'}

render = build_renderer(mushroom_gills, IDENTITY_CONTRACT)
