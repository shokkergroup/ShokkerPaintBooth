# SPB-105 / tick28 / 2026-09-06: final native + picker acceptance.
# Owner: fine details, many spec shades, unique construction and name-true design.
# M7: new/unscored -> 98.05; invariant nearest 0.36624 (<.55). Full movement/evidence: docs/SPEC_OVERLAYS_V2_ACCEPTANCE_2026-09-06.md.
"""SPB-105 v2 tick 6: Moire Packets. Identity declared before rendering/scoring."""
from ..optical_designs import moire_packets
from ..renderer import build_renderer

IDENTITY_CONTRACT = {'schema': 'spb-finish-identity/1',
 'finish_id': 'spov2_moire_packets',
 'display_name': 'Moire Packets - spec overlay',
 'promise': 'Moire Packets assembles crossed grating packets, grating beat nodes, packet separation '
            'gutters, registration tick clusters and etched aperture windows.',
 'paint_policy': 'Preserve source paint bytes; no color profile is generated.',
 'reference_physics': {'mechanism': 'Decorative interpretation of optical surface processes; the '
                                    'authored masks and material tiers are an artistic construction, '
                                    'not a measured physical simulation.',
                       'sources': ['https://support.iracing.com/support/solutions/articles/31000153524-paint-textures']},
 'carrier_grammar': 'Moire Packets assembles crossed grating packets, grating beat nodes, packet '
                    'separation gutters, registration tick clusters and etched aperture windows. '
                    'Geometry is independently authored in optical_designs.py:moire_packets.',
 'spec_grammar': 'Named feature masks bind independent M/R/Cc intervals to crossed grating packets, '
                 'grating beat nodes, packet separation gutters, registration tick clusters, etched '
                 'aperture windows.',
 'native_scale_px': [8, 32],
 'mark_types': [{'name': 'crossed_grating_packets',
                 'role': 'Crossed grating packets use M/R/Cc intervals [(18, 246), (0, 246), (24, 248)] '
                         'in their own geometry.'},
                {'name': 'grating_beat_nodes',
                 'role': 'Grating beat nodes use M/R/Cc intervals [(142, 255), (0, 92), (0, 112)] in '
                         'their own geometry.'},
                {'name': 'packet_separation_gutters',
                 'role': 'Packet separation gutters use M/R/Cc intervals [(0, 98), (180, 255), (146, '
                         '254)] in their own geometry.'},
                {'name': 'registration_tick_clusters',
                 'role': 'Registration tick clusters use M/R/Cc intervals [(56, 204), (102, 232), (68, '
                         '204)] in their own geometry.'},
                {'name': 'etched_aperture_windows',
                 'role': 'Etched aperture windows use M/R/Cc intervals [(96, 228), (54, 180), (164, '
                         '255)] in their own geometry.'}],
 'material_binding': {'M': ['crossed_grating_packets',
                            'grating_beat_nodes',
                            'packet_separation_gutters',
                            'registration_tick_clusters',
                            'etched_aperture_windows'],
                      'R': ['crossed_grating_packets',
                            'grating_beat_nodes',
                            'packet_separation_gutters',
                            'registration_tick_clusters',
                            'etched_aperture_windows'],
                      'Cc': ['crossed_grating_packets',
                             'grating_beat_nodes',
                             'packet_separation_gutters',
                             'registration_tick_clusters',
                             'etched_aperture_windows']},
 'material_tiers': ['substrate',
                    'recess',
                    'satin',
                    'polish',
                    'coat break',
                    'coat pool',
                    'transition lip',
                    'crest'],
 'nearest_neighbors': [{'finish_id': 'spov2_paired_facet_lattice',
                        'difference': 'Moire Packets must visibly separate through crossed grating '
                                      'packets, grating beat nodes, packet separation gutters and the '
                                      'remaining named marks, not color or parameter changes.'},
                       {'finish_id': 'spov2_fresnel_segments',
                        'difference': 'Moire Packets must visibly separate through crossed grating '
                                      'packets, grating beat nodes, packet separation gutters and the '
                                      'remaining named marks, not color or parameter changes.'}],
 'name_truth': {'visible_evidence': ['Two crossing fine gratings form clipped interference packets.',
                                     'crossed grating packets is present in the native named-feature '
                                     'coverage probe.',
                                     'grating beat nodes is present in the native named-feature '
                                     'coverage probe.',
                                     'packet separation gutters is present in the native named-feature '
                                     'coverage probe.'],
                'hidden_title_verdict': 'pass'},
 'construction_key': 'spec-v2/moire_packets/independent-feature-carrier',
 'spec_key': 'spec-v2/moire_packets/named-material-bindings'}

render = build_renderer(moire_packets, IDENTITY_CONTRACT)
