# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 98.18; invariant nearest 0.53299 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Satin Float. Identity declared before rendering/scoring."""
from ..weave_designs import satin_float
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_satin_float',
 'display_name': 'Satin Float - spec overlay',
 'promise': 'Satin Float assembles long float caps, buried weft, binding knots, resin channels and '
            'raised fiber tips.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of weave surface processes; the authored '
                                    'masks and material tiers are an artistic construction, not a '
                                    'measured physical simulation.',
                       'sources': ['https://www.toraycma.com/wp-content/uploads/3900-Prepreg-System.pdf']},
 'carrier_grammar': 'Satin Float assembles long float caps, buried weft, binding knots, resin channels '
                    'and raised fiber tips. Geometry is independently authored in '
                    'weave_designs.py:satin_float.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to long float caps, buried '
                 'weft, binding knots, resin channels, raised fiber tips.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'long_float_caps',
                 'role': 'Long float caps use M/R/Cc intervals [(96, 246), (16, 136), (32, 238)] in '
                         'their own geometry.'},
                {'name': 'buried_weft',
                 'role': 'Buried weft use M/R/Cc intervals [(4, 124), (142, 253), (140, 254)] in their '
                         'own geometry.'},
                {'name': 'binding_knots',
                 'role': 'Binding knots use M/R/Cc intervals [(28, 192), (58, 200), (16, 122)] in their '
                         'own geometry.'},
                {'name': 'resin_channels',
                 'role': 'Resin channels use M/R/Cc intervals [(0, 76), (12, 70), (0, 64)] in their own '
                         'geometry.'},
                {'name': 'raised_fiber_tips',
                 'role': 'Raised fiber tips use M/R/Cc intervals [(180, 255), (108, 234), (104, 246)] '
                         'in their own geometry.'}],
 'material_binding': {'M': ['long_float_caps',
                            'buried_weft',
                            'binding_knots',
                            'resin_channels',
                            'raised_fiber_tips'],
                      'R': ['long_float_caps',
                            'buried_weft',
                            'binding_knots',
                            'resin_channels',
                            'raised_fiber_tips'],
                      'Cc': ['long_float_caps',
                             'buried_weft',
                             'binding_knots',
                             'resin_channels',
                             'raised_fiber_tips']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_braided_junction',
                        'difference': 'Satin Float must visibly separate through long float caps, '
                                      'buried weft, binding knots and the remaining named marks, not '
                                      'color or parameter changes.'},
                       {'finish_id': 'spov2_triaxial_basket',
                        'difference': 'Satin Float must visibly separate through long float caps, '
                                      'buried weft, binding knots and the remaining named marks, not '
                                      'color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Long satin floats overlap narrow transverse threads.',
                                     'long float caps is present in the native named-feature coverage '
                                     'probe.',
                                     'buried weft is present in the native named-feature coverage '
                                     'probe.',
                                     'binding knots is present in the native named-feature coverage '
                                     'probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/satin_float/independent-feature-carrier',
 'spec_key': 'spec-v2/satin_float/named-material-bindings'}

render = build_renderer(satin_float, IDENTITY_CONTRACT)
