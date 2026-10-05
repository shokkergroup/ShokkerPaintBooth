# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 97.86; invariant nearest 0.53255 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Hilbert Relays. Identity declared before rendering/scoring."""
from ..experimental_designs import hilbert_relays
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_hilbert_relays',
 'display_name': 'Hilbert Relays - spec overlay',
 'promise': 'Hilbert Relays assembles space filling relay tracks, relay corner pads, insulating channel '
            'pockets, path terminal slots and bridge via collars.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of experimental surface processes; the '
                                    'authored masks and material tiers are an artistic construction, '
                                    'not a measured physical simulation.',
                       'sources': ['https://arxiv.org/abs/2303.10798']},
 'carrier_grammar': 'Hilbert Relays assembles space filling relay tracks, relay corner pads, insulating '
                    'channel pockets, path terminal slots and bridge via collars. Geometry is '
                    'independently authored in experimental_designs.py:hilbert_relays.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to space filling relay tracks, '
                 'relay corner pads, insulating channel pockets, path terminal slots, bridge via '
                 'collars.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'space_filling_relay_tracks',
                 'role': 'Space filling relay tracks use M/R/Cc intervals [(18, 246), (24, 214), (24, '
                         '248)] in their own geometry.'},
                {'name': 'relay_corner_pads',
                 'role': 'Relay corner pads use M/R/Cc intervals [(146, 255), (16, 108), (0, 114)] in '
                         'their own geometry.'},
                {'name': 'insulating_channel_pockets',
                 'role': 'Insulating channel pockets use M/R/Cc intervals [(0, 98), (180, 255), (146, '
                         '254)] in their own geometry.'},
                {'name': 'path_terminal_slots',
                 'role': 'Path terminal slots use M/R/Cc intervals [(56, 204), (102, 232), (68, 204)] '
                         'in their own geometry.'},
                {'name': 'bridge_via_collars',
                 'role': 'Bridge via collars use M/R/Cc intervals [(96, 228), (54, 180), (164, 255)] in '
                         'their own geometry.'}],
 'material_binding': {'M': ['space_filling_relay_tracks',
                            'relay_corner_pads',
                            'insulating_channel_pockets',
                            'path_terminal_slots',
                            'bridge_via_collars'],
                      'R': ['space_filling_relay_tracks',
                            'relay_corner_pads',
                            'insulating_channel_pockets',
                            'path_terminal_slots',
                            'bridge_via_collars'],
                      'Cc': ['space_filling_relay_tracks',
                             'relay_corner_pads',
                             'insulating_channel_pockets',
                             'path_terminal_slots',
                             'bridge_via_collars']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_aperiodic_alloy',
                        'difference': 'Hilbert Relays must visibly separate through space filling relay '
                                      'tracks, relay corner pads, insulating channel pockets and the '
                                      'remaining named marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_gyroid_windows',
                        'difference': 'Hilbert Relays must visibly separate through space filling relay '
                                      'tracks, relay corner pads, insulating channel pockets and the '
                                      'remaining named marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Nested rectilinear relay paths retain isolated corner links.',
                                     'space filling relay tracks is present in the native named-feature '
                                     'coverage probe.',
                                     'relay corner pads is present in the native named-feature coverage '
                                     'probe.',
                                     'insulating channel pockets is present in the native named-feature '
                                     'coverage probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/hilbert_relays/independent-feature-carrier',
 'spec_key': 'spec-v2/hilbert_relays/named-material-bindings'}

render = build_renderer(hilbert_relays, IDENTITY_CONTRACT)
