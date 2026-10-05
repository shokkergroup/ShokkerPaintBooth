# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 98.69; invariant nearest 0.4796 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Auxetic Hinges. Identity declared before rendering/scoring."""
from ..experimental_designs import auxetic_hinges
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_auxetic_hinges',
 'display_name': 'Auxetic Hinges - spec overlay',
 'promise': 'Auxetic Hinges assembles reentrant bowtie plates, rotating hinge necks, reentrant edge '
            'slots, shear relief eyelets and hinge corner bearing tabs.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of experimental surface processes; the '
                                    'authored masks and material tiers are an artistic construction, '
                                    'not a measured physical simulation.',
                       'sources': ['https://arxiv.org/abs/2303.10798']},
 'carrier_grammar': 'Auxetic Hinges assembles reentrant bowtie plates, rotating hinge necks, reentrant '
                    'edge slots, shear relief eyelets and hinge corner bearing tabs. Geometry is '
                    'independently authored in experimental_designs.py:auxetic_hinges.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to reentrant bowtie plates, '
                 'rotating hinge necks, reentrant edge slots, shear relief eyelets, hinge corner '
                 'bearing tabs.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'reentrant_bowtie_plates',
                 'role': 'Reentrant bowtie plates use M/R/Cc intervals [(18, 246), (24, 214), (24, '
                         '248)] in their own geometry.'},
                {'name': 'rotating_hinge_necks',
                 'role': 'Rotating hinge necks use M/R/Cc intervals [(146, 255), (16, 108), (0, 114)] '
                         'in their own geometry.'},
                {'name': 'reentrant_edge_slots',
                 'role': 'Reentrant edge slots use M/R/Cc intervals [(0, 98), (180, 255), (146, 254)] '
                         'in their own geometry.'},
                {'name': 'shear_relief_eyelets',
                 'role': 'Shear relief eyelets use M/R/Cc intervals [(56, 204), (102, 232), (68, 204)] '
                         'in their own geometry.'},
                {'name': 'hinge_corner_bearing_tabs',
                 'role': 'Hinge corner bearing tabs use M/R/Cc intervals [(96, 228), (54, 180), (164, '
                         '255)] in their own geometry.'}],
 'material_binding': {'M': ['reentrant_bowtie_plates',
                            'rotating_hinge_necks',
                            'reentrant_edge_slots',
                            'shear_relief_eyelets',
                            'hinge_corner_bearing_tabs'],
                      'R': ['reentrant_bowtie_plates',
                            'rotating_hinge_necks',
                            'reentrant_edge_slots',
                            'shear_relief_eyelets',
                            'hinge_corner_bearing_tabs'],
                      'Cc': ['reentrant_bowtie_plates',
                             'rotating_hinge_necks',
                             'reentrant_edge_slots',
                             'shear_relief_eyelets',
                             'hinge_corner_bearing_tabs']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_aperiodic_alloy',
                        'difference': 'Auxetic Hinges must visibly separate through reentrant bowtie '
                                      'plates, rotating hinge necks, reentrant edge slots and the '
                                      'remaining named marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_gyroid_windows',
                        'difference': 'Auxetic Hinges must visibly separate through reentrant bowtie '
                                      'plates, rotating hinge necks, reentrant edge slots and the '
                                      'remaining named marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Re-entrant hinge units form inward-bending open cells.',
                                     'reentrant bowtie plates is present in the native named-feature '
                                     'coverage probe.',
                                     'rotating hinge necks is present in the native named-feature '
                                     'coverage probe.',
                                     'reentrant edge slots is present in the native named-feature '
                                     'coverage probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/auxetic_hinges/independent-feature-carrier',
 'spec_key': 'spec-v2/auxetic_hinges/named-material-bindings'}

render = build_renderer(auxetic_hinges, IDENTITY_CONTRACT)
