# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 97.02; invariant nearest 0.38598 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Truchet Switchyard. Identity declared before rendering/scoring."""
from ..experimental_designs import truchet_switchyard
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_truchet_switchyard',
 'display_name': 'Truchet Switchyard - spec overlay',
 'promise': 'Truchet Switchyard assembles paired truchet tracks, track switch collars, recessed arc '
            'interstices, junction contact tabs and guideway index ticks.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of experimental surface processes; the '
                                    'authored masks and material tiers are an artistic construction, '
                                    'not a measured physical simulation.',
                       'sources': ['https://arxiv.org/abs/2303.10798']},
 'carrier_grammar': 'Truchet Switchyard assembles paired truchet tracks, track switch collars, recessed '
                    'arc interstices, junction contact tabs and guideway index ticks. Geometry is '
                    'independently authored in experimental_designs.py:truchet_switchyard.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to paired truchet tracks, track '
                 'switch collars, recessed arc interstices, junction contact tabs, guideway index '
                 'ticks.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'paired_truchet_tracks',
                 'role': 'Paired truchet tracks use M/R/Cc intervals [(18, 246), (24, 214), (24, 248)] '
                         'in their own geometry.'},
                {'name': 'track_switch_collars',
                 'role': 'Track switch collars use M/R/Cc intervals [(146, 255), (16, 108), (0, 114)] '
                         'in their own geometry.'},
                {'name': 'recessed_arc_interstices',
                 'role': 'Recessed arc interstices use M/R/Cc intervals [(0, 98), (180, 255), (146, '
                         '254)] in their own geometry.'},
                {'name': 'junction_contact_tabs',
                 'role': 'Junction contact tabs use M/R/Cc intervals [(56, 204), (102, 232), (68, 204)] '
                         'in their own geometry.'},
                {'name': 'guideway_index_ticks',
                 'role': 'Guideway index ticks use M/R/Cc intervals [(96, 228), (54, 180), (164, 255)] '
                         'in their own geometry.'}],
 'material_binding': {'M': ['paired_truchet_tracks',
                            'track_switch_collars',
                            'recessed_arc_interstices',
                            'junction_contact_tabs',
                            'guideway_index_ticks'],
                      'R': ['paired_truchet_tracks',
                            'track_switch_collars',
                            'recessed_arc_interstices',
                            'junction_contact_tabs',
                            'guideway_index_ticks'],
                      'Cc': ['paired_truchet_tracks',
                             'track_switch_collars',
                             'recessed_arc_interstices',
                             'junction_contact_tabs',
                             'guideway_index_ticks']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_aperiodic_alloy',
                        'difference': 'Truchet Switchyard must visibly separate through paired truchet '
                                      'tracks, track switch collars, recessed arc interstices and the '
                                      'remaining named marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_gyroid_windows',
                        'difference': 'Truchet Switchyard must visibly separate through paired truchet '
                                      'tracks, track switch collars, recessed arc interstices and the '
                                      'remaining named marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Alternating quarter-turn connections create local Truchet '
                                     'switches.',
                                     'paired truchet tracks is present in the native named-feature '
                                     'coverage probe.',
                                     'track switch collars is present in the native named-feature '
                                     'coverage probe.',
                                     'recessed arc interstices is present in the native named-feature '
                                     'coverage probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/truchet_switchyard/independent-feature-carrier',
 'spec_key': 'spec-v2/truchet_switchyard/named-material-bindings'}

render = build_renderer(truchet_switchyard, IDENTITY_CONTRACT)
