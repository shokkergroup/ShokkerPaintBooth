# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 89.55; invariant nearest 0.21848 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Florentine Hatch. Identity declared before rendering/scoring."""
from ..engraved_designs import florentine_hatch
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_florentine_hatch',
 'display_name': 'Florentine Hatch - spec overlay',
 'promise': 'Florentine Hatch assembles first chisel hatching, crosscut engraving, recessed cut starts, '
            'raised chisel shoulders and crossing burr clusters.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of engraved surface processes; the '
                                    'authored masks and material tiers are an artistic construction, '
                                    'not a measured physical simulation.',
                       'sources': ['https://www.breguet.com/en/guilloche-according-breguet']},
 'carrier_grammar': 'Florentine Hatch assembles first chisel hatching, crosscut engraving, recessed cut '
                    'starts, raised chisel shoulders and crossing burr clusters. Geometry is '
                    'independently authored in engraved_designs.py:florentine_hatch.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to first chisel hatching, '
                 'crosscut engraving, recessed cut starts, raised chisel shoulders, crossing burr '
                 'clusters.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'first_chisel_hatching',
                 'role': 'First chisel hatching use M/R/Cc intervals [(20, 240), (28, 216), (24, 248)] '
                         'in their own geometry.'},
                {'name': 'crosscut_engraving',
                 'role': 'Crosscut engraving use M/R/Cc intervals [(146, 255), (16, 108), (0, 114)] in '
                         'their own geometry.'},
                {'name': 'recessed_cut_starts',
                 'role': 'Recessed cut starts use M/R/Cc intervals [(0, 100), (180, 255), (146, 254)] '
                         'in their own geometry.'},
                {'name': 'raised_chisel_shoulders',
                 'role': 'Raised chisel shoulders use M/R/Cc intervals [(58, 204), (102, 230), (68, '
                         '210)] in their own geometry.'},
                {'name': 'crossing_burr_clusters',
                 'role': 'Crossing burr clusters use M/R/Cc intervals [(96, 228), (54, 184), (164, '
                         '255)] in their own geometry.'}],
 'material_binding': {'M': ['first_chisel_hatching',
                            'crosscut_engraving',
                            'recessed_cut_starts',
                            'raised_chisel_shoulders',
                            'crossing_burr_clusters'],
                      'R': ['first_chisel_hatching',
                            'crosscut_engraving',
                            'recessed_cut_starts',
                            'raised_chisel_shoulders',
                            'crossing_burr_clusters'],
                      'Cc': ['first_chisel_hatching',
                             'crosscut_engraving',
                             'recessed_cut_starts',
                             'raised_chisel_shoulders',
                             'crossing_burr_clusters']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_security_guilloche',
                        'difference': 'Florentine Hatch must visibly separate through first chisel '
                                      'hatching, crosscut engraving, recessed cut starts and the '
                                      'remaining named marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_damascene_inlay',
                        'difference': 'Florentine Hatch must visibly separate through first chisel '
                                      'hatching, crosscut engraving, recessed cut starts and the '
                                      'remaining named marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Independent interrupted chisel passes cross without filled tile '
                                     'plates.',
                                     'first chisel hatching is present in the native named-feature '
                                     'coverage probe.',
                                     'crosscut engraving is present in the native named-feature '
                                     'coverage probe.',
                                     'recessed cut starts is present in the native named-feature '
                                     'coverage probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/florentine_hatch/independent-feature-carrier',
 'spec_key': 'spec-v2/florentine_hatch/named-material-bindings'}

render = build_renderer(florentine_hatch, IDENTITY_CONTRACT)
