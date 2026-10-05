# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 95.67; invariant nearest 0.42888 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Conchoidal Obsidian. Identity declared before rendering/scoring."""
from ..crystal_designs import conchoidal_obsidian
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_conchoidal_obsidian',
 'display_name': 'Conchoidal Obsidian - spec overlay',
 'promise': 'Conchoidal Obsidian assembles shell fracture faces, arrest ridges, impact bulbs, hackle '
            'forks and sharp chips.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of crystal surface processes; the '
                                    'authored masks and material tiers are an artistic construction, '
                                    'not a measured physical simulation.',
                       'sources': ['https://www.nist.gov/itl/math/visualization-dendritic-growth']},
 'carrier_grammar': 'Conchoidal Obsidian assembles shell fracture faces, arrest ridges, impact bulbs, '
                    'hackle forks and sharp chips. Geometry is independently authored in '
                    'crystal_designs.py:conchoidal_obsidian.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to shell fracture faces, arrest '
                 'ridges, impact bulbs, hackle forks, sharp chips.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'shell_fracture_faces',
                 'role': 'Shell fracture faces use M/R/Cc intervals [(12, 240), (16, 224), (24, 248)] '
                         'in their own geometry.'},
                {'name': 'arrest_ridges',
                 'role': 'Arrest ridges use M/R/Cc intervals [(142, 255), (22, 110), (0, 96)] in their '
                         'own geometry.'},
                {'name': 'impact_bulbs',
                 'role': 'Impact bulbs use M/R/Cc intervals [(0, 102), (148, 250), (128, 252)] in their '
                         'own geometry.'},
                {'name': 'hackle_forks',
                 'role': 'Hackle forks use M/R/Cc intervals [(54, 206), (66, 188), (70, 232)] in their '
                         'own geometry.'},
                {'name': 'sharp_chips',
                 'role': 'Sharp chips use M/R/Cc intervals [(170, 255), (10, 66), (148, 252)] in their '
                         'own geometry.'}],
 'material_binding': {'M': ['shell_fracture_faces',
                            'arrest_ridges',
                            'impact_bulbs',
                            'hackle_forks',
                            'sharp_chips'],
                      'R': ['shell_fracture_faces',
                            'arrest_ridges',
                            'impact_bulbs',
                            'hackle_forks',
                            'sharp_chips'],
                      'Cc': ['shell_fracture_faces',
                             'arrest_ridges',
                             'impact_bulbs',
                             'hackle_forks',
                             'sharp_chips']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_crystal_front',
                        'difference': 'Conchoidal Obsidian must visibly separate through shell fracture '
                                      'faces, arrest ridges, impact bulbs and the remaining named '
                                      'marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_basalt_prisms',
                        'difference': 'Conchoidal Obsidian must visibly separate through shell fracture '
                                      'faces, arrest ridges, impact bulbs and the remaining named '
                                      'marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Nested curved fracture fronts stop against angular chips.',
                                     'shell fracture faces is present in the native named-feature '
                                     'coverage probe.',
                                     'arrest ridges is present in the native named-feature coverage '
                                     'probe.',
                                     'impact bulbs is present in the native named-feature coverage '
                                     'probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/conchoidal_obsidian/independent-feature-carrier',
 'spec_key': 'spec-v2/conchoidal_obsidian/named-material-bindings'}

render = build_renderer(conchoidal_obsidian, IDENTITY_CONTRACT)
