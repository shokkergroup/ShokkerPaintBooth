# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 98.04; invariant nearest 0.36483 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Stitched Hex. Identity declared before rendering/scoring."""
from ..weave_designs import stitched_hex
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_stitched_hex',
 'display_name': 'Stitched Hex - spec overlay',
 'promise': 'Stitched Hex assembles quilted panels, seam stitches, buttoned centers, tension pleats and '
            'thread return loops.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of weave surface processes; the authored '
                                    'masks and material tiers are an artistic construction, not a '
                                    'measured physical simulation.',
                       'sources': ['https://www.toraycma.com/wp-content/uploads/3900-Prepreg-System.pdf']},
 'carrier_grammar': 'Stitched Hex assembles quilted panels, seam stitches, buttoned centers, tension '
                    'pleats and thread return loops. Geometry is independently authored in '
                    'weave_designs.py:stitched_hex.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to quilted panels, seam '
                 'stitches, buttoned centers, tension pleats, thread return loops.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'quilted_panels',
                 'role': 'Quilted panels use M/R/Cc intervals [(18, 228), (0, 246), (24, 236)] in their '
                         'own geometry.'},
                {'name': 'seam_stitches',
                 'role': 'Seam stitches use M/R/Cc intervals [(160, 255), (0, 92), (0, 122)] in their '
                         'own geometry.'},
                {'name': 'buttoned_centers',
                 'role': 'Buttoned centers use M/R/Cc intervals [(0, 84), (180, 255), (132, 255)] in '
                         'their own geometry.'},
                {'name': 'tension_pleats',
                 'role': 'Tension pleats use M/R/Cc intervals [(70, 212), (76, 206), (66, 204)] in '
                         'their own geometry.'},
                {'name': 'thread_return_loops',
                 'role': 'Thread return loops use M/R/Cc intervals [(24, 184), (116, 244), (152, 252)] '
                         'in their own geometry.'}],
 'material_binding': {'M': ['quilted_panels',
                            'seam_stitches',
                            'buttoned_centers',
                            'tension_pleats',
                            'thread_return_loops'],
                      'R': ['quilted_panels',
                            'seam_stitches',
                            'buttoned_centers',
                            'tension_pleats',
                            'thread_return_loops'],
                      'Cc': ['quilted_panels',
                             'seam_stitches',
                             'buttoned_centers',
                             'tension_pleats',
                             'thread_return_loops']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_braided_junction',
                        'difference': 'Stitched Hex must visibly separate through quilted panels, seam '
                                      'stitches, buttoned centers and the remaining named marks, not '
                                      'color or parameter changes.'},
                       {'finish_id': 'spov2_triaxial_basket',
                        'difference': 'Stitched Hex must visibly separate through quilted panels, seam '
                                      'stitches, buttoned centers and the remaining named marks, not '
                                      'color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Hexagon seam outlines carry running stitches and small return '
                                     'loops.',
                                     'quilted panels is present in the native named-feature coverage '
                                     'probe.',
                                     'seam stitches is present in the native named-feature coverage '
                                     'probe.',
                                     'buttoned centers is present in the native named-feature coverage '
                                     'probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/stitched_hex/independent-feature-carrier',
 'spec_key': 'spec-v2/stitched_hex/named-material-bindings'}

render = build_renderer(stitched_hex, IDENTITY_CONTRACT)
