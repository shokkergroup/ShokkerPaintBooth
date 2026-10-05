# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 98.49; invariant nearest 0.34943 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Wing Scale Sockets. Identity declared before rendering/scoring."""
from ..skin_designs import wing_scale_sockets
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_wing_scale_sockets',
 'display_name': 'Wing Scale Sockets - spec overlay',
 'promise': 'Wing Scale Sockets assembles scale blades, longitudinal ribs, socket cups, cross rib '
            'windows and serrated blade ends.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of skin surface processes; the authored '
                                    'masks and material tiers are an artistic construction, not a '
                                    'measured physical simulation.',
                       'sources': ['https://pmc.ncbi.nlm.nih.gov/articles/PMC6631580/']},
 'carrier_grammar': 'Wing Scale Sockets assembles scale blades, longitudinal ribs, socket cups, cross '
                    'rib windows and serrated blade ends. Geometry is independently authored in '
                    'skin_designs.py:wing_scale_sockets.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to scale blades, longitudinal '
                 'ribs, socket cups, cross rib windows, serrated blade ends.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'scale_blades',
                 'role': 'Scale blades use M/R/Cc intervals [(18, 246), (20, 224), (24, 248)] in their '
                         'own geometry.'},
                {'name': 'longitudinal_ribs',
                 'role': 'Longitudinal ribs use M/R/Cc intervals [(146, 255), (16, 92), (0, 112)] in '
                         'their own geometry.'},
                {'name': 'socket_cups',
                 'role': 'Socket cups use M/R/Cc intervals [(0, 96), (170, 255), (142, 252)] in their '
                         'own geometry.'},
                {'name': 'cross_rib_windows',
                 'role': 'Cross rib windows use M/R/Cc intervals [(52, 204), (116, 232), (72, 210)] in '
                         'their own geometry.'},
                {'name': 'serrated_blade_ends',
                 'role': 'Serrated blade ends use M/R/Cc intervals [(102, 232), (62, 192), (160, 254)] '
                         'in their own geometry.'}],
 'material_binding': {'M': ['scale_blades',
                            'longitudinal_ribs',
                            'socket_cups',
                            'cross_rib_windows',
                            'serrated_blade_ends'],
                      'R': ['scale_blades',
                            'longitudinal_ribs',
                            'socket_cups',
                            'cross_rib_windows',
                            'serrated_blade_ends'],
                      'Cc': ['scale_blades',
                             'longitudinal_ribs',
                             'socket_cups',
                             'cross_rib_windows',
                             'serrated_blade_ends']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_denticle_armor',
                        'difference': 'Wing Scale Sockets must visibly separate through scale blades, '
                                      'longitudinal ribs, socket cups and the remaining named marks, '
                                      'not color or parameter changes.'},
                       {'finish_id': 'spov2_diatom_sieve',
                        'difference': 'Wing Scale Sockets must visibly separate through scale blades, '
                                      'longitudinal ribs, socket cups and the remaining named marks, '
                                      'not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Long scale blades end in socket cups and fine rib windows.',
                                     'scale blades is present in the native named-feature coverage '
                                     'probe.',
                                     'longitudinal ribs is present in the native named-feature coverage '
                                     'probe.',
                                     'socket cups is present in the native named-feature coverage '
                                     'probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/wing_scale_sockets/independent-feature-carrier',
 'spec_key': 'spec-v2/wing_scale_sockets/named-material-bindings'}

render = build_renderer(wing_scale_sockets, IDENTITY_CONTRACT)
