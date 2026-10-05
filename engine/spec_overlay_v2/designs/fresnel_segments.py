# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 97.94; invariant nearest 0.3184 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Fresnel Segments. Identity declared before rendering/scoring."""
from ..optical_designs import fresnel_segments
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_fresnel_segments',
 'display_name': 'Fresnel Segments - spec overlay',
 'promise': 'Fresnel Segments assembles stepped lens segments, facet reset edges, segment separator '
            'slots, lens center tabs and truncated facet corners.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of optical surface processes; the '
                                    'authored masks and material tiers are an artistic construction, '
                                    'not a measured physical simulation.',
                       'sources': ['https://support.iracing.com/support/solutions/articles/31000153524-paint-textures']},
 'carrier_grammar': 'Fresnel Segments assembles stepped lens segments, facet reset edges, segment '
                    'separator slots, lens center tabs and truncated facet corners. Geometry is '
                    'independently authored in optical_designs.py:fresnel_segments.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to stepped lens segments, facet '
                 'reset edges, segment separator slots, lens center tabs, truncated facet corners.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'stepped_lens_segments',
                 'role': 'Stepped lens segments use M/R/Cc intervals [(18, 248), (0, 246), (24, 248)] '
                         'in their own geometry.'},
                {'name': 'facet_reset_edges',
                 'role': 'Facet reset edges use M/R/Cc intervals [(148, 255), (0, 92), (0, 112)] in '
                         'their own geometry.'},
                {'name': 'segment_separator_slots',
                 'role': 'Segment separator slots use M/R/Cc intervals [(0, 98), (180, 255), (146, '
                         '254)] in their own geometry.'},
                {'name': 'lens_center_tabs',
                 'role': 'Lens center tabs use M/R/Cc intervals [(56, 204), (102, 232), (68, 204)] in '
                         'their own geometry.'},
                {'name': 'truncated_facet_corners',
                 'role': 'Truncated facet corners use M/R/Cc intervals [(98, 228), (54, 180), (164, '
                         '255)] in their own geometry.'}],
 'material_binding': {'M': ['stepped_lens_segments',
                            'facet_reset_edges',
                            'segment_separator_slots',
                            'lens_center_tabs',
                            'truncated_facet_corners'],
                      'R': ['stepped_lens_segments',
                            'facet_reset_edges',
                            'segment_separator_slots',
                            'lens_center_tabs',
                            'truncated_facet_corners'],
                      'Cc': ['stepped_lens_segments',
                             'facet_reset_edges',
                             'segment_separator_slots',
                             'lens_center_tabs',
                             'truncated_facet_corners']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_paired_facet_lattice',
                        'difference': 'Fresnel Segments must visibly separate through stepped lens '
                                      'segments, facet reset edges, segment separator slots and the '
                                      'remaining named marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_moire_packets',
                        'difference': 'Fresnel Segments must visibly separate through stepped lens '
                                      'segments, facet reset edges, segment separator slots and the '
                                      'remaining named marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Narrow curved lens slivers contain repeated material reset steps.',
                                     'stepped lens segments is present in the native named-feature '
                                     'coverage probe.',
                                     'facet reset edges is present in the native named-feature coverage '
                                     'probe.',
                                     'segment separator slots is present in the native named-feature '
                                     'coverage probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/fresnel_segments/independent-feature-carrier',
 'spec_key': 'spec-v2/fresnel_segments/named-material-bindings'}

render = build_renderer(fresnel_segments, IDENTITY_CONTRACT)
